"""Etapa 4 — gráficos (matplotlib orientado a objeto, sem estado global)."""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st
from matplotlib.figure import Figure

import componentes
from data_utils import variaveis_numericas

COR = "#1C7C92"


def _estilo(ax, titulo: str, x: str, y: str):
    ax.set_title(titulo, fontsize=12, fontweight="bold", loc="left")
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.grid(alpha=.18)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


def render(analise):
    num = variaveis_numericas(analise)
    if not num:
        componentes.vazio("Defina pelo menos uma variável numérica na etapa Variáveis para criar gráficos.")
        return
    grafico = st.radio("Tipo de gráfico", ["Histograma", "Dispersão", "Boxplot por grupo"], horizontal=True)
    fig = Figure(figsize=(8.0, 4.8))
    ax = fig.subplots()
    try:
        if grafico == "Histograma":
            x = st.selectbox("Variável", num, key="hist_x")
            valores = pd.to_numeric(analise[x], errors="coerce").dropna()
            ax.hist(valores, bins="auto", color=COR, edgecolor="white")
            _estilo(ax, f"Distribuição de {x}", x, "Frequência")
        elif grafico == "Dispersão":
            a, b = st.columns(2)
            x = a.selectbox("Variável X", num, key="sc_x")
            y = b.selectbox("Variável Y", num, index=min(1, len(num) - 1), key="sc_y")
            ax.scatter(pd.to_numeric(analise[x], errors="coerce"), pd.to_numeric(analise[y], errors="coerce"),
                       alpha=.75, color=COR, edgecolor="white", linewidth=.5)
            _estilo(ax, f"{y} × {x}", x, y)
        else:
            a, b = st.columns(2)
            x = a.selectbox("Variável numérica", num, key="box_v")
            g = b.selectbox("Variável de agrupamento", list(analise.columns), key="box_g")
            valores = pd.DataFrame({"v": pd.to_numeric(analise[x], errors="coerce"), "g": analise[g]}).dropna()
            cats = list(pd.unique(valores.g))
            if len(cats) > 25:
                raise ValueError("Há muitas categorias (mais de 25). Escolha outra variável de agrupamento.")
            caixas = ax.boxplot([valores.loc[valores.g.eq(c), "v"].to_numpy(dtype=float) for c in cats],
                                tick_labels=[str(c) for c in cats], patch_artist=True)
            for caixa in caixas["boxes"]:
                caixa.set(facecolor="#d8ebf0", edgecolor=COR)
            _estilo(ax, f"{x} por {g}", g, x)
        fig.tight_layout()
        st.pyplot(fig)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        st.download_button("Baixar PNG (300 dpi)", data=buf.getvalue(),
                           file_name="grafico_estatistica_livre.png", mime="image/png")
    except (ValueError, TypeError) as exc:
        st.error(f"Não foi possível construir o gráfico: {exc}")
