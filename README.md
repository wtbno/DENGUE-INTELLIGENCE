# DENGUE INTELLIGENCE BR

Plataforma aberta de Engenharia de Dados e Ciência de Dados para organizar, analisar e visualizar notificações de dengue no Brasil.

O projeto utiliza dados históricos do Sistema de Informação de Agravos de Notificação (SINAN), dados municipais do IBGE e fontes complementares para transformar registros públicos em indicadores epidemiológicos rastreáveis, úteis à vigilância em saúde e à tomada de decisão.

## Por que analisar dados epidemiológicos da dengue?

A dengue é uma doença sensível ao tempo, ao território e às condições ambientais. Uma análise consistente permite acompanhar a intensidade da transmissão, identificar padrões sazonais, comparar regiões e orientar ações de prevenção antes que os casos se transformem em surtos.

A qualidade dessa análise depende de dados bem padronizados. Mesmo informações públicas podem apresentar divergências de preenchimento, códigos municipais, categorias diagnósticas e ausência de registros ao longo dos anos. Por isso, este projeto não apenas calcula gráficos: ele investiga a origem, a integridade e as limitações dos dados antes de produzir resultados.

Entre os usos epidemiológicos mais importantes estão:

- monitorar o número de notificações e casos ao longo do tempo;
- estimar a incidência em relação à população municipal e estadual;
- acompanhar óbitos e taxas de letalidade;
- identificar municípios e estados com maior concentração de casos;
- reconhecer períodos sazonais e mudanças entre anos;
- apoiar estudos sobre clima, mobilidade, vulnerabilidade e transmissão;
- fornecer uma base organizada para modelos preditivos responsáveis;
- comunicar informações com transparência sobre qualidade e incertezas.

Os resultados devem ser interpretados como instrumentos de apoio à vigilância e à investigação epidemiológica, não como diagnósticos individuais ou substitutos de critérios oficiais do Ministério da Saúde.

## Objetivo do projeto

Construir uma plataforma completa de inteligência epidemiológica capaz de:

1. preservar os dados brutos originais;
2. padronizar diferentes estruturas anuais do SINAN;
3. validar códigos municipais e informações geográficas;
4. identificar duplicidades, valores ausentes e inconsistências;
5. gerar dados analíticos em formato Parquet;
6. calcular indicadores epidemiológicos documentados;
7. disponibilizar análises interativas em Streamlit;
8. manter rastreabilidade entre dados brutos, processamento e relatórios;
9. preparar uma base confiável para Machine Learning.

## Estado atual

### Dados e engenharia

- estrutura organizada por dados brutos, dados processados, relatórios e referência;
- arquivos históricos do SINAN disponíveis na estrutura de dados;
- pipeline reutilizável para processamento anual em `src/processing/sinan_pipeline.py`;
- leitura e inspeção de bases SINAN em módulos específicos;
- enriquecimento com códigos e informações municipais;
- geração de relatórios de qualidade e indicadores;
- armazenamento analítico em Parquet;
- testes automatizados para o pipeline e os indicadores epidemiológicos.

### Dashboard

A aplicação Streamlit já possui módulos para:

- visão geral;
- explorador do SINAN;
- qualidade dos dados;
- análise temporal;
- análise geográfica;
- integração com o InfoDengue;
- exploração de resultados de Machine Learning.

### Próximas prioridades

- concluir a validação dos schemas entre os anos disponíveis;
- confirmar critérios de classificação, outliers e valores ausentes;
- revisar a cobertura e consistência geográfica;
- consolidar e documentar os indicadores epidemiológicos;
- validar os denominadores populacionais do IBGE;
- definir a estratégia de persistência entre Parquet e PostgreSQL;
- avaliar modelos somente após a consolidação da qualidade dos dados.

## Arquitetura da solução

```text
data/raw
    Dados originais preservados
        |
data/processed
    Dados padronizados e analíticos em Parquet
        |
src/processing
    Limpeza, validação, enriquecimento e indicadores
        |
reports
    Resumos de qualidade, logs e indicadores agregados
        |
dashboard
    Visualização interativa e exploração dos resultados
```

O projeto mantém uma separação clara entre:

- **dados brutos**: origem histórica que não deve ser sobrescrita;
- **dados processados**: bases padronizadas para análise;
- **processamento**: regras de limpeza e transformação;
- **relatórios**: evidências de qualidade e rastreabilidade;
- **apresentação**: interface interativa para exploração.

## Indicadores epidemiológicos planejados

Os indicadores serão apresentados com fórmulas, critérios e limitações documentadas. Entre eles:

- total de notificações;
- casos classificados como prováveis segundo critérios epidemiológicos definidos;
- casos graves;
- óbitos;
- taxa de letalidade;
- incidência por 100 mil habitantes;
- evolução mensal e anual;
- distribuição por município, estado e região;
- concentração geográfica e padrões sazonais.

Exemplos conceituais:

```text
Incidência por 100 mil habitantes = casos da população / população residente × 100.000
Taxa de letalidade = óbitos confirmados / casos confirmados × 100
```

Nenhuma fórmula deve ser aplicada sem considerar a cobertura, o tipo de caso e a qualidade dos registros usados no cálculo.

## Estrutura do repositório

- `app.py` — entrada principal da aplicação Streamlit.
- `dashboard/` — páginas e componentes visuais.
- `src/` — leitura, ingestão, processamento e utilitários.
- `data/raw/` — dados públicos originais.
- `data/processed/` — bases padronizadas em Parquet.
- `data/reference/` — referências auxiliares, como municípios do IBGE.
- `reports/` — indicadores, qualidade e logs gerados.
- `models/` — artefatos de modelos quando forem consolidados.
- `notebooks/` — exploração, limpeza e experimentação.
- `tests/` — testes automatizados do projeto.
- `requirements.txt` — dependências Python.

## Como executar

Crie e ative um ambiente virtual:

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute a aplicação:

```bash
streamlit run app.py
```

Execute os testes:

```bash
pytest
```

## Qualidade e rastreabilidade

Antes de interpretar um indicador, o projeto busca validar:

- consistência dos nomes e tipos das colunas;
- valores ausentes;
- duplicidades;
- formatos e códigos municipais;
- coerência temporal;
- divergências entre anos;
- registros fora de padrões epidemiológicos esperados;
- capacidade de reproduzir os dados processados.

Os dados brutos não devem ser sobrescritos. Dados derivados, relatórios e logs são considerados artefatos gerados e podem ser reproduzidos por meio do pipeline.

## Estratégia para Machine Learning

Modelos preditivos serão desenvolvidos somente após consolidar dados suficientes e verificar sua qualidade. A estratégia deverá:

- utilizar validação temporal;
- evitar vazamento de dados;
- comparar modelos simples como referência;
- avaliar regressões, Random Forest e abordagens de séries temporais;
- considerar métricas como MAE, RMSE e MAPE, quando apropriadas;
- testar a contribuição de variáveis climáticas e geográficas;
- registrar limitações, períodos de treinamento e incertezas.

Um bom modelo epidemiológico não depende apenas da capacidade preditiva: também precisa ter dados representativos, critérios claros e interpretação compatível com o fenômeno observado.

## Tecnologias

- Python
- Pandas e NumPy
- PyArrow
- Streamlit
- Plotly
- Scikit-learn
- SQLAlchemy
- pytest
- Jupyter Notebook

## Regras de desenvolvimento

1. trabalhar em etapas pequenas e independentes;
2. não sobrescrever dados brutos;
3. não remover funcionalidades existentes sem justificativa;
4. não inventar informações ou resultados;
5. documentar alterações de dados e decisões técnicas;
6. criar testes para novos módulos;
7. atualizar as dependências quando necessário;
8. manter compatibilidade com Windows;
9. registrar riscos e limitações;
10. atualizar este README conforme o projeto evoluir.

## Próximo passo recomendado

Concluir a validação da Fase 1:

- confirmar todos os anos processados;
- comparar schemas e diferenças de estrutura;
- verificar os Parquets gerados;
- revisar relatórios e logs de qualidade;
- executar a suíte de testes;
- registrar pendências antes da consolidação dos indicadores.

Depois dessa etapa, o projeto poderá avançar com maior segurança para a engenharia analítica, os indicadores epidemiológicos e a interface pública de dados.
