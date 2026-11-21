
import requests
import zipfile
from pathlib import Path
from tqdm import tqdm

# Configurações
BASE_URL = (
    "https://s3.sa-east-1.amazonaws.com/"
    "ckan.saude.gov.br/SINAN/Dengue/csv/"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "sinan"

YEARS = range(2020, 2027)

HEADERS = {
    "User-Agent": "DengueIntelligenceBR/1.0"
}


def download_file(year):

    filename = f"DENGBR{str(year)[-2:]}.csv.zip"
    url = BASE_URL + filename

    destination = OUTPUT_DIR / str(year)
    destination.mkdir(parents=True, exist_ok=True)

    zip_path = destination / filename

    # Evita baixar novamente arquivos já existentes e válidos
    if zip_path.exists() and zipfile.is_zipfile(zip_path):
        print(f"[EXISTENTE] {year}: download ignorado.")
        return

    print(f"\nBaixando SINAN {year}...")

    response = requests.get(
        url,
        headers=HEADERS,
        stream=True,
        timeout=(30, 300)
    )

    if response.status_code == 404:
        print(f"[INDISPONÍVEL] Arquivo de {year} não encontrado.")
        return

    response.raise_for_status()

    temp_path = zip_path.with_suffix(".zip.part")

    try:
        with open(temp_path, "wb") as file:

            total = int(response.headers.get("content-length", 0))

            with tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc=str(year)
            ) as progress:

                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        file.write(chunk)
                        progress.update(len(chunk))

        if not zipfile.is_zipfile(temp_path):
            raise ValueError("O arquivo recebido não é um ZIP válido.")

        temp_path.replace(zip_path)

        # Extração
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(destination)

        print(f"[OK] SINAN {year} baixado e extraído.")

    finally:
        if temp_path.exists():
            temp_path.unlink()


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("DENGUE INTELLIGENCE BR")
    print("Coleta de microdados SINAN")
    print("=" * 50)

    for year in YEARS:

        try:
            download_file(year)

        except Exception as error:
            print(f"[ERRO] {year}: {error}")


if __name__ == "__main__":
    main()
