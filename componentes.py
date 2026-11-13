"""Componentes visuais reutilizáveis."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

import interpretacao


def cabecalho(nome_base: str, n_casos: int, n_vars: int, n_ausentes: int, n_analises: int):
    """Barra de topo compacta: título à esquerda; projeto e contadores como chips à direita."""
    def n(valor: int, sing: str, plur: str) -> str:
        return f"<span class='el-chip'><b>{valor}</b> {sing if valor == 1 else plur}</span>"

    chips = (f"<span class='el-chip el-chip-nome' title='{escape(nome_base)}'>📁 {escape(nome_base)}</span>"
             + n(n_casos, "caso", "casos") + n(n_vars, "variável", "variáveis")
             + n(n_ausentes, "ausente", "ausentes") + n(n_analises, "análise", "análises"))
    st.markdown(
        f"<div class='el-header'><div class='el-title'><span class='el-logo'>📊</span>"
        f"<h1>Estatística Livre</h1><span class='el-ver'>v0.2</span></div>"
        f"<div class='el-chips'>{chips}</div></div>", unsafe_allow_html=True)


def vazio(mensagem: str):
    st.markdown(f"<div class='el-vazio'>{escape(mensagem)}</div>", unsafe_allow_html=True)


def guia(item: dict[str, str]):
    st.markdown(
        f"<div class='el-guia'><b>O que faz:</b> {escape(item['resumo'])}<br>"
        f"<b>Quando usar:</b> {escape(item['quando'])}<br>"
        f"<b>Pressupostos:</b> {escape(item['pressupostos'])}</div>", unsafe_allow_html=True)


def exibir_resultado(item: dict, alpha: float, titulo: bool = True):
    """Cartão de resultado: indicadores, interpretação em linguagem simples, tabela e observações."""
    if titulo:
        st.markdown(
            f"<div class='el-card'><h4>{escape(item['teste'])}</h4>"
            f"<div class='el-sub'>{escape(item.get('variaveis', ''))} · {escape(item.get('quando', ''))}</div></div>",
            unsafe_allow_html=True)
    p = item.get("p")
    if p is not None:
        a, b, c, d = st.columns(4)
        a.metric("Estatística", (item.get("estatistica") or "—").replace(".", ","))  # vírgula decimal
        b.metric("p-valor", interpretacao.formatar_p(p))
        c.metric("N utilizado", item.get("n", 0))
        d.metric("α definido", str(item.get("alpha", alpha)).replace(".", ","))
        alpha_item = item.get("alpha", alpha)
        padrao_texto, padrao_tom = interpretacao.conclusao(item.get("tipo", ""), p, alpha_item)
        texto = item.get("conclusao") or padrao_texto
        tom = item.get("tom") or padrao_tom
        if texto:
            st.markdown(f"<div class='el-concl {tom}'>{escape(texto)}</div>", unsafe_allow_html=True)
    if item.get("magnitude"):
        st.markdown(f"**Tamanho do efeito:** {item['magnitude']}")
        st.caption("Rótulos de magnitude são referências convencionais (Cohen); interprete conforme o contexto da pesquisa.")
    elif item.get("efeito"):
        st.markdown(f"**Tamanho do efeito:** {item['efeito']}")
    tabela = item.get("tabela")
    if isinstance(tabela, pd.DataFrame) and not tabela.empty:
        st.dataframe(tabela, hide_index=True, width="stretch")
    if item.get("nota"):
        with st.expander("Pressupostos e observações", expanded=False):
            st.write(item["nota"])
