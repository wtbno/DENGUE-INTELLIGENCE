import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.epidemiological_indicators import (
    build_annual_municipality_summary,
    build_annual_state_summary,
    build_epidemiological_indicators,
)


def test_build_epidemiological_indicators_calculates_core_metrics():
    frame = pd.DataFrame(
        {
            "ID_MN_RESI": ["110001", "110001", "110002", "110002", None],
            "DT_SIN_PRI_DATE": pd.to_datetime(
                [
                    "2024-01-05",
                    "2024-01-20",
                    "2024-02-02",
                    "2024-03-10",
                    "2024-03-15",
                ]
            ),
            "IS_DENGUE": [True, True, False, True, True],
            "IS_ALARM_SIGNS": [True, False, False, True, False],
            "IS_SEVERE_DENGUE": [False, True, False, False, False],
            "IS_DENGUE_DEATH": [False, True, False, False, False],
        }
    )

    population = pd.DataFrame(
        {
            "ID_MN_RESI": ["110001", "110002"],
            "POPULACAO": [1000, 1000],
        }
    )

    summary = build_epidemiological_indicators(frame, population)

    assert summary["total_notifications"] == 5
    assert summary["probable_cases"] == 4
    assert summary["alarm_signs"] == 2
    assert summary["severe_dengue"] == 1
    assert summary["dengue_deaths"] == 1
    assert summary["fatality_rate"] == 25.0
    assert summary["incidence_per_100k"] == 200.0
    assert summary["cases_by_month"]["2024-01"] == 2
    assert summary["cases_by_month"]["2024-02"] == 0


def test_build_annual_municipality_and_state_summary():
    frame = pd.DataFrame(
        {
            "ID_MN_RESI": ["110001", "110001", "110002"],
            "SIGLA_UF": ["RO", "RO", "SP"],
            "DT_SIN_PRI_DATE": pd.to_datetime(["2024-01-02", "2024-02-05", "2024-02-10"]),
            "IS_DENGUE": [True, True, False],
            "IS_ALARM_SIGNS": [False, True, False],
            "IS_SEVERE_DENGUE": [False, False, False],
            "IS_DENGUE_DEATH": [False, True, False],
        }
    )

    population = pd.DataFrame(
        {
            "ID_MN_RESI": ["110001", "110002"],
            "POPULACAO": [1000, 500],
        }
    )

    municipality_summary = build_annual_municipality_summary(frame, population=population, year=2024)
    state_summary = build_annual_state_summary(frame, population=pd.DataFrame({"SIGLA_UF": ["RO", "SP"], "POPULACAO": [1500, 500]}), year=2024)

    assert municipality_summary["probable_cases"].sum() == 2
    assert municipality_summary["dengue_deaths"].sum() == 1
    assert municipality_summary["incidence_per_100k"].iloc[0] == 200.0
    assert state_summary.loc[state_summary["SIGLA_UF"] == "RO", "probable_cases"].iloc[0] == 2
