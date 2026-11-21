from typing import Optional, List
from pathlib import Path
import pandas as pd


# Localiza automaticamente a raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parents[2]

SINAN_PROCESSED_DIR = (
    PROJECT_ROOT / "data" / "processed" / "sinan"
)


# Colunas necessárias para os primeiros indicadores do dashboard
OVERVIEW_COLUMNS = [
    "DT_SIN_PRI_DATE",
    "ID_MN_RESI",
    "CLASSI_FIN",
    "EVOLUCAO",
    "IS_DENGUE",
    "IS_ALARM_SIGNS",
    "IS_SEVERE_DENGUE",
    "IS_DISCARDED",
    "IS_DENGUE_DEATH",
]


def get_sinan_path(year: int) -> Path:
    """Retorna o caminho do Parquet de determinado ano."""

    short_year = str(year)[-2:]

    return (
        SINAN_PROCESSED_DIR
        / str(year)
        / f"DENGBR{short_year}.parquet"
    )


def get_available_years() -> list[int]:
    """Identifica os anos com arquivos Parquet disponíveis."""

    years = []

    if not SINAN_PROCESSED_DIR.exists():
        return years

    for file in SINAN_PROCESSED_DIR.glob("*/DENGBR*.parquet"):
        try:
            years.append(int(file.parent.name))
        except ValueError:
            continue

    return sorted(set(years))


def load_sinan(
    year: int,
    columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """Carrega os dados processados do SINAN."""

    file_path = get_sinan_path(year)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Arquivo Parquet não encontrado: {file_path}"
        )

    return pd.read_parquet(
        file_path,
        columns=columns or OVERVIEW_COLUMNS
    )
