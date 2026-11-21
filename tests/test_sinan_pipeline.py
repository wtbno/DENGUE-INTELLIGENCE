import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.processing.sinan_pipeline import (
    build_quality_summary,
    build_storage_recommendation,
    clean_missing_values,
    discover_years,
    identify_duplicates,
    validate_ibge_municipality_codes,
    validate_schema,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "sinan"


def test_discover_years_detects_available_sinan_files():
    years = discover_years(RAW_DIR)
    assert 2020 in years
    assert 2025 in years
    assert all(year >= 2020 for year in years)


def test_build_quality_summary_counts_indicators():
    frame = pd.DataFrame(
        {
            "CLASSI_FIN": ["10", "11", "12", "5", "10"],
            "EVOLUCAO": ["1", "2", "2", "3", "2"],
            "ID_MN_RESI": ["110001", "110002", "110003", None, "110005"],
        }
    )

    summary = build_quality_summary(frame)

    assert summary["records"] == 5
    assert summary["is_dengue"] == 4
    assert summary["is_alarm_signs"] == 1
    assert summary["is_severe_dengue"] == 1
    assert summary["is_discarded"] == 1
    assert summary["is_dengue_death"] == 3


def test_validate_schema_and_clean_missing_data():
    frame = pd.DataFrame(
        {
            "CLASSI_FIN": ["10", None],
            "EVOLUCAO": ["2", "1"],
            "ID_MN_RESI": ["110001", None],
        }
    )

    schema = validate_schema(frame, ["CLASSI_FIN", "EVOLUCAO", "ID_MN_RESI"])
    cleaned = clean_missing_values(frame)

    assert schema["valid"] is True
    assert cleaned["CLASSI_FIN"].iloc[1] == ""
    assert cleaned["ID_MN_RESI"].iloc[1] == ""


def test_identify_duplicates_and_ibge_validation():
    frame = pd.DataFrame(
        {
            "ID_MN_RESI": ["110001", "110001", "110002"],
            "DT_SIN_PRI": ["2020-01-01", "2020-01-01", "2020-01-02"],
            "CLASSI_FIN": ["10", "10", "11"],
        }
    )

    duplicates = identify_duplicates(frame, ["ID_MN_RESI", "DT_SIN_PRI", "CLASSI_FIN"])
    ibge_reference = pd.DataFrame({"ID_SINAN": ["110001", "110002"]})
    ibge_validation = validate_ibge_municipality_codes(frame, ibge_reference)

    assert duplicates["duplicate_rows"] == 2
    assert ibge_validation["matched_codes"] == 2
    assert ibge_validation["unmatched_codes"] == 0


def test_storage_recommendation_is_explicit():
    recommendation = build_storage_recommendation()

    assert "PostgreSQL" in recommendation["recommended_stack"][1]
    assert "Parquet" in recommendation["recommended_stack"][0]
    assert "final_recommendation" in recommendation
