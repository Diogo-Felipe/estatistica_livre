"""Etapa 2 — dicionário de variáveis."""
from __future__ import annotations

import streamlit as st

import estado
import schema as variaveis


def render():
    raw, schema = st.session_state.df, st.session_state.schema
    st.markdown("##### Dicionário de variáveis")
    st.caption("Edite nomes, rótulos, tipo, nível de medida e códigos ausentes (ex.: 99;999). "
               "Rótulos de valores usam o formato 0=Não;1=Sim.")
    dic_base = variaveis.tabela_dicionario(raw, schema)
    dic_ed = st.data_editor(
        dic_base, num_rows="fixed", hide_index=True, key=f"dic_{st.session_state.revisao}", width="stretch",
        column_config={
            "Nome": st.column_config.TextColumn("Nome", required=True),
            "Rótulo": st.column_config.TextColumn("Rótulo"),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=list(variaveis.TIPOS), required=True),
            "Medida": st.column_config.SelectboxColumn("Medida", options=list(variaveis.MEDIDAS), required=True),
            "Ausentes definidos": st.column_config.TextColumn(
                "Ausentes definidos", help="Ex.: 99;999 — permanecem na planilha bruta."),
            "Rótulos de valores": st.column_config.TextColumn("Rótulos de valores", help="Ex.: 0=Não;1=Sim"),
        })
    mudou = not dic_ed.equals(dic_base)
    if mudou:
        st.warning("Definições alteradas. Clique em **Aplicar dicionário** para atualizá-las.")
    if st.button("Aplicar dicionário", type="primary", disabled=not mudou):
        try:
            d, novo_schema = variaveis.aplicar_dicionario(raw, dic_ed)
            estado.mudar_base(d, st.session_state.dataset_nome, novo_schema)
        except (ValueError, TypeError) as exc:
            st.error(str(exc))
    with st.expander("Resumo de tipos, valores válidos e ausentes", expanded=True):
        tab = variaveis.estatisticas_variaveis(raw, schema)
        st.dataframe(tab[["Nome", "Rótulo", "Tipo", "Medida", "Válidos", "Ausentes", "Distintos"]],
                     hide_index=True, width="stretch")
    st.info("Variáveis nominais e ordinais podem ser numéricas (ex.: grupo codificado como 0/1). "
            "O nível de medida é descritivo: a escolha do teste ainda exige avaliação metodológica. "
            "Alterar o dicionário apaga as análises já registradas.")
