"""Estatística Livre 0.2 — editor semelhante ao SPSS e relatórios reproduzíveis.

Executar: python -m streamlit run app.py
"""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import engine
import project_io
import reports
import schema as variaveis
from data_utils import ler_arquivo, to_csv_bytes, variaveis_numericas

st.set_page_config(page_title="Estatística Livre 0.2", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
BASE = Path(__file__).parent

st.markdown("""<style>
.block-container{padding-top:1.4rem;max-width:1550px}
h1{letter-spacing:-.04em;font-weight:750}h2,h3{letter-spacing:-.018em}
[data-testid='stMetric']{border:1px solid #dce8ec;border-radius:12px;padding:12px 16px;background:#f8fbfc}
[data-testid='stTabs'] button{font-size:14px;font-weight:600}
.stButton button[kind='primary']{border-radius:8px}
.small-note{font-size:.86rem;color:#60747f}
</style>""", unsafe_allow_html=True)


def iniciar():
    if "df" not in st.session_state:
        df = pd.read_csv(BASE / "exemplo_ficticio.csv")
        st.session_state.df = df
        st.session_state.schema = variaveis.criar_dicionario(df)
        st.session_state.dataset_nome = "Exemplo fictício · 18 participantes"
    if "schema" not in st.session_state:
        st.session_state.schema = variaveis.criar_dicionario(st.session_state.df)
    st.session_state.setdefault("revisao", 0)
    st.session_state.setdefault("historico", [])


def mudar_base(df: pd.DataFrame, nome: str, dic: dict | None = None):
    st.session_state.df = df.reset_index(drop=True)
    st.session_state.schema = dic if dic is not None else variaveis.criar_dicionario(st.session_state.df)
    st.session_state.dataset_nome = nome
    st.session_state.historico = []
    st.session_state.revisao += 1
    st.rerun()


def invalidar_historico():
    st.session_state.historico = []
    st.session_state.revisao += 1


def exibir_resultado(item: dict, alpha: float):
    if item.get("p") is not None:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Estatística", item.get("estatistica") or "—")
        col2.metric("p-valor", reports._ptexto(item["p"]))
        col3.metric("N utilizado", item.get("n", 0))
        col4.metric("α definido", str(alpha).replace(".", ","))
        if item.get("tipo") == "normalidade":
            texto = ("O teste encontrou evidência contra a hipótese de normalidade (p < α)." if item["p"] < alpha
                     else "Não houve evidência suficiente contra a normalidade (p ≥ α). Isso não comprova normalidade.")
        else:
            texto = ("Há evidência estatística contra a hipótese nula (p < α)." if item["p"] < alpha
                     else "Não houve evidência suficiente contra a hipótese nula (p ≥ α).")
        st.info(texto)
        if item.get("efeito"):
            st.write("**Tamanho do efeito:**", item["efeito"])
    tabela = item.get("tabela")
    if isinstance(tabela, pd.DataFrame) and not tabela.empty:
        st.dataframe(tabela, hide_index=True, use_container_width=True)
    if item.get("nota"):
        st.caption(item["nota"])


iniciar()
st.title("Estatística Livre")
st.caption("Versão 0.2  •  Dados e variáveis  /  Análises  /  Relatórios  •  Aplicativo independente, sem código IBM")

with st.sidebar:
    st.subheader("Seu projeto")
    st.caption(st.session_state.dataset_nome)
    st.caption("Salvo somente durante esta sessão, a menos que você exporte o projeto.")
    alpha = st.select_slider("Significância (α)", options=[0.01, 0.05, 0.10], value=0.05)
    st.divider()
    st.subheader("Importar dados")
    arquivo = st.file_uploader("Arquivo .csv ou .xlsx", type=["csv", "xlsx"], key="entrada_dados")
    sep = st.selectbox("Separador CSV", ["Automático", ";", ",", "Tabulação"], index=0)
    decimal = st.selectbox("Decimal CSV", ["Virgula", "Ponto"], index=0,
                           format_func=lambda s: "Vírgula (1,5)" if s == "Virgula" else "Ponto (1.5)")
    aba = 0
    if arquivo is not None and arquivo.name.lower().endswith(".xlsx"):
        try:
            with pd.ExcelFile(io.BytesIO(arquivo.getvalue()), engine="openpyxl") as xls:
                aba = st.selectbox("Aba do Excel", xls.sheet_names)
        except Exception as e:
            st.error(f"Não foi possível listar abas: {e}")
    if st.button("Importar arquivo", disabled=arquivo is None, use_container_width=True):
        try:
            mapa_sep = {"Automático": "automático", "Tabulação": "\t"}
            df_novo = ler_arquivo(arquivo, sep=mapa_sep.get(sep, sep),
                                  decimal="," if decimal == "Virgula" else ".", aba=aba)
            mudar_base(df_novo, f"{arquivo.name}" + (f" · {aba}" if isinstance(aba,str) else ""))
        except Exception as e:
            st.error(f"Erro na importação: {e}")
    c1, c2 = st.columns(2)
    if c1.button("Exemplo", use_container_width=True):
        mudar_base(pd.read_csv(BASE / "exemplo_ficticio.csv"), "Exemplo fictício · 18 participantes")
    if c2.button("Validação", use_container_width=True):
        mudar_base(pd.read_csv(BASE / "validacao_estatistica_ficticia.csv", sep=";", decimal=","),
                   "Validação fictícia · 60 registros")
    st.divider()
    st.subheader("Projeto salvo")
    projeto = st.file_uploader("Restaurar arquivo .elproj", type=["elproj"], key="upload_projeto")
    if st.button("Restaurar projeto", disabled=projeto is None, use_container_width=True):
        try:
            d, dic, nome = project_io.importar_projeto(projeto.getvalue())
            mudar_base(d, nome, dic)
        except ValueError as e:
            st.error(str(e))
    st.caption("As análises anteriores são apagadas ao alterar os dados ou o dicionário.")
    st.divider()
    st.caption("Uso local. Evite publicar bases com dados pessoais ou clínicos identificáveis.")

raw = st.session_state.df
schema = st.session_state.schema
analise = variaveis.preparar_analise(raw, schema)

r1, r2, r3, r4 = st.columns(4)
r1.metric("Casos / linhas", f"{len(raw):,}".replace(",", "."))
r2.metric("Variáveis", len(raw.columns))
r3.metric("Células ausentes", int(analise.isna().sum().sum()))
r4.metric("Análises registradas", len(st.session_state.historico))

aba_dados, aba_variaveis, aba_analises, aba_graficos, aba_relat = st.tabs(
    ["📋 Visão de dados", "🧩 Visão de variáveis", "∑ Análises", "📈 Gráficos", "📄 Relatórios"])

with aba_dados:
    st.subheader("Editor de dados")
    st.caption("Linhas = casos; colunas = variáveis. Edite as células e clique em **Aplicar mudanças** para gravar.")
    if st.checkbox("Visualizar rótulos de valores (somente leitura)", value=False, key="mostrar_rotulos"):
        visual = raw.copy()
        for col in visual.columns:
            m = variaveis.labels_valores(schema.get(str(col), {}).get("valores", ""))
            if m:
                visual[col] = visual[col].astype("string").map(lambda v: variaveis.rotulo_valor(v, m) if pd.notna(v) else v)
        st.dataframe(visual, use_container_width=True)
        st.caption("A edição continua sendo feita nos códigos originais abaixo.")
    editado = st.data_editor(raw, key=f"dados_{st.session_state.revisao}", num_rows="dynamic",
                             use_container_width=True, hide_index=False)
    diferencas = not editado.equals(raw)
    if diferencas:
        st.warning("Existem mudanças ainda não aplicadas. Elas não entram nas análises até você salvá-las.")
    bt1, bt2, bt3 = st.columns([1.3, 1.3, 1])
    if bt1.button("Aplicar mudanças", type="primary", disabled=not diferencas, use_container_width=True):
        if editado.columns.duplicated().any():
            st.error("Existem colunas com nomes duplicados.")
        else:
            novo_schema = {c: schema.get(c, variaveis.criar_dicionario(editado)[c]) for c in editado.columns}
            mudar_base(editado, st.session_state.dataset_nome, novo_schema)
    bt2.download_button("Baixar dados (.csv)", data=to_csv_bytes(raw), file_name="dados_estatistica_livre.csv",
                        mime="text/csv", use_container_width=True)
    with bt3:
        st.caption("Os dados brutos não são alterados por códigos de ausentes definidos no dicionário.")
    with st.expander("Adicionar ou excluir variáveis"):
        novo_nome = st.text_input("Nome da nova variável", placeholder="Ex.: copm_satisfacao", key="nome_col")
        c1, c2 = st.columns(2)
        if c1.button("Adicionar coluna", use_container_width=True):
            nome = novo_nome.strip()
            if not nome or nome in raw.columns:
                st.error("Informe um nome novo e não vazio.")
            else:
                d = raw.copy()
                d[nome] = pd.Series([float("nan")] * len(d))
                mudar_base(d, st.session_state.dataset_nome)
        excluir = c2.multiselect("Excluir variáveis", list(raw.columns), key="excluir_colunas")
        if st.button("Excluir variáveis selecionadas", disabled=not excluir):
            if len(excluir) == len(raw.columns):
                st.error("O projeto precisa ter ao menos uma variável.")
            else:
                d = raw.drop(columns=excluir)
                mudar_base(d, st.session_state.dataset_nome,
                           {c: schema[c] for c in d.columns})
    st.caption("Para renomear variáveis ou definir códigos de ausentes, use a guia 'Visão de variáveis'.")

with aba_variaveis:
    st.subheader("Dicionário de variáveis")
    st.caption("Edite nomes, rótulos, tipo, nível de medida e códigos ausentes (ex.: 99;999). "
               "Os rótulos dos valores usam o formato 0=Não;1=Sim.")
    dic_base = variaveis.tabela_dicionario(raw, schema)
    dic_ed = st.data_editor(dic_base, num_rows="fixed", hide_index=True,
                            key=f"dic_{st.session_state.revisao}", use_container_width=True,
                            column_config={
                                "Nome": st.column_config.TextColumn("Nome", required=True),
                                "Rótulo": st.column_config.TextColumn("Rótulo"),
                                "Tipo": st.column_config.SelectboxColumn("Tipo", options=list(variaveis.TIPOS), required=True),
                                "Medida": st.column_config.SelectboxColumn("Medida", options=list(variaveis.MEDIDAS), required=True),
                                "Ausentes definidos": st.column_config.TextColumn("Ausentes definidos", help="Ex.: 99;999 — permanecem na planilha bruta."),
                                "Rótulos de valores": st.column_config.TextColumn("Rótulos de valores", help="Ex.: 0=Não;1=Sim"),
                            })
    if not dic_ed.equals(dic_base):
        st.warning("Definições alteradas. Clique em 'Aplicar dicionário' para atualizá-las.")
    if st.button("Aplicar dicionário", type="primary", use_container_width=False,
                 disabled=dic_ed.equals(dic_base)):
        try:
            d, novo_schema = variaveis.aplicar_dicionario(raw, dic_ed)
            mudar_base(d, st.session_state.dataset_nome, novo_schema)
        except (ValueError, TypeError) as exc:
            st.error(str(exc))
    with st.expander("Resumo dos tipos, categorias e ausentes", expanded=True):
        tab = variaveis.estatisticas_variaveis(raw, schema)
        st.dataframe(tab[["Nome", "Rótulo", "Tipo", "Medida", "Válidos", "Ausentes", "Distintos"]],
                     hide_index=True, use_container_width=True)
    st.info("As variáveis nominais e ordinais podem ser numéricas (ex.: grupo codificado como 0/1). "
            "O nível de medida é descritivo: a seleção do teste ainda exige avaliação metodológica.")

with aba_analises:
    st.subheader("Procedimentos estatísticos")
    numericas = variaveis_numericas(analise)
    metodo = st.selectbox("Escolha o procedimento", ["Descritiva", "Shapiro-Wilk", "Correlação (Pearson / Spearman)",
                "t independente (Welch)", "t pareado", "Mann–Whitney U", "Wilcoxon pareado",
                "ANOVA de uma via", "Qui-quadrado / Fisher"])
    parametros = {}
    valido = bool(numericas) or metodo == "Qui-quadrado / Fisher"
    try:
        if metodo == "Descritiva":
            parametros["Variáveis"] = st.multiselect("Variáveis numéricas", numericas, default=numericas[:4])
            valido = bool(parametros["Variáveis"])
        elif metodo == "Shapiro-Wilk":
            parametros["Variável"] = st.selectbox("Variável numérica", numericas)
        elif metodo == "Correlação (Pearson / Spearman)":
            a,b = st.columns(2)
            parametros["X"] = a.selectbox("Variável X", numericas)
            parametros["Y"] = b.selectbox("Variável Y", numericas, index=min(1,len(numericas)-1))
            parametros["Método"] = st.radio("Coeficiente", ["Spearman", "Pearson"], horizontal=True)
            valido = len(numericas) >= 2 and parametros["X"] != parametros["Y"]
        elif metodo in ["t independente (Welch)", "Mann–Whitney U"]:
            a,b = st.columns(2)
            parametros["Variável"] = a.selectbox("Variável numérica", numericas)
            grupo_index = list(analise.columns).index("grupo") if "grupo" in analise else 0
            parametros["Grupo"] = b.selectbox("Variável de agrupamento", list(analise.columns), index=grupo_index)
            levels = list(analise[parametros["Grupo"]].dropna().unique())
            if len(levels) >= 2:
                g1,g2 = st.columns(2)
                parametros["Grupo 1"] = g1.selectbox("Grupo 1", levels, format_func=str)
                parametros["Grupo 2"] = g2.selectbox("Grupo 2", levels, index=1, format_func=str)
                valido = parametros["Grupo 1"] != parametros["Grupo 2"]
            else:
                valido = False
                st.warning("Selecione um fator com pelo menos duas categorias válidas.")
        elif metodo in ["t pareado", "Wilcoxon pareado"]:
            a,b = st.columns(2)
            parametros["Medida 1"] = a.selectbox("Primeira medida", numericas)
            parametros["Medida 2"] = b.selectbox("Segunda medida", numericas, index=min(1,len(numericas)-1))
            valido = len(numericas) >= 2 and parametros["Medida 1"] != parametros["Medida 2"]
        elif metodo == "ANOVA de uma via":
            a,b = st.columns(2)
            parametros["Variável"] = a.selectbox("Variável dependente (numérica)", numericas)
            grupo_index = list(analise.columns).index("grupo") if "grupo" in analise else 0
            parametros["Grupo"] = b.selectbox("Fator categórico", list(analise.columns), index=grupo_index)
            valido = len(analise[parametros["Grupo"]].dropna().unique()) >= 2
        else:
            a,b = st.columns(2)
            parametros["Categoria 1"] = a.selectbox("Variável categórica 1", list(analise.columns))
            parametros["Categoria 2"] = b.selectbox("Variável categórica 2", list(analise.columns),
                                                  index=min(1,len(analise.columns)-1))
            valido = len(analise.columns) >= 2 and parametros["Categoria 1"] != parametros["Categoria 2"]
    except (ValueError, IndexError):
        valido = False
        st.warning("Faltam colunas adequadas; confira a guia Variáveis.")

    if st.button("Executar análise", type="primary", disabled=not valido):
        try:
            if metodo == "Descritiva":
                table = engine.descritiva(analise, parametros["Variáveis"])
                registrado = reports.registrar_resultado(metodo, ", ".join(parametros["Variáveis"]), table,
                      len(analise), alpha, nota="N válido/ausente indicado por variável; uma linha por caso.",
                      fonte=st.session_state.dataset_nome, tipo="descritiva")
            else:
                if metodo == "Shapiro-Wilk":
                    r = engine.normalidade(analise, parametros["Variável"])
                elif metodo == "Correlação (Pearson / Spearman)":
                    r = engine.correlacao(analise, parametros["X"], parametros["Y"], parametros["Método"].lower())
                elif metodo == "t independente (Welch)":
                    r = engine.t_independente(analise, parametros["Variável"], parametros["Grupo"],
                                             parametros["Grupo 1"], parametros["Grupo 2"])
                elif metodo == "Mann–Whitney U":
                    r = engine.mann_whitney(analise, parametros["Variável"], parametros["Grupo"],
                                            parametros["Grupo 1"], parametros["Grupo 2"])
                elif metodo == "t pareado":
                    r = engine.t_pareado(analise, parametros["Medida 1"], parametros["Medida 2"])
                elif metodo == "Wilcoxon pareado":
                    r = engine.wilcoxon_pareado(analise, parametros["Medida 1"], parametros["Medida 2"])
                elif metodo == "ANOVA de uma via":
                    r = engine.anova(analise, parametros["Variável"], parametros["Grupo"])
                else:
                    r = engine.qui_quadrado(analise, parametros["Categoria 1"], parametros["Categoria 2"])
                registrado = reports.registrar_engine(r, parametros, alpha, st.session_state.dataset_nome)
            st.session_state.historico.append(registrado)
            st.success("Análise executada e adicionada ao relatório.")
        except (ValueError, TypeError, ZeroDivisionError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Falha na análise: {type(exc).__name__}: {exc}")
    if st.session_state.historico:
        st.divider()
        st.markdown("#### Último resultado")
        exibir_resultado(st.session_state.historico[-1], st.session_state.historico[-1].get("alpha", alpha))
    else:
        st.caption("O relatório será gerado com os resultados dos testes que você executar.")

with aba_graficos:
    st.subheader("Gráficos")
    num = variaveis_numericas(analise)
    if not num:
        st.warning("Importe ou defina pelo menos uma variável numérica.")
    else:
        grafico = st.radio("Tipo", ["Histograma", "Dispersão", "Boxplot por grupo"], horizontal=True)
        fig, ax = plt.subplots(figsize=(8.0, 4.8))
        try:
            if grafico == "Histograma":
                x = st.selectbox("Variável", num, key="hist_x")
                values = pd.to_numeric(analise[x], errors="coerce").dropna()
                ax.hist(values, bins="auto", edgecolor="white")
                ax.set(xlabel=x, ylabel="Frequência")
            elif grafico == "Dispersão":
                a,b = st.columns(2)
                x = a.selectbox("Variável X", num, key="sc_x")
                y = b.selectbox("Variável Y", num, index=min(1,len(num)-1), key="sc_y")
                ax.scatter(pd.to_numeric(analise[x], errors="coerce"),
                           pd.to_numeric(analise[y], errors="coerce"), alpha=.75)
                ax.set(xlabel=x, ylabel=y)
            else:
                a,b = st.columns(2)
                x = a.selectbox("Variável numérica", num, key="box_v")
                g = b.selectbox("Variável de agrupamento", list(analise.columns), key="box_g")
                valores = pd.DataFrame({"v":pd.to_numeric(analise[x], errors="coerce"), "g":analise[g]}).dropna()
                cats = list(pd.unique(valores.g))
                if len(cats) > 25:
                    raise ValueError("Há muitas categorias (mais de 25). Escolha outra variável de agrupamento.")
                ax.boxplot([valores.loc[valores.g.eq(cat), "v"].to_numpy(dtype=float) for cat in cats],
                           tick_labels=[str(cat) for cat in cats])
                ax.set(xlabel=g, ylabel=x)
            ax.set_title(grafico)
            ax.grid(alpha=.15)
            fig.tight_layout()
            st.pyplot(fig)
            buffer = io.BytesIO()
            fig.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
            st.download_button("Baixar PNG em 300 dpi", data=buffer.getvalue(), file_name="grafico_estatistica_livre.png",
                               mime="image/png")
        except (ValueError, TypeError) as exc:
            st.error(f"Não foi possível construir o gráfico: {exc}")
        finally:
            plt.close(fig)

with aba_relat:
    st.subheader("Relatórios estatísticos")
    st.caption("Histórico desta versão da base, com variáveis utilizadas, N, estatística, p, efeito e observações.")
    hist = st.session_state.historico
    if not hist:
        st.info("Execute um procedimento na guia 'Análises' para começar seu relatório.")
    else:
        tabela = reports.tabela_resumo(hist)
        st.dataframe(tabela, hide_index=True, use_container_width=True)
        with st.expander("Visualizar resultados completos", expanded=False):
            for i, r in enumerate(hist, 1):
                st.markdown(f"##### {i}. {r['teste']}")
                st.caption(r.get("variaveis", ""))
                exibir_resultado(r, r.get("alpha", alpha))
        st.divider()
        nome_rel = st.text_input("Título do relatório", value="Análises estatísticas — Estatística Livre")
        html = reports.gerar_html(hist, nome_rel, st.session_state.dataset_nome, schema)
        excel = reports.gerar_excel(hist, variaveis.estatisticas_variaveis(raw, schema))
        col1, col2, col3 = st.columns(3)
        col1.download_button("Relatório HTML / imprimir PDF", html, file_name="relatorio_estatistico.html",
                             mime="text/html", use_container_width=True)
        col2.download_button("Relatório Excel (.xlsx)", excel, file_name="relatorio_estatistico.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        col3.download_button("Resumo CSV", to_csv_bytes(tabela), file_name="resumo_resultados.csv",
                             mime="text/csv", use_container_width=True)
        st.caption("Para PDF: abra o relatório HTML no navegador e use Ctrl+P → Salvar como PDF.")
        if st.button("Limpar histórico de análises"):
            st.session_state.historico = []
            st.rerun()
    st.divider()
    st.markdown("#### Salvar dados e definições do projeto")
    try:
        projeto_bytes = project_io.exportar_projeto(raw, schema, st.session_state.dataset_nome)
        st.download_button("Salvar projeto (.elproj)", projeto_bytes, "meu_projeto.elproj",
                           "application/octet-stream", use_container_width=False)
    except ValueError as exc:
        st.warning(str(exc))
    st.caption("O projeto guarda os dados brutos e o dicionário de variáveis. "
               "O histórico de análises é exportado separadamente, não é restaurado pelo arquivo .elproj.")

st.divider()
st.caption("Ferramenta educacional • Uma linha por unidade amostral independente • "
           "Teste suposições de independência, distribuição, homocedasticidade e multiplicidade • "
           "Não transforme tentativas repetidas em participantes independentes.")
