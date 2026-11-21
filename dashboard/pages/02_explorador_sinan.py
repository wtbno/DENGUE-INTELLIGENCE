
import streamlit as st
import pandas as pd

from pathlib import Path

st.set_page_config(
    page_title="Explorador SINAN",
    page_icon="🔬",
    layout="wide"
)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "raw" / "sinan"

st.title("🔬 Explorador de dados SINAN")
st.caption("Inspeção dos microdados epidemiológicos de dengue")

st.divider()

# Localização dos arquivos
files = list(DATA_DIR.rglob("*.csv"))

if not files:
    st.warning("Nenhum arquivo CSV encontrado na pasta SINAN.")
    st.stop()

# Seleção do arquivo
file_options = {
    f"{file.parent.name} | {file.name}": file
    for file in files
}

selected_file = st.selectbox(
    "Selecione o arquivo:",
    options=list(file_options.keys())
)

file_path = file_options[selected_file]

@st.cache_data(show_spinner="Carregando microdados...")
def load_data(path):

    for encoding in ["latin1", "utf-8", "utf-8-sig"]:

        try:
            return pd.read_csv(
                path,
                sep=";",
                encoding=encoding,
                dtype=str,
                low_memory=False
            )

        except UnicodeDecodeError:
            continue

    raise ValueError("Não foi possível identificar a codificação.")

try:

    df = load_data(str(file_path))

    # Indicadores
    col1, col2, col3 = st.columns(3)

    col1.metric("Registros", f"{len(df):,}")
    col2.metric("Variáveis", len(df.columns))
    col3.metric(
        "Tamanho",
        f"{file_path.stat().st_size / 1024**2:.2f} MB"
    )

    st.divider()

    # Visualização
    st.subheader("Amostra dos registros")

    limit = st.slider(
        "Quantidade de registros:",
        min_value=5,
        max_value=100,
        value=20
    )

    st.dataframe(
        df.head(limit),
        use_container_width=True,
        hide_index=True
    )

    # Estrutura
    st.subheader("Dicionário de variáveis")

    schema = pd.DataFrame({
        "Variável": df.columns,
        "Tipo": df.dtypes.astype(str).values,
        "Valores preenchidos": df.notna().sum().values,
        "Valores ausentes": df.isna().sum().values
    })

    st.dataframe(
        schema,
        use_container_width=True,
        hide_index=True
    )

    # Pesquisa
    st.subheader("Pesquisar registros")

    column = st.selectbox(
        "Selecione uma variável:",
        options=df.columns
    )

    search = st.text_input("Digite um valor para pesquisar:")

    if search:

        result = df[
            df[column].fillna("").str.contains(
                search,
                case=False,
                regex=False
            )
        ]

        st.write(f"Registros encontrados: {len(result):,}")

        st.dataframe(
            result.head(500),
            use_container_width=True
        )

    # Estatísticas
    st.subheader("Resumo estatístico")

    st.write(df.describe(include="all").T)

except Exception as error:

    st.error(f"Erro ao carregar os dados: {error}")
