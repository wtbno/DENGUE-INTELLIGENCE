from __future__ import annotations

from typing import Any, Iterable

import pandas as pd


def _normalize_municipality_codes(series: pd.Series) -> pd.Series:
    return (
        series
        .astype("string")
        .str.strip()
        .str.replace(r"\D+", "", regex=True)
        .str.zfill(6)
    )


def build_epidemiological_indicators(
    frame: pd.DataFrame,
    population: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Calcula indicadores epidemiológicos básicos para um dataset SINAN.

    Args:
        frame: DataFrame processado com indicadores do SINAN.
        population: DataFrame opcional com colunas `ID_MN_RESI` e `POPULACAO`.

    Returns:
        Dicionário com totais, taxas e agregação por mês.
    """
    working = frame.copy()

    if "ID_MN_RESI" in working.columns:
        working["ID_MN_RESI"] = _normalize_municipality_codes(working["ID_MN_RESI"])

    if "DT_SIN_PRI_DATE" in working.columns:
        working["DT_SIN_PRI_DATE"] = pd.to_datetime(
            working["DT_SIN_PRI_DATE"],
            errors="coerce",
        )
    elif "DT_SIN_PRI" in working.columns:
        working["DT_SIN_PRI_DATE"] = pd.to_datetime(
            working["DT_SIN_PRI"],
            errors="coerce",
        )

    total_notifications = int(len(working))
    probable_cases = int(working["IS_DENGUE"].fillna(False).astype(bool).sum()) if "IS_DENGUE" in working.columns else 0
    alarm_signs = int(working["IS_ALARM_SIGNS"].fillna(False).astype(bool).sum()) if "IS_ALARM_SIGNS" in working.columns else 0
    severe_dengue = int(working["IS_SEVERE_DENGUE"].fillna(False).astype(bool).sum()) if "IS_SEVERE_DENGUE" in working.columns else 0
    dengue_deaths = int(working["IS_DENGUE_DEATH"].fillna(False).astype(bool).sum()) if "IS_DENGUE_DEATH" in working.columns else 0
    fatality_rate = round((dengue_deaths / probable_cases) * 100, 2) if probable_cases else 0.0

    population_total = 0
    if population is not None:
        pop = population.copy()
        if "ID_MN_RESI" in pop.columns:
            pop["ID_MN_RESI"] = _normalize_municipality_codes(pop["ID_MN_RESI"])
        pop_value_column = "POPULACAO" if "POPULACAO" in pop.columns else "POPULATION"
        population_total = int(pop[pop_value_column].fillna(0).sum())

    incidence_per_100k = round((probable_cases / population_total) * 100_000, 2) if population_total else 0.0

    if "DT_SIN_PRI_DATE" in working.columns:
        valid_dates = working[working["DT_SIN_PRI_DATE"].notna()].copy()
        if not valid_dates.empty:
            monthly_counts = (
                valid_dates.loc[valid_dates["IS_DENGUE"].fillna(False), "DT_SIN_PRI_DATE"]
                .dt.to_period("M")
                .astype(str)
                .value_counts()
                .sort_index()
            )
            first_month = monthly_counts.index.min()
            last_month = monthly_counts.index.max()
            months = pd.period_range(start=first_month, end=last_month, freq="M")
            month_map = {period.strftime("%Y-%m"): 0 for period in months}
            month_map.update({key: int(value) for key, value in monthly_counts.items()})
            cases_by_month = dict(sorted(month_map.items()))
        else:
            cases_by_month = {}
    else:
        cases_by_month = {}

    municipality_summary = None
    if "ID_MN_RESI" in working.columns:
        municipality_summary = (
            working.groupby("ID_MN_RESI").agg(
                total_notifications=("ID_MN_RESI", "size"),
                probable_cases=("IS_DENGUE", lambda values: int(values.fillna(False).sum())),
                alarm_signs=("IS_ALARM_SIGNS", lambda values: int(values.fillna(False).sum())),
                severe_dengue=("IS_SEVERE_DENGUE", lambda values: int(values.fillna(False).sum())),
                dengue_deaths=("IS_DENGUE_DEATH", lambda values: int(values.fillna(False).sum())),
            ).reset_index()
        )

    return {
        "total_notifications": total_notifications,
        "probable_cases": probable_cases,
        "alarm_signs": alarm_signs,
        "severe_dengue": severe_dengue,
        "dengue_deaths": dengue_deaths,
        "fatality_rate": fatality_rate,
        "incidence_per_100k": incidence_per_100k,
        "population_total": population_total,
        "cases_by_month": cases_by_month,
        "municipality_summary": municipality_summary,
    }


def build_annual_municipality_summary(
    frame: pd.DataFrame,
    population: pd.DataFrame | None = None,
    year: int | str | None = None,
) -> pd.DataFrame:
    """Agrupa indicadores por município e ano."""
    working = frame.copy()
    if "ID_MN_RESI" in working.columns:
        working["ID_MN_RESI"] = _normalize_municipality_codes(working["ID_MN_RESI"])
    else:
        return pd.DataFrame(columns=["year", "ID_MN_RESI", "total_notifications", "probable_cases", "alarm_signs", "severe_dengue", "dengue_deaths", "fatality_rate", "incidence_per_100k"])

    if "DT_SIN_PRI_DATE" not in working.columns and "DT_SIN_PRI" in working.columns:
        working["DT_SIN_PRI_DATE"] = pd.to_datetime(working["DT_SIN_PRI"], errors="coerce")

    if year is not None:
        working["year"] = int(year)
    elif "year" in working.columns:
        working["year"] = working["year"].astype(int)
    else:
        if "DT_SIN_PRI_DATE" in working.columns:
            working["year"] = working["DT_SIN_PRI_DATE"].dt.year
        else:
            working["year"] = 0

    grouped = (
        working.groupby(["year", "ID_MN_RESI"], dropna=False).agg(
            total_notifications=("ID_MN_RESI", "size"),
            probable_cases=("IS_DENGUE", lambda values: int(values.fillna(False).sum())),
            alarm_signs=("IS_ALARM_SIGNS", lambda values: int(values.fillna(False).sum())),
            severe_dengue=("IS_SEVERE_DENGUE", lambda values: int(values.fillna(False).sum())),
            dengue_deaths=("IS_DENGUE_DEATH", lambda values: int(values.fillna(False).sum())),
        ).reset_index()
    )

    if population is not None:
        pop = population.copy()
        if "ID_MN_RESI" in pop.columns:
            pop["ID_MN_RESI"] = _normalize_municipality_codes(pop["ID_MN_RESI"])
        pop_value_column = "POPULACAO" if "POPULACAO" in pop.columns else "POPULATION"
        grouped = grouped.merge(
            pop[["ID_MN_RESI", pop_value_column]].rename(columns={pop_value_column: "POPULACAO"}),
            on="ID_MN_RESI",
            how="left",
        )
        grouped["incidence_per_100k"] = (
            grouped["probable_cases"] / grouped["POPULACAO"].fillna(0).replace(0, pd.NA)
        ) * 100_000
    else:
        grouped["POPULACAO"] = pd.NA
        grouped["incidence_per_100k"] = 0.0

    grouped["fatality_rate"] = pd.to_numeric(
        grouped["dengue_deaths"] / grouped["probable_cases"].replace(0, pd.NA) * 100,
        errors="coerce",
    ).fillna(0.0)

    grouped = grouped[[
        "year",
        "ID_MN_RESI",
        "total_notifications",
        "probable_cases",
        "alarm_signs",
        "severe_dengue",
        "dengue_deaths",
        "fatality_rate",
        "incidence_per_100k",
    ]]

    return grouped


def build_annual_state_summary(
    frame: pd.DataFrame,
    population: pd.DataFrame | None = None,
    year: int | str | None = None,
) -> pd.DataFrame:
    """Agrupa indicadores por unidade federativa e ano."""
    working = frame.copy()
    if "SIGLA_UF" not in working.columns and "UF" in working.columns:
        working["SIGLA_UF"] = working["UF"]

    if "SIGLA_UF" not in working.columns:
        return pd.DataFrame(columns=["year", "SIGLA_UF", "total_notifications", "probable_cases", "alarm_signs", "severe_dengue", "dengue_deaths", "fatality_rate", "incidence_per_100k"]) 

    if year is not None:
        working["year"] = int(year)
    elif "year" in working.columns:
        working["year"] = working["year"].astype(int)
    else:
        if "DT_SIN_PRI_DATE" in working.columns:
            working["year"] = working["DT_SIN_PRI_DATE"].dt.year
        else:
            working["year"] = 0

    grouped = (
        working.groupby(["year", "SIGLA_UF"], dropna=False).agg(
            total_notifications=("SIGLA_UF", "size"),
            probable_cases=("IS_DENGUE", lambda values: int(values.fillna(False).sum())),
            alarm_signs=("IS_ALARM_SIGNS", lambda values: int(values.fillna(False).sum())),
            severe_dengue=("IS_SEVERE_DENGUE", lambda values: int(values.fillna(False).sum())),
            dengue_deaths=("IS_DENGUE_DEATH", lambda values: int(values.fillna(False).sum())),
        ).reset_index()
    )

    if population is not None:
        pop = population.copy()
        if "SIGLA_UF" in pop.columns:
            pop = pop.groupby("SIGLA_UF", as_index=False).agg(POPULACAO=("POPULACAO", "sum"))
        elif "UF" in pop.columns:
            pop = pop.groupby("UF", as_index=False).agg(POPULACAO=("POPULACAO", "sum"))
            pop = pop.rename(columns={"UF": "SIGLA_UF"})
        grouped = grouped.merge(pop, on="SIGLA_UF", how="left")
        grouped["incidence_per_100k"] = (
            grouped["probable_cases"] / grouped["POPULACAO"].fillna(0).replace(0, pd.NA)
        ) * 100_000
    else:
        grouped["POPULACAO"] = pd.NA
        grouped["incidence_per_100k"] = 0.0

    grouped["fatality_rate"] = pd.to_numeric(
        grouped["dengue_deaths"] / grouped["probable_cases"].replace(0, pd.NA) * 100,
        errors="coerce",
    ).fillna(0.0)

    grouped = grouped[[
        "year",
        "SIGLA_UF",
        "total_notifications",
        "probable_cases",
        "alarm_signs",
        "severe_dengue",
        "dengue_deaths",
        "fatality_rate",
        "incidence_per_100k",
    ]]

    return grouped


def build_dashboard_indicators_dataset(
    years: Iterable[int] | None = None,
    processed_dir: str | None = None,
    population: pd.DataFrame | None = None,
    ibge_reference: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carrega dados processados por ano e monta a base agregada para dashboard."""
    from src.data_access.sinan_reader import get_available_years, load_sinan

    final_years = list(years) if years is not None else get_available_years()
    municipality_frames = []
    state_frames = []

    ibge = None
    if ibge_reference is not None:
        ibge = ibge_reference.copy()
        if "ID_SINAN" in ibge.columns:
            ibge["ID_MN_RESI"] = _normalize_municipality_codes(ibge["ID_SINAN"])
        elif "ID_MN_RESI" in ibge.columns:
            ibge["ID_MN_RESI"] = _normalize_municipality_codes(ibge["ID_MN_RESI"])

    for year in sorted(set(final_years)):
        try:
            frame = load_sinan(year)
        except Exception:
            continue

        if ibge is not None and "ID_MN_RESI" in frame.columns:
            enrich_columns = ["ID_MN_RESI"] + [col for col in ["SIGLA_UF", "UF", "REGIAO", "MUNICIPIO"] if col in ibge.columns]
            frame = frame.merge(
                ibge[enrich_columns].drop_duplicates(subset=["ID_MN_RESI"]),
                on="ID_MN_RESI",
                how="left",
            )

        municipality_frames.append(build_annual_municipality_summary(frame, population=population, year=year))
        state_frames.append(build_annual_state_summary(frame, population=population, year=year))

    municipality_summary = pd.concat(municipality_frames, ignore_index=True) if municipality_frames else pd.DataFrame()
    state_summary = pd.concat(state_frames, ignore_index=True) if state_frames else pd.DataFrame()

    return municipality_summary, state_summary
