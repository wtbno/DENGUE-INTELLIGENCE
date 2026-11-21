
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "raw" / "sinan"

file = next(
    f for f in DATA_DIR.rglob("*")
    if f.name.upper() == "DENGBR20.CSV"
)

columns = ["EVOLUCAO", "DT_OBITO", "CLASSI_FIN"]

parts = []

for chunk in pd.read_csv(
    file,
    sep=None,
    engine="python",
    encoding="latin1",
    dtype=str,
    usecols=columns,
    chunksize=100_000
):
    parts.append(chunk)

df = pd.concat(parts, ignore_index=True)

df["EVOLUCAO"] = df["EVOLUCAO"].fillna("<VAZIO>").str.strip()
df["DT_OBITO"] = df["DT_OBITO"].fillna("").str.strip()

df["TEM_DATA_OBITO"] = df["DT_OBITO"].ne("")

print("\nEVOLUÇÃO X DATA DE ÓBITO")
print(
    pd.crosstab(
        df["EVOLUCAO"],
        df["TEM_DATA_OBITO"],
        margins=True
    )
)

print("\nREGISTROS COM DATA DE ÓBITO E EVOLUÇÃO DIFERENTE DE 2, 3 OU 4")

inconsistentes = df[
    df["TEM_DATA_OBITO"]
    & ~df["EVOLUCAO"].isin(["2", "3", "4"])
]

print(inconsistentes.to_string(index=False))
print(f"\nTotal: {len(inconsistentes)}")

print("\nCLASSIFICAÇÃO FINAL 8")
print(
    df[df["CLASSI_FIN"] == "8"]["EVOLUCAO"]
    .value_counts(dropna=False)
)
