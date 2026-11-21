
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "raw" / "sinan"
REPORT_DIR = ROOT / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Localizar arquivos CSV
files = sorted(
    f for f in DATA_DIR.rglob("*")
    if f.is_file() and f.suffix.lower() == ".csv"
)

if not files:
    raise FileNotFoundError("Nenhum CSV encontrado na pasta SINAN.")

print("\nARQUIVOS SINAN DISPONÍVEIS:\n")

for i, file in enumerate(files):
    size_mb = file.stat().st_size / (1024 ** 2)
    print(f"[{i}] {file.name} — {size_mb:.2f} MB")

index = int(input("\nDigite o número do arquivo que deseja analisar: "))

selected = files[index]

print(f"\nAnalisando: {selected.name}")
print("Carregando amostra de até 50 mil registros...\n")

df = pd.read_csv(
    selected,
    sep=None,
    engine="python",
    encoding="latin1",
    dtype=str,
    nrows=50000,
    on_bad_lines="warn"
)

# Perfil das variáveis
profile = pd.DataFrame({
    "variavel": df.columns,
    "tipo": df.dtypes.astype(str).values,
    "preenchidos": df.notna().sum().values,
    "ausentes": df.isna().sum().values,
    "percentual_ausente": (
        df.isna().mean().values * 100
    ).round(2),
    "valores_distintos_amostra": (
        df.nunique(dropna=True).values
    )
})

# Exemplos de valores
profile["exemplos"] = [
    " | ".join(
        df[col].dropna().astype(str).unique()[:5]
    )
    for col in df.columns
]

profile = profile.sort_values(
    "percentual_ausente",
    ascending=False
)

output = REPORT_DIR / f"perfil_{selected.stem}.csv"
profile.to_csv(output, index=False, encoding="utf-8-sig")

print("RESUMO DA AMOSTRA")
print(f"Registros analisados: {len(df):,}")
print(f"Variáveis encontradas: {len(df.columns)}")

print("\nPERFIL DAS VARIÁVEIS:")
print(profile.to_string(index=False))

print(f"\nRelatório salvo em: {output}")
