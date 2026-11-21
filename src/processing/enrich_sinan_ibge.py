
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

SINAN_FILE = (
    ROOT / "data" / "processed" / "sinan"
    / "2020" / "DENGBR20.parquet"
)

IBGE_FILE = (
    ROOT / "data" / "reference" / "ibge"
    / "municipios.csv"
)

OUTPUT_FILE = (
    ROOT / "data" / "processed" / "sinan"
    / "2020" / "municipios_2020.parquet"
)


def main():

    print("Iniciando cruzamento SINAN + IBGE...")

    # 1. Carregar somente as colunas necessárias
    sinan = pd.read_parquet(
        SINAN_FILE,
        columns=["ID_MN_RESI", "IS_DENGUE"]
    )

    ibge = pd.read_csv(
        IBGE_FILE,
        dtype=str
    )

    # 2. Padronizar os códigos municipais
    sinan["ID_MN_RESI"] = (
        sinan["ID_MN_RESI"]
        .astype("string")
        .str.strip()
        .str.zfill(6)
    )

    ibge["ID_SINAN"] = (
        ibge["ID_SINAN"]
        .astype("string")
        .str.strip()
        .str.zfill(6)
    )

    # 3. Agrupar registros por município de residência
    summary = (
        sinan
        .dropna(subset=["ID_MN_RESI"])
        .groupby("ID_MN_RESI")
        .agg(
            REGISTROS_TOTAIS=("IS_DENGUE", "size"),
            CASOS_DENGUE=(
                "IS_DENGUE",
                lambda x: x.fillna(False).sum()
            )
        )
        .reset_index()
    )

    # 4. Cruzar com o cadastro do IBGE
    result = summary.merge(
        ibge,
        left_on="ID_MN_RESI",
        right_on="ID_SINAN",
        how="left",
        validate="one_to_one"
    )

    # 5. Calcular participação nacional
    total_cases = result["CASOS_DENGUE"].sum()

    result["PARTICIPACAO_NACIONAL"] = (
        result["CASOS_DENGUE"] / total_cases * 100
    )

    # 6. Separar municípios encontrados e não encontrados
    matched = result["MUNICIPIO"].notna()
    unmatched = result[~matched].copy()

    unmatched_records = unmatched["REGISTROS_TOTAIS"].sum()
    unmatched_cases = unmatched["CASOS_DENGUE"].sum()

    matched_records = result.loc[matched, "REGISTROS_TOTAIS"].sum()
    matched_cases = result.loc[matched, "CASOS_DENGUE"].sum()

    total_records_with_municipality = result["REGISTROS_TOTAIS"].sum()

    print("\n========== COBERTURA POR REGISTROS ==========")
    print(f"Registros associados ao IBGE: {matched_records:,}")
    print(f"Registros sem correspondência: {unmatched_records:,}")
    print(
        f"Cobertura dos registros: "
        f"{matched_records / total_records_with_municipality * 100:.2f}%"
    )
    print(f"Casos de dengue sem correspondência: {unmatched_cases:,}")
    print(f"Cobertura dos casos de dengue: {matched_cases / total_cases * 100:.2f}%")

    print("\n========== MUNICÍPIOS NÃO ENCONTRADOS ==========")
    print(
        unmatched[
            ["ID_MN_RESI", "REGISTROS_TOTAIS", "CASOS_DENGUE"]
        ].to_string(index=False)
    )

    # Salvar relatório para investigação
    unmatched.to_csv(
        OUTPUT_FILE.parent / "municipios_nao_encontrados.csv",
        index=False,
        encoding="utf-8"
    )

    print("\n========== AUDITORIA DO JOIN ==========")
    print(f"Registros SINAN: {len(sinan):,}")
    print(
        "Registros sem município de residência:",
        sinan["ID_MN_RESI"].isna().sum()
    )

    print(
        "Municípios distintos no SINAN:",
        summary["ID_MN_RESI"].nunique()
    )

    print(
        "Municípios encontrados no IBGE:",
        matched.sum()
    )

    print(
        "Municípios não encontrados:",
        (~matched).sum()
    )

    print(
        "Percentual de correspondência:",
        f"{matched.mean() * 100:.2f}%"
    )

    print("\n========== TOP 10 MUNICÍPIOS ==========")
    top10 = result.sort_values(
        "CASOS_DENGUE",
        ascending=False
    ).head(10)

    print(
        top10[
            [
                "MUNICIPIO",
                "SIGLA_UF",
                "REGIAO",
                "REGISTROS_TOTAIS",
                "CASOS_DENGUE",
                "PARTICIPACAO_NACIONAL"
            ]
        ].to_string(index=False)
    )

    # 7. Salvar resultado
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_parquet(
        OUTPUT_FILE,
        index=False
    )

    print("\nArquivo enriquecido salvo:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
