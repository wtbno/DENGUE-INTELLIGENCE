
from pathlib import Path
from collections import Counter

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[2]

FILE = (
    ROOT
    / "data"
    / "processed"
    / "sinan"
    / "2020"
    / "DENGBR20.parquet"
)

if not FILE.exists():
    raise FileNotFoundError(FILE)

parquet = pq.ParquetFile(FILE)

total = 0
classification = Counter()
evolution = Counter()

metrics = Counter()
death_dates = 0

print("\nValidando Parquet SINAN 2020...\n")

for batch in parquet.iter_batches(batch_size=100_000):

    data = batch.to_pydict()
    total += batch.num_rows

    for value in data["CLASSI_FIN"]:
        classification[value if value is not None else "<VAZIO>"] += 1

    for value in data["EVOLUCAO"]:
        evolution[value if value is not None else "<VAZIO>"] += 1

    for flag in [
        "IS_DENGUE",
        "IS_ALARM_SIGNS",
        "IS_SEVERE_DENGUE",
        "IS_DISCARDED",
        "IS_DENGUE_DEATH",
        "DEATH_DATA_MISMATCH"
    ]:
        if flag in data:
            metrics[flag] += sum(
                value is True for value in data[flag]
            )

    if "DT_OBITO_DATE" in data:
        death_dates += sum(
            value is not None
            for value in data["DT_OBITO_DATE"]
        )


print("=" * 45)
print("RESULTADO DA VALIDAÇÃO")
print("=" * 45)

print(f"Registros: {total:,}")
print(f"Colunas: {len(parquet.schema.names)}")

print("\nClassificações:")
for code, quantity in classification.most_common():
    print(f"{code}: {quantity:,}")

print("\nIndicadores derivados:")
for name, quantity in metrics.items():
    print(f"{name}: {quantity:,}")

print(f"\nDatas de óbito válidas: {death_dates:,}")

# Comparações com a auditoria original
expected = {
    "registros": 1_495_117,
    "dengue": 793_010,
    "descartados": 538_654,
    "sinais_alarme": 9_578,
    "dengue_grave": 934,
    "obitos_dengue": 583,
    "inconsistencias_obito": 2,
    "datas_obito": 2_239
}

actual = {
    "registros": total,
    "dengue": metrics["IS_DENGUE"],
    "descartados": metrics["IS_DISCARDED"],
    "sinais_alarme": metrics["IS_ALARM_SIGNS"],
    "dengue_grave": metrics["IS_SEVERE_DENGUE"],
    "obitos_dengue": metrics["IS_DENGUE_DEATH"],
    "inconsistencias_obito": metrics["DEATH_DATA_MISMATCH"],
    "datas_obito": death_dates
}

print("\nCONFERÊNCIA:")

for key, expected_value in expected.items():

    actual_value = actual[key]
    status = "OK" if actual_value == expected_value else "DIVERGENTE"

    print(
        f"{key}: {actual_value:,} "
        f"| Esperado: {expected_value:,} "
        f"| {status}"
    )

if actual == expected:
    print("\nVALIDAÇÃO CONCLUÍDA COM SUCESSO!")
else:
    print("\nATENÇÃO: existem divergências para investigar.")
