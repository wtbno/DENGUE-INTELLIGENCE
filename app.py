
import streamlit as st
import pandas as pd
from pathlib import Path

from src.data_access.sinan_reader import (
    load_sinan,
    get_available_years,
)


st.set_page_config(
    page_title="Dengue Intelligence BR",
    page_icon="🦟",
    layout="wide",
)

ROOT = Path(__file__).resolve().parent
INDICATOR_DIR = ROOT / "reports" / "indicators"
IBGE_REFERENCE_PATH = ROOT / "data" / "reference" / "ibge" / "municipios.csv"


def normalize_code(value):
    if pd.isna(value):
        return None
    text = str(value).strip().replace(".0", "")
    return text or None


@st.cache_data(show_spinner="Carregando indicadores do dashboard...")
def load_indicator_tables():
    municipality_path = INDICATOR_DIR / "municipio_indicadores_anuais.csv"
    state_path = INDICATOR_DIR / "estado_indicadores_anuais.csv"

    municipality_df = pd.read_csv(municipality_path) if municipality_path.exists() else pd.DataFrame()
    state_df = pd.read_csv(state_path) if state_path.exists() else pd.DataFrame()

    if not municipality_df.empty:
        municipality_df["year"] = municipality_df["year"].astype(int)
        municipality_df["ID_MN_RESI"] = municipality_df["ID_MN_RESI"].map(normalize_code)
        for column in [
            "total_notifications",
            "probable_cases",
            "alarm_signs",
            "severe_dengue",
            "dengue_deaths",
            "fatality_rate",
            "incidence_per_100k",
        ]:
            if column in municipality_df.columns:
                municipality_df[column] = pd.to_numeric(municipality_df[column], errors="coerce").fillna(0)

    if not state_df.empty:
        state_df["year"] = state_df["year"].astype(int)
        for column in [
            "total_notifications",
            "probable_cases",
            "alarm_signs",
            "severe_dengue",
            "dengue_deaths",
            "fatality_rate",
            "incidence_per_100k",
        ]:
            if column in state_df.columns:
                state_df[column] = pd.to_numeric(state_df[column], errors="coerce").fillna(0)

    if not municipality_df.empty and IBGE_REFERENCE_PATH.exists():
        ibge = pd.read_csv(IBGE_REFERENCE_PATH, dtype=str)
        ibge["ID_MN_RESI"] = ibge["ID_SINAN"].map(normalize_code)
        municipality_df = municipality_df.merge(
            ibge[["ID_MN_RESI", "MUNICIPIO", "UF", "SIGLA_UF", "REGIAO"]].drop_duplicates(),
            on="ID_MN_RESI",
            how="left",
        )

    return municipality_df, state_df


@st.cache_data(show_spinner="Carregando dados epidemiológicos...")
def get_data(year):
    return load_sinan(year)


st.title("🦟 Dengue Intelligence BR")
st.caption("Plataforma de análise epidemiológica e monitoramento da dengue no Brasil")
st.divider()

municipality_df, state_df = load_indicator_tables()

available_years = sorted(set(get_available_years() + (municipality_df["year"].tolist() if not municipality_df.empty else [])))

if not available_years:
    st.warning("Nenhum dado processado encontrado. Execute primeiro o ETL do SINAN.")
    st.stop()

selected_years = st.sidebar.multiselect(
    "Ano epidemiológico",
    available_years,
    default=sorted(available_years)[-2:] if len(available_years) > 1 else [available_years[0]],
)

if not selected_years:
    selected_years = [available_years[0]]

state_options = []
if not state_df.empty and "SIGLA_UF" in state_df.columns:
    state_options = sorted(state_df["SIGLA_UF"].dropna().astype(str).unique().tolist())

selected_states = st.sidebar.multiselect("UF", state_options, default=state_options[:]) if state_options else []

municipality_options = []
if not municipality_df.empty and "MUNICIPIO" in municipality_df.columns:
    municipality_options = sorted(municipality_df["MUNICIPIO"].dropna().astype(str).unique().tolist())

selected_municipality = st.sidebar.selectbox(
    "Município",
    ["Todos"] + municipality_options,
    index=0,
)

st.sidebar.info(f"Dados disponíveis: {len(available_years)} ano(s)")

if municipality_df.empty or state_df.empty:
    st.info("Base agregada de indicadores não encontrada; o dashboard está usando a fonte Parquet do SINAN para manter a leitura funcional.")

filtered_municipality = municipality_df.copy()
filtered_state = state_df.copy()

if not filtered_municipality.empty:
    filtered_municipality = filtered_municipality[filtered_municipality["year"].isin(selected_years)]
    if selected_states:
        filtered_municipality = filtered_municipality[filtered_municipality["SIGLA_UF"].isin(selected_states)] if "SIGLA_UF" in filtered_municipality.columns else filtered_municipality
    if selected_municipality != "Todos":
        filtered_municipality = filtered_municipality[filtered_municipality["MUNICIPIO"].astype(str).str.contains(selected_municipality, case=False, na=False)] if "MUNICIPIO" in filtered_municipality.columns else filtered_municipality

if not filtered_state.empty:
    filtered_state = filtered_state[filtered_state["year"].isin(selected_years)]
    if selected_states:
        filtered_state = filtered_state[filtered_state["SIGLA_UF"].isin(selected_states)] if "SIGLA_UF" in filtered_state.columns else filtered_state

if municipality_df.empty and state_df.empty:
    try:
        df = get_data(selected_years[0])
    except Exception as exc:
        st.error(f"Erro ao carregar os dados: {exc}")
        st.stop()

    total_records = len(df)
    total_dengue = int(df["IS_DENGUE"].fillna(False).sum())
    alarm_signs = int(df["IS_ALARM_SIGNS"].fillna(False).sum())
    severe_dengue = int(df["IS_SEVERE_DENGUE"].fillna(False).sum())
    dengue_deaths = int(df["IS_DENGUE_DEATH"].fillna(False).sum())

    st.subheader(f"Visão geral — {', '.join(map(str, selected_years))}")
    st.caption("Indicadores calculados diretamente a partir do SINAN processado.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Registros classificados como dengue", f"{total_dengue:,}".replace(",", "."))
    col2.metric("Sinais de alarme", f"{alarm_signs:,}".replace(",", "."))
    col3.metric("Dengue grave", f"{severe_dengue:,}".replace(",", "."))
    col4.metric("Óbitos por dengue", f"{dengue_deaths:,}".replace(",", "."))

    st.divider()
    st.subheader("Evolução temporal dos casos")
    temporal_df = df[["DT_SIN_PRI_DATE", "IS_DENGUE"]].copy()
    temporal_df["DT_SIN_PRI_DATE"] = pd.to_datetime(temporal_df["DT_SIN_PRI_DATE"], errors="coerce")
    temporal_df = temporal_df.dropna(subset=["DT_SIN_PRI_DATE"]) 
    temporal_df = temporal_df[temporal_df["IS_DENGUE"].fillna(False)]
    if not temporal_df.empty:
        temporal_df["MES"] = temporal_df["DT_SIN_PRI_DATE"].dt.to_period("M").dt.to_timestamp()
        monthly_cases = temporal_df.groupby("MES").size().reset_index(name="CASOS")
        st.line_chart(monthly_cases.set_index("MES"), y="CASOS")
    else:
        st.info("Não há datas válidas para construir o gráfico")

    st.divider()
    st.subheader("Informações da base processada")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de registros", f"{total_records:,}".replace(",", "."))
    col2.metric("Variáveis carregadas", len(df.columns))
    col3.metric("Municípios de residência", int(df["ID_MN_RESI"].nunique()))
else:
    if filtered_municipality.empty and filtered_state.empty:
        st.warning("Nenhum registro encontrado para os filtros selecionados.")
        st.stop()

    metrics_total_notifications = int(filtered_municipality["total_notifications"].sum()) if not filtered_municipality.empty else 0
    metrics_probable_cases = int(filtered_municipality["probable_cases"].sum()) if not filtered_municipality.empty else int(filtered_state["probable_cases"].sum())
    metrics_alarm_signs = int(filtered_municipality["alarm_signs"].sum()) if not filtered_municipality.empty else int(filtered_state["alarm_signs"].sum())
    metrics_severe_dengue = int(filtered_municipality["severe_dengue"].sum()) if not filtered_municipality.empty else int(filtered_state["severe_dengue"].sum())
    metrics_deaths = int(filtered_municipality["dengue_deaths"].sum()) if not filtered_municipality.empty else int(filtered_state["dengue_deaths"].sum())

    st.subheader(f"Visão geral agregada — {', '.join(map(str, selected_years))}")
    st.caption("Indicadores combinados por município e UF a partir dos CSVs gerados pela etapa analítica.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Notificações totais", f"{metrics_total_notifications:,}".replace(",", "."))
    col2.metric("Casos prováveis", f"{metrics_probable_cases:,}".replace(",", "."))
    col3.metric("Dengue grave", f"{metrics_severe_dengue:,}".replace(",", "."))
    col4.metric("Óbitos por dengue", f"{metrics_deaths:,}".replace(",", "."))

    st.divider()
    st.subheader("Tendência anual")
    if not filtered_state.empty:
        annual_trend = filtered_state.groupby("year", as_index=False)["probable_cases"].sum().sort_values("year")
        st.line_chart(annual_trend.set_index("year"), y="probable_cases")
    else:
        st.info("Sem dados estaduais para construir a tendência anual.")

    st.divider()
    st.subheader("Top municípios por casos prováveis")
    if not filtered_municipality.empty:
        top_municipalities = (
            filtered_municipality.groupby(["MUNICIPIO"], as_index=False)["probable_cases"].sum()
            .sort_values("probable_cases", ascending=False)
            .head(10)
        )
        st.bar_chart(top_municipalities.set_index("MUNICIPIO"), y="probable_cases")
    else:
        st.info("Sem município filtrado para exibir o ranking.")

    st.divider()
    st.subheader("Comparativo por UF")
    if not filtered_state.empty:
        state_comparison = filtered_state[["SIGLA_UF", "probable_cases", "dengue_deaths", "fatality_rate"]].sort_values("probable_cases", ascending=False)
        st.dataframe(state_comparison, use_container_width=True)
    else:
        st.info("Sem dados por UF para exibir a comparação.")

    st.divider()
    st.info("Denominadores populacionais ainda não foram incorporados em uma base estruturada; quando houver a fonte correta, a incidência por 100 mil será calculada automaticamente e integrada ao painel.")
