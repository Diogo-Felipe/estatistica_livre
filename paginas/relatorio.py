"""Etapa 5 — relatório e projeto."""
from __future__ import annotations

import streamlit as st

import componentes
import reports
import schema as variaveis
from data_utils import to_csv_bytes


def render(alpha: float):
    raw, schema = st.session_state.df, st.session_state.schema
    hist = st.session_state.historico
    st.caption("Histórico desta versão da base: variáveis, N, estatística, p, efeito, interpretação e observações.")
    if not hist:
        componentes.vazio("Nenhuma análise registrada. Execute um procedimento na etapa Análises.")
    else:
        tabela = reports.tabela_resumo(hist)
        st.dataframe(tabela, hide_index=True, width="stretch")
        with st.expander("Ver resultados completos", expanded=False):
            for i, r in enumerate(hist, 1):
                st.markdown(f"##### {i}. {r['teste']}")
                st.caption(r.get("variaveis", ""))
                componentes.exibir_resultado(r, r.get("alpha", alpha), titulo=False)
        st.divider()
        titulo = st.text_input("Título do relatório", value="Análises estatísticas — Estatística Livre")
        html = reports.gerar_html(hist, titulo, st.session_state.dataset_nome, schema)
        excel = reports.gerar_excel(hist, variaveis.estatisticas_variaveis(raw, schema))
        c1, c2, c3 = st.columns(3)
        c1.download_button("Relatório HTML", html, file_name="relatorio_estatistico.html",
                           mime="text/html", type="primary", width="stretch")
        c2.download_button("Relatório Excel (.xlsx)", excel, file_name="relatorio_estatistico.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
        c3.download_button("Resumo CSV", to_csv_bytes(tabela), file_name="resumo_resultados.csv",
                           mime="text/csv", width="stretch")
        st.caption("Para PDF: abra o relatório HTML no navegador e use Ctrl+P → Salvar como PDF.")
        if st.button("Limpar histórico de análises"):
            st.session_state.historico = []
            st.rerun()
    st.caption("Para guardar dados e dicionário, use **Salvar projeto** na barra lateral.")
