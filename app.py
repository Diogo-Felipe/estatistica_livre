"""Estatística Livre 0.2 — fluxo guiado: Dados → Variáveis → Análises → Gráficos → Relatório.

Executar: python -m streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

import barra_lateral
import componentes
import estado
import estilo
import schema as variaveis
from paginas import analises, dados, graficos, relatorio
from paginas import variaveis as pagina_variaveis

st.set_page_config(page_title="Estatística Livre", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
estilo.aplicar()
estado.iniciar()

# ---------- espaços reservados (preenchidos depois das abas, para refletir análises recém-executadas) ----------
topo = st.container()
with st.sidebar:
    alpha = barra_lateral.configuracoes()
    lateral = st.container()

raw = st.session_state.df
schema = st.session_state.schema
analise = variaveis.preparar_analise(raw, schema)
n_ausentes = int(analise.isna().sum().sum())

t1, t2, t3, t4, t5 = st.tabs(["1 · Dados", "2 · Variáveis", "3 · Análises", "4 · Gráficos", "5 · Relatório"])
with t1:
    dados.render()
with t2:
    pagina_variaveis.render()
with t3:
    analises.render(analise, alpha)
with t4:
    graficos.render(analise)
with t5:
    relatorio.render(alpha)

with topo:
    componentes.cabecalho(st.session_state.dataset_nome, len(raw), len(raw.columns), n_ausentes,
                          len(st.session_state.historico))
with lateral:
    barra_lateral.projeto_e_historico(raw, schema, n_ausentes)

st.caption("Ferramenta educacional · Verifique independência, distribuição, homocedasticidade e multiplicidade antes de concluir.")
