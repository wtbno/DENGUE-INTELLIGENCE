from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_SINAN_DIR = PROJECT_ROOT / "data" / "raw" / "sinan"
PROCESSED_SINAN_DIR = PROJECT_ROOT / "data" / "processed" / "sinan"
REPORTS_DIR = PROJECT_ROOT / "reports"

REQUIRED_COLUMNS = [
    "CLASSI_FIN",
    "EVOLUCAO",
    "CRITERIO",
    "ID_MN_RESI",
    "ID_MUNICIP",
]

DATE_COLUMNS = [
    "DT_SIN_PRI",
    "DT_NOTIFIC",
    "DT_ENCERRA",
    "DT_OBITO",
]


def discover_years(raw_dir: Path | str, years: Optional[Iterable[int]] = None) -> list[int]:
    """Retorna os anos com arquivos SINAN disponíveis."""

    raw_path = Path(raw_dir)
    if not raw_path.exists():
        return []

    discovered = []
    for candidate in sorted(raw_path.iterdir(), key=lambda item: item.name):
        if not candidate.is_dir():
            continue

        try:
            year = int(candidate.name)
        except ValueError:
            continue

        if any(file.name.startswith("DENGBR") and file.suffix.lower() == ".csv" for file in candidate.iterdir()):
            discovered.append(year)

    if years is not None:
        allowed = set(years)
        discovered = [year for year in discovered if year in allowed]

    return sorted(set(discovered))


def build_quality_summary(frame: pd.DataFrame) -> dict:
    """Cria o resumo de qualidade do dataset processado."""

    working = frame.copy()
    working.columns = [str(column).strip() for column in working.columns]

    classification = working["CLASSI_FIN"].fillna("").astype(str).str.strip() if "CLASSI_FIN" in working.columns else pd.Series("", index=working.index)
    evolution = working["EVOLUCAO"].fillna("").astype(str).str.strip() if "EVOLUCAO" in working.columns else pd.Series("", index=working.index)

    is_dengue = working["IS_DENGUE"] if "IS_DENGUE" in working.columns else classification.isin(["10", "11", "12"])
    is_alarm_signs = working["IS_ALARM_SIGNS"] if "IS_ALARM_SIGNS" in working.columns else classification.eq("11")
    is_severe_dengue = working["IS_SEVERE_DENGUE"] if "IS_SEVERE_DENGUE" in working.columns else classification.eq("12")
    is_discarded = working["IS_DISCARDED"] if "IS_DISCARDED" in working.columns else classification.eq("5")
    is_dengue_death = working["IS_DENGUE_DEATH"] if "IS_DENGUE_DEATH" in working.columns else evolution.eq("2")
    death_data_mismatch = working["DEATH_DATA_MISMATCH"] if "DEATH_DATA_MISMATCH" in working.columns else pd.Series(False, index=working.index)

    summary = {
        "records": int(len(working)),
        "columns": int(len(working.columns)),
        "null_id_mn_resi": int(working["ID_MN_RESI"].isna().sum()) if "ID_MN_RESI" in working.columns else 0,
        "is_dengue": int(is_dengue.fillna(False).sum()),
        "is_alarm_signs": int(is_alarm_signs.fillna(False).sum()),
        "is_severe_dengue": int(is_severe_dengue.fillna(False).sum()),
        "is_discarded": int(is_discarded.fillna(False).sum()),
        "is_dengue_death": int(is_dengue_death.fillna(False).sum()),
        "death_date_mismatch": int(death_data_mismatch.fillna(False).sum()),
    }
    return summary


def validate_schema(frame: pd.DataFrame, required_columns: Optional[list[str]] = None) -> dict:
    """Valida se o DataFrame contém as colunas mínimas exigidas."""

    expected = list(required_columns or REQUIRED_COLUMNS)
    actual = [str(column) for column in frame.columns]
    missing = [column for column in expected if column not in actual]
    return {
        "valid": not missing,
        "expected_columns": expected,
        "actual_columns": actual,
        "missing_columns": missing,
    }


def clean_missing_values(frame: pd.DataFrame, fill_string: str = "") -> pd.DataFrame:
    """Padroniza valores ausentes para campos string e numéricos."""

    cleaned = frame.copy()
    for column in cleaned.columns:
        if pd.api.types.is_numeric_dtype(cleaned[column]):
            cleaned[column] = cleaned[column].fillna(0)
        else:
            cleaned[column] = cleaned[column].fillna(fill_string)
    return cleaned


def identify_duplicates(frame: pd.DataFrame, key_columns: Optional[list[str]] = None) -> dict:
    """Identifica registros duplicados com base em colunas-chave."""

    keys = key_columns or ["ID_MN_RESI", "DT_SIN_PRI", "CLASSI_FIN"]
    keys = [column for column in keys if column in frame.columns]

    if not keys:
        return {"duplicate_rows": 0, "duplicate_keys": pd.DataFrame(), "keys": keys}

    duplicate_mask = frame.duplicated(subset=keys, keep=False)
    duplicates = frame.loc[duplicate_mask].copy()
    duplicate_summary = duplicates.groupby(keys).size().reset_index(name="count") if keys else pd.DataFrame()

    return {
        "duplicate_rows": int(len(duplicates)),
        "duplicate_keys": duplicate_summary,
        "keys": keys,
    }


def validate_ibge_municipality_codes(
    frame: pd.DataFrame,
    ibge_reference: pd.DataFrame,
    sinan_column: str = "ID_MN_RESI",
    ibge_column: str = "ID_SINAN",
) -> dict:
    """Valida se cada código municipal SINAN existe no cadastro do IBGE."""

    if sinan_column not in frame.columns:
        raise KeyError(f"Coluna SINAN {sinan_column} não encontrada no DataFrame.")
    if ibge_column not in ibge_reference.columns:
        raise KeyError(f"Coluna IBGE {ibge_column} não encontrada no cadastro do IBGE.")

    normalized_sinan = frame[[sinan_column]].copy()
    normalized_sinan[sinan_column] = (
        normalized_sinan[sinan_column]
        .astype("string")
        .str.replace(r"\D+", "", regex=True)
        .str.strip()
        .str.zfill(6)
    )

    normalized_ibge = ibge_reference[[ibge_column]].copy()
    normalized_ibge[ibge_column] = (
        normalized_ibge[ibge_column]
        .astype("string")
        .str.replace(r"\D+", "", regex=True)
        .str.strip()
        .str.zfill(6)
    )

    unique_sinan = normalized_sinan.drop_duplicates(subset=[sinan_column]).copy()
    unique_ibge = normalized_ibge.drop_duplicates(subset=[ibge_column]).copy()

    matched = unique_sinan.merge(
        unique_ibge,
        left_on=sinan_column,
        right_on=ibge_column,
        how="left",
        indicator=True,
    )

    unmatched = matched[matched["_merge"] == "left_only"].copy()
    valid = len(unmatched) == 0
    coverage = 0.0 if len(unique_sinan) == 0 else (1 - (len(unmatched) / len(unique_sinan))) * 100

    return {
        "valid": valid,
        "total_codes": int(len(unique_sinan)),
        "matched_codes": int(len(unique_sinan) - len(unmatched)),
        "unmatched_codes": int(len(unmatched)),
        "coverage_pct": round(float(coverage), 2),
        "unmatched_values": unmatched[sinan_column].dropna().unique().tolist(),
    }


def write_quality_manifest(run_name: str, payload: dict, output_dir: Path | str = REPORTS_DIR) -> Path:
    """Salva o manifest de rastreabilidade da execução do pipeline."""

    output_path = Path(output_dir) / "quality"
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path / f"{run_name}_manifest.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def build_storage_recommendation() -> dict:
    """Avalia estratégia de armazenamento analítico sem abandonar Parquet."""

    return {
        "recommended_stack": [
            "Parquet para dados brutos e processados em camada analítica/local",
            "PostgreSQL para consultas operacionais, joins analíticos e dashboards interativos",
        ],
        "reasoning": [
            "O Parquet é excelente para armazenamento eficiente, versionamento e leitura em lote.",
            "O PostgreSQL agrega valor em consultas OLAP/OLTP híbridas, filtros interativos e integração com ferramentas analíticas.",
            "A melhor arquitetura é manter Parquet como camada de persistência logística e PostgreSQL como camada analítica de consulta.",
        ],
        "final_recommendation": "Usar Parquet como base de dados de processamento e PostgreSQL apenas quando houver necessidade de camada analítica e consulta interativa.",
    }


def standardize_chunk(frame: pd.DataFrame) -> pd.DataFrame:
    """Padroniza colunas, tipos e indicadores dos microdados."""

    standardized = frame.copy()
    standardized.columns = [str(column).strip() for column in standardized.columns]

    for column in standardized.columns:
        if standardized[column].dtype == object:
            standardized[column] = standardized[column].map(
                lambda value: value.strip() if isinstance(value, str) else value
            )

    for column in REQUIRED_COLUMNS:
        if column in standardized.columns:
            standardized[column] = standardized[column].astype("string")

    for column in DATE_COLUMNS:
        if column in standardized.columns:
            standardized[f"{column}_DATE"] = pd.to_datetime(
                standardized[column],
                format="%Y-%m-%d",
                errors="coerce",
            )

    classification = standardized["CLASSI_FIN"].fillna("").astype(str).str.strip()
    evolution = standardized["EVOLUCAO"].fillna("").astype(str).str.strip()

    standardized["IS_DENGUE"] = classification.isin(["10", "11", "12"])
    standardized["IS_ALARM_SIGNS"] = classification.eq("11")
    standardized["IS_SEVERE_DENGUE"] = classification.eq("12")
    standardized["IS_DISCARDED"] = classification.eq("5")
    standardized["IS_CLASSIFICATION_8"] = classification.eq("8")
    standardized["IS_DENGUE_DEATH"] = evolution.eq("2")
    standardized["IS_OTHER_CAUSE_DEATH"] = evolution.eq("3")
    standardized["IS_DEATH_UNDER_INVESTIGATION"] = evolution.eq("4")

    if "DT_OBITO_DATE" in standardized.columns:
        standardized["HAS_DEATH_DATE"] = standardized["DT_OBITO_DATE"].notna()
        standardized["DEATH_DATA_MISMATCH"] = (
            standardized["HAS_DEATH_DATE"]
            & ~standardized["EVOLUCAO"].fillna("").astype(str).str.strip().isin(["2", "3", "4"])
        )

    if "ID_MN_RESI" in standardized.columns:
        standardized["ID_MN_RESI"] = (
            standardized["ID_MN_RESI"]
            .astype("string")
            .str.strip()
            .str.replace(r"\D+", "", regex=True)
            .str.zfill(6)
        )

    if "ID_MUNICIP" in standardized.columns:
        standardized["ID_MUNICIP"] = (
            standardized["ID_MUNICIP"]
            .astype("string")
            .str.strip()
            .str.replace(r"\D+", "", regex=True)
            .str.zfill(6)
        )

    return standardized


def process_year(
    year: int,
    raw_dir: Path | str = RAW_SINAN_DIR,
    processed_dir: Path | str = PROCESSED_SINAN_DIR,
    report_dir: Path | str = REPORTS_DIR,
    chunksize: int = 100_000,
) -> dict:
    """Processa um ano completo do SINAN e salva o Parquet padronizado."""

    raw_path = Path(raw_dir)
    processed_path = Path(processed_dir)
    reports_path = Path(report_dir)

    input_file = raw_path / str(year) / f"DENGBR{str(year)[-2:]}.csv"
    output_dir = processed_path / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"DENGBR{str(year)[-2:]}.parquet"
    quality_dir = reports_path / "quality"
    quality_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = reports_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        raise FileNotFoundError(f"Arquivo bruto não encontrado: {input_file}")

    logger = logging.getLogger(f"sinan_{year}")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        file_handler = logging.FileHandler(logs_dir / f"sinan_{year}_etl.log", encoding="utf-8")
        logger.addHandler(file_handler)
        logger.propagate = False

    logger.info("Iniciando processamento do SINAN %s", year)
    logger.info("Arquivo de entrada: %s", input_file)

    total_records = 0
    quality_summary = {
        "year": year,
        "input_file": str(input_file),
        "output_file": str(output_file),
        "schema_validation": None,
        "duplicate_validation": None,
        "storage_recommendation": build_storage_recommendation(),
    }
    parquet_writer = None

    try:
        chunk_reader = pd.read_csv(
            input_file,
            sep=",",
            engine="python",
            encoding="latin1",
            dtype="string",
            chunksize=chunksize,
            on_bad_lines="warn",
        )

        for chunk_number, chunk in enumerate(chunk_reader, start=1):
            chunk = chunk.copy()
            chunk.columns = [str(column).strip() for column in chunk.columns]

            schema_check = validate_schema(chunk, REQUIRED_COLUMNS)
            quality_summary["schema_validation"] = schema_check

            if not schema_check["valid"]:
                raise ValueError(f"Colunas mínimas ausentes em {year}: {schema_check['missing_columns']}")

            cleaned = clean_missing_values(chunk)
            standardized = standardize_chunk(cleaned)
            duplicates = identify_duplicates(standardized, ["ID_MN_RESI", "DT_SIN_PRI", "CLASSI_FIN"])
            quality_summary["duplicate_validation"] = {
                "duplicate_rows": duplicates["duplicate_rows"],
                "keys": duplicates["keys"],
            }

            table = pa.Table.from_pandas(standardized, preserve_index=False)

            if parquet_writer is None:
                parquet_writer = pq.ParquetWriter(str(output_file), table.schema, compression="snappy")

            parquet_writer.write_table(table)

            total_records += len(standardized)
            logger.info("Bloco %s processado; total acumulado: %s", chunk_number, total_records)

        if parquet_writer is not None:
            parquet_writer.close()

        processed_frame = pd.read_parquet(output_file)
        quality_summary.update(build_quality_summary(processed_frame))
        quality_summary["status"] = "success"

        write_quality_manifest(f"sinan_{year}", quality_summary, reports_path)

        quality_file = quality_dir / f"{year}_quality_summary.csv"
        summary_df = pd.DataFrame([quality_summary])
        summary_df.to_csv(quality_file, index=False, encoding="utf-8")

        logger.info("Processamento concluído com sucesso para %s", year)
        logger.info("Resumo: %s", json.dumps(quality_summary, ensure_ascii=False))

        return quality_summary

    except Exception as error:
        quality_summary["status"] = "error"
        quality_summary["error"] = str(error)
        quality_summary["records_processed"] = total_records

        quality_file = quality_dir / f"{year}_quality_summary.csv"
        pd.DataFrame([quality_summary]).to_csv(quality_file, index=False, encoding="utf-8")

        logger.exception("Erro durante o processamento do SINAN %s", year)
        raise

    finally:
        if parquet_writer is not None:
            parquet_writer.close()


def run_pipeline(
    years: Optional[Iterable[int]] = None,
    raw_dir: Path | str = RAW_SINAN_DIR,
    processed_dir: Path | str = PROCESSED_SINAN_DIR,
    report_dir: Path | str = REPORTS_DIR,
) -> list[dict]:
    """Executa o pipeline para uma lista de anos ou para todos os disponíveis."""

    raw_path = Path(raw_dir)
    if years is None:
        target_years = discover_years(raw_path)
    else:
        target_years = sorted(set(years))

    results = []
    manifest_rows = []

    for year in target_years:
        summary = process_year(year, raw_dir=raw_path, processed_dir=processed_dir, report_dir=report_dir)
        results.append(summary)
        manifest_rows.append({
            "year": year,
            "records": summary.get("records", 0),
            "is_dengue": summary.get("is_dengue", 0),
            "is_dengue_death": summary.get("is_dengue_death", 0),
            "status": summary.get("status", "unknown"),
        })

    manifest = pd.DataFrame(manifest_rows)
    manifest_path = Path(report_dir) / "quality" / "sinan_manifest.csv"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(manifest_path, index=False, encoding="utf-8")

    return results


def main() -> None:
    years = list(range(2020, 2026))
    available = discover_years(RAW_SINAN_DIR, years)
    if not available:
        raise FileNotFoundError(f"Nenhum arquivo SINAN encontrado em {RAW_SINAN_DIR}")

    print("Iniciando ETL SINAN para os anos:", available)
    results = run_pipeline(years=available)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
