
from pathlib import Path
from collections import Counter

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


# ==========================================
# CONFIGURAÇÕES
# ==========================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT / "data" / "raw" / "sinan" / "2020" / "DENGBR20.csv"

OUTPUT_DIR = ROOT / "data" / "processed" / "sinan" / "2020"

OUTPUT_FILE = OUTPUT_DIR / "DENGBR20.parquet"

CHUNK_SIZE = 100_000

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# VALIDAÇÃO DO ARQUIVO
# ==========================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Arquivo não encontrado: {INPUT_FILE}"
    )


# ==========================================
# VARIÁVEIS DE CONTROLE
# ==========================================

date_columns = [
    "DT_SIN_PRI",
    "DT_NOTIFIC",
    "DT_ENCERRA",
    "DT_OBITO"
]

required_columns = [
    "CLASSI_FIN",
    "EVOLUCAO",
    "CRITERIO",
    "ID_MN_RESI",
    "ID_MUNICIP"
]

total_records = 0

classification_counts = Counter()
evolution_counts = Counter()

writer = None


# ==========================================
# PROCESSAMENTO
# ==========================================

print("\nIniciando ETL SINAN 2020...")
print(f"Arquivo de origem: {INPUT_FILE.name}")

try:

    reader = pd.read_csv(
        INPUT_FILE,
        sep=None,
        engine="python",
        encoding="latin1",
        dtype="string",
        chunksize=CHUNK_SIZE,
        on_bad_lines="warn"
    )

    for chunk_number, df in enumerate(reader, start=1):

        print(f"\nProcessando bloco {chunk_number}...")

        # Validar variáveis necessárias
        missing_columns = [
            col for col in required_columns
            if col not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Variáveis ausentes: {missing_columns}"
            )

        # Padronizar espaços
        for col in df.columns:
            df[col] = df[col].str.strip()

        # Contabilizar categorias originais
        classification_counts.update(
            df["CLASSI_FIN"].fillna("<VAZIO>").value_counts().to_dict()
        )

        evolution_counts.update(
            df["EVOLUCAO"].fillna("<VAZIO>").value_counts().to_dict()
        )

        # Converter datas sem perder os campos originais
        for col in date_columns:

            if col in df.columns:

                df[f"{col}_DATE"] = pd.to_datetime(
                    df[col],
                    format="%Y-%m-%d",
                    errors="coerce"
                )

        # ==================================
        # INDICADORES DERIVADOS
        # ==================================

        classification = df["CLASSI_FIN"]
        evolution = df["EVOLUCAO"]

        df["IS_DENGUE"] = classification.isin(
            ["10", "11", "12"]
        )

        df["IS_ALARM_SIGNS"] = classification.eq("11")

        df["IS_SEVERE_DENGUE"] = classification.eq("12")

        df["IS_DISCARDED"] = classification.eq("5")

        df["IS_CLASSIFICATION_8"] = classification.eq("8")

        df["IS_DENGUE_DEATH"] = evolution.eq("2")

        df["IS_OTHER_CAUSE_DEATH"] = evolution.eq("3")

        df["IS_DEATH_UNDER_INVESTIGATION"] = evolution.eq("4")

        # ==================================
        # CONTROLE DE QUALIDADE
        # ==================================

        if "DT_OBITO_DATE" in df.columns:

            has_death_date = df["DT_OBITO_DATE"].notna()

            df["HAS_DEATH_DATE"] = has_death_date

            df["DEATH_DATA_MISMATCH"] = (
                has_death_date
                & ~evolution.isin(["2", "3", "4"])
            )

        # ==================================
        # SALVAR EM PARQUET
        # ==================================

        table = pa.Table.from_pandas(
            df,
            preserve_index=False
        )

        if writer is None:

            writer = pq.ParquetWriter(
                OUTPUT_FILE,
                table.schema,
                compression="snappy"
            )

        writer.write_table(table)

        total_records += len(df)

        print(
            f"Registros processados: {total_records:,}"
        )

finally:

    if writer is not None:
        writer.close()


# ==========================================
# RELATÓRIO FINAL
# ==========================================

print("\n" + "=" * 45)
print("ETL CONCLUÍDO")
print("=" * 45)

print(f"Total de registros: {total_records:,}")

print("\nClassificação final:")
for code, quantity in classification_counts.most_common():
    print(f"{code}: {quantity:,}")

print("\nEvolução:")
for code, quantity in evolution_counts.most_common():
    print(f"{code}: {quantity:,}")

print(f"\nArquivo gerado: {OUTPUT_FILE}")

print(
    f"Tamanho: {OUTPUT_FILE.stat().st_size / (1024**2):.2f} MB"
)
