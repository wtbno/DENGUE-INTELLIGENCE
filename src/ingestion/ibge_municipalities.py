
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = ROOT / "data" / "reference" / "ibge"
OUTPUT_FILE = OUTPUT_DIR / "municipios.csv"

API_URL = (
    "https://servicodados.ibge.gov.br/"
    "api/v1/localidades/municipios"
)


def extract_uf(item):
    """Extrai a UF usando as hierarquias disponíveis na API."""

    # Estrutura antiga
    micro = item.get("microrregiao")

    if micro:
        meso = micro.get("mesorregiao")

        if meso and meso.get("UF"):
            return meso["UF"]

    # Estrutura de regiões imediatas/intermediárias
    immediate = item.get("regiao-imediata")

    if immediate:
        intermediate = immediate.get("regiao-intermediaria")

        if intermediate and intermediate.get("UF"):
            return intermediate["UF"]

    return None


def download_municipalities():

    print("Consultando API de localidades do IBGE...")

    response = requests.get(
        API_URL,
        timeout=60
    )

    response.raise_for_status()

    municipalities = response.json()

    records = []
    without_uf = []

    for item in municipalities:

        uf = extract_uf(item)

        if uf is None:
            without_uf.append(item["nome"])
            continue

        records.append({
            "ID_IBGE": str(item["id"]),
            "ID_SINAN": str(item["id"])[:-1],
            "MUNICIPIO": item["nome"],
            "UF": uf["nome"],
            "SIGLA_UF": uf["sigla"],
            "REGIAO": uf["regiao"]["nome"]
        })

    df = pd.DataFrame(records)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8"
    )

    print("\nCadastro IBGE salvo!")
    print(f"Municípios recebidos: {len(municipalities)}")
    print(f"Municípios processados: {len(df)}")
    print(f"Sem UF identificada: {len(without_uf)}")
    print(f"Arquivo: {OUTPUT_FILE}")

    if without_uf:
        print("\nMunicípios sem UF:")
        print(without_uf[:20])

    print("\nPrévia:")
    print(df.head(10))

    print("\nUFs encontradas:")
    print(df["SIGLA_UF"].nunique())

    return df


if __name__ == "__main__":
    download_municipalities()
