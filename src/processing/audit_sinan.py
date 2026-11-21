
from pathlib import Path
from collections import Counter
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "raw" / "sinan"

files = sorted(
    f for f in DATA_DIR.rglob("*")
    if f.is_file() and f.suffix.lower() == ".csv"
)

for i, file in enumerate(files):
    print(f"[{i}] {file.name}")

index = int(input("\nEscolha o arquivo de 2020: "))
selected = files[index]

columns = [
    "CLASSI_FIN",
    "EVOLUCAO",
    "CRITERIO",
    "DT_OBITO",
    "ID_MN_RESI",
    "ID_MUNICIP"
]

counts = {col: Counter() for col in columns}
total = 0

print(f"\nAuditando {selected.name}...")

for chunk in pd.read_csv(
    selected,
    sep=None,
    engine="python",
    encoding="latin1",
    dtype=str,
    usecols=columns,
    chunksize=100_000
):
    total += len(chunk)

    for col in columns:
        values = chunk[col].fillna("<VAZIO>").str.strip()
        counts[col].update(values.value_counts().to_dict())

print(f"\nTotal de registros: {total:,}")

for col in columns:
    print(f"\n{'=' * 45}")
    print(f"VARIÁVEL: {col}")
    print(f"{'=' * 45}")

    for value, quantity in counts[col].most_common(20):
        percentage = quantity / total * 100
        print(f"{value:15} {quantity:12,} ({percentage:6.2f}%)")

print("\nAUDITORIA DE ÓBITOS")

deaths = sum(
    counts["EVOLUCAO"][code]
    for code in ["2", "3", "4"]
)

dates = total - counts["DT_OBITO"]["<VAZIO>"]

print(f"Evoluções 2, 3 ou 4: {deaths:,}")
print(f"Registros com data de óbito: {dates:,}")

print("\nAuditoria concluída!")
