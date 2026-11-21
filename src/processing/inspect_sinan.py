
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "raw" / "sinan"
REPORT_DIR = ROOT / "reports"

REPORT_DIR.mkdir(exist_ok=True)

files = list(DATA_DIR.rglob("*.csv"))

report = []

report.append("DENGUE INTELLIGENCE BR")
report.append("RELATORIO DE INSPECAO SINAN")
report.append("=" * 60)

for file in files:

    report.append(f"\nARQUIVO: {file.name}")
    report.append(f"TAMANHO: {file.stat().st_size / 1024**2:.2f} MB")

    try:
        df = pd.read_csv(
            file,
            sep=";",
            encoding="latin1",
            dtype=str,
            nrows=5
        )

        report.append(f"COLUNAS: {len(df.columns)}")
        report.append("\nVARIAVEIS:")

        report.extend(df.columns.tolist())

        report.append("\nAMOSTRA DE DADOS:")
        report.append(df.head(3).to_string(index=False))

    except Exception as error:
        report.append(f"ERRO: {error}")

output = REPORT_DIR / "sinan_inspection.txt"

output.write_text(
    "\n".join(report),
    encoding="utf-8"
)

print(f"Relatorio gerado: {output}")
print(f"Arquivos analisados: {len(files)}")
