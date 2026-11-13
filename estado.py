"""Estado da sessão Streamlit (base, dicionário, histórico)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import schema as variaveis

BASE = Path(__file__).parent
EXEMPLO = ("exemplo_ficticio.csv", "Exemplo fictício · 18 participantes")


def carregar_exemplo() -> pd.DataFrame:
    return pd.read_csv(BASE / EXEMPLO[0])


def carregar_validacao() -> pd.DataFrame:
    return pd.read_csv(BASE / "validacao_estatistica_ficticia.csv", sep=";", decimal=",")


def iniciar():
    if "df" not in st.session_state:
        df = carregar_exemplo()
        st.session_state.df = df
        st.session_state.schema = variaveis.criar_dicionario(df)
        st.session_state.dataset_nome = EXEMPLO[1]
    if "schema" not in st.session_state:
        st.session_state.schema = variaveis.criar_dicionario(st.session_state.df)
    st.session_state.setdefault("revisao", 0)
    st.session_state.setdefault("historico", [])


def mudar_base(df: pd.DataFrame, nome: str, dic: dict | None = None):
    """Substitui a base; apaga o histórico para que relatórios não fiquem desatualizados."""
    st.session_state.df = df.reset_index(drop=True)
    st.session_state.schema = dic if dic is not None else variaveis.criar_dicionario(st.session_state.df)
    st.session_state.dataset_nome = nome
    st.session_state.historico = []
    st.session_state.revisao += 1
    st.rerun()
