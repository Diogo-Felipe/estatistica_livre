"""Etapa 3 — escolher o objetivo, o procedimento e executar."""
from __future__ import annotations

import streamlit as st

import componentes
import procedimentos
from data_utils import variaveis_numericas


def _parametros(metodo: str, analise, numericas: list[str]) -> tuple[dict, bool]:
    """Desenha os campos do procedimento. Devolve (parâmetros, pode_executar)."""
    p: dict = {}
    k = metodo  # chaves distintas por procedimento
    colunas = list(analise.columns)
    if metodo == "Descritiva":
        p["Variáveis"] = st.multiselect("Variáveis numéricas", numericas, default=numericas[:4], key=f"{k}_vars")
        return p, bool(p["Variáveis"])
    if metodo == "Shapiro-Wilk":
        p["Variável"] = st.selectbox("Variável numérica", numericas, key=f"{k}_v")
        return p, True
    if metodo == "Correlação (Pearson / Spearman)":
        a, b = st.columns(2)
        p["X"] = a.selectbox("Variável X", numericas, key=f"{k}_x")
        p["Y"] = b.selectbox("Variável Y", numericas, index=min(1, len(numericas) - 1), key=f"{k}_y")
        p["Método"] = st.radio("Coeficiente", ["Spearman", "Pearson"], horizontal=True, key=f"{k}_m")
        return p, len(numericas) >= 2 and p["X"] != p["Y"]
    if metodo in ("t independente (Welch)", "Mann–Whitney U"):
        a, b = st.columns(2)
        p["Variável"] = a.selectbox("Variável numérica", numericas, key=f"{k}_v")
        gi = colunas.index("grupo") if "grupo" in colunas else 0
        p["Grupo"] = b.selectbox("Variável de agrupamento", colunas, index=gi, key=f"{k}_g")
        niveis = list(analise[p["Grupo"]].dropna().unique())
        if len(niveis) < 2:
            st.warning("Escolha um fator com pelo menos duas categorias válidas.")
            return p, False
        g1, g2 = st.columns(2)
        p["Grupo 1"] = g1.selectbox("Grupo 1", niveis, format_func=str, key=f"{k}_g1")
        p["Grupo 2"] = g2.selectbox("Grupo 2", niveis, index=1, format_func=str, key=f"{k}_g2")
        return p, p["Grupo 1"] != p["Grupo 2"]
    if metodo in ("t pareado", "Wilcoxon pareado"):
        a, b = st.columns(2)
        p["Medida 1"] = a.selectbox("Primeira medida", numericas, key=f"{k}_m1")
        p["Medida 2"] = b.selectbox("Segunda medida", numericas, index=min(1, len(numericas) - 1), key=f"{k}_m2")
        return p, len(numericas) >= 2 and p["Medida 1"] != p["Medida 2"]
    if metodo == "Friedman":
        p["Medidas"] = st.multiselect("Medidas (3 ou mais, nos mesmos participantes)", numericas,
                                      default=numericas[:3], key=f"{k}_medidas")
        if len(p["Medidas"]) < 3:
            st.warning("Selecione pelo menos 3 medidas. Para 2 medidas, use Wilcoxon pareado.")
        return p, len(p["Medidas"]) >= 3
    if metodo == "ANOVA de uma via":
        a, b = st.columns(2)
        p["Variável"] = a.selectbox("Variável dependente (numérica)", numericas, key=f"{k}_v")
        gi = colunas.index("grupo") if "grupo" in colunas else 0
        p["Grupo"] = b.selectbox("Fator categórico", colunas, index=gi, key=f"{k}_g")
        return p, len(analise[p["Grupo"]].dropna().unique()) >= 2
    a, b = st.columns(2)
    p["Categoria 1"] = a.selectbox("Variável categórica 1", colunas, key=f"{k}_c1")
    p["Categoria 2"] = b.selectbox("Variável categórica 2", colunas, index=min(1, len(colunas) - 1), key=f"{k}_c2")
    return p, len(colunas) >= 2 and p["Categoria 1"] != p["Categoria 2"]


def render(analise, alpha: float):
    numericas = variaveis_numericas(analise)
    qui = "Qui-quadrado / Fisher"

    st.markdown("##### 1. O que você quer fazer?")
    objetivo = st.radio("Objetivo", list(procedimentos.OBJETIVOS), label_visibility="collapsed",
                        horizontal=False, key="objetivo")
    opcoes = procedimentos.OBJETIVOS[objetivo]
    if len(opcoes) > 1:
        st.markdown("##### 2. Escolha o procedimento")
        metodo = st.radio("Procedimento", opcoes, horizontal=True, label_visibility="collapsed",
                          key=f"proc_{objetivo}")
    else:
        metodo = opcoes[0]
    componentes.guia(procedimentos.GUIA[metodo])

    if not numericas and metodo != qui:
        st.warning("Este procedimento precisa de variáveis numéricas. Defina o tipo na etapa **Variáveis**.")
        return

    st.markdown("##### 3. Selecione as variáveis")
    parametros, valido = _parametros(metodo, analise, numericas)

    if st.button("Executar análise", type="primary", disabled=not valido):
        try:
            registro = procedimentos.executar(metodo, analise, parametros, alpha, st.session_state.dataset_nome)
            st.session_state.historico.append(registro)
            st.success("Análise concluída e adicionada ao relatório.")
        except (ValueError, TypeError, ZeroDivisionError) as exc:
            st.error(str(exc))
        except Exception as exc:  # erro inesperado: mostrar sem derrubar o app
            st.error(f"Falha na análise: {type(exc).__name__}: {exc}")

    st.divider()
    if st.session_state.historico:
        st.markdown("#### Último resultado")
        ultimo = st.session_state.historico[-1]
        componentes.exibir_resultado(ultimo, ultimo.get("alpha", alpha))
    else:
        componentes.vazio("Nenhuma análise ainda. Escolha um objetivo, selecione as variáveis e clique em "
                          "“Executar análise”.")
