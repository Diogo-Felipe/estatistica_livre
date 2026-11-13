"""Barra lateral: projeto, configurações, análises registradas e ajuda."""
from __future__ import annotations

from html import escape

import streamlit as st

import estado
import interpretacao
import project_io


def configuracoes() -> float:
    """Controles que as análises precisam antes de executar (renderizados no topo)."""
    st.markdown("##### Configurações")
    return st.select_slider("Nível de significância (α)", options=[0.01, 0.05, 0.10], value=0.05,
                            help="Critério de decisão. Não altera o p-valor calculado.")


def projeto_e_historico(raw, schema, n_ausentes: int):
    """Projeto, análises registradas e ajuda; chamado depois das abas para refletir a execução atual."""
    st.divider()
    st.markdown("##### Projeto")
    st.caption(f"**{st.session_state.dataset_nome}**  \n{len(raw)} casos · {len(raw.columns)} variáveis · "
               f"{n_ausentes} células ausentes")
    try:
        dados = project_io.exportar_projeto(raw, schema, st.session_state.dataset_nome)
        st.download_button("💾 Salvar projeto (.elproj)", dados, "meu_projeto.elproj", "application/octet-stream",
                           width="stretch", help="Guarda dados brutos e dicionário. O histórico de análises "
                                                "não é restaurado; exporte o relatório separadamente.")
    except ValueError as exc:
        st.warning(str(exc))
    with st.expander("Restaurar projeto"):
        projeto = st.file_uploader("Arquivo .elproj", type=["elproj"], key="upload_projeto")
        if st.button("Restaurar", disabled=projeto is None, width="stretch"):
            try:
                d, dic, nome = project_io.importar_projeto(projeto.getvalue())
                estado.mudar_base(d, nome, dic)
            except ValueError as e:
                st.error(str(e))

    st.divider()
    hist = st.session_state.historico
    st.markdown(f"##### Análises registradas ({len(hist)})")
    if not hist:
        st.caption("Nenhuma ainda. Os resultados que você executar aparecem aqui e entram no relatório.")
    else:
        for i, r in enumerate(hist, 1):
            resumo = f"N = {r['n']}"
            if r.get("p") is not None:  # descritiva não tem p-valor
                resumo = f"p = {interpretacao.formatar_p(r['p'])} · {resumo}"
            st.markdown(f"**{i}. {escape(r['teste'])}**  \n<span class='small-note'>{escape(resumo)}</span>",
                        unsafe_allow_html=True)
        st.caption("Detalhes e exportação na etapa **5 · Relatório**.")
        if st.button("Limpar análises", width="stretch", key="limpar_lateral"):
            st.session_state.historico = []
            st.rerun()

    st.divider()
    with st.expander("Ajuda e boas práticas"):
        st.markdown(
            "**Fluxo:** 1 Dados → 2 Variáveis → 3 Análises → 4 Gráficos → 5 Relatório.\n\n"
            "- Uma linha = uma unidade amostral independente (exceto em testes pareados).\n"
            "- Alterar dados ou dicionário apaga as análises registradas.\n"
            "- Nada é salvo automaticamente: salve o projeto para guardar seu trabalho.\n"
            "- Uso local: evite publicar bases com dados pessoais ou clínicos identificáveis.")
