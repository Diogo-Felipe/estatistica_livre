"""Etapa 1 — importar e editar os dados."""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

import estado
import schema as variaveis
from data_utils import ColunasSemNomeError, ler_arquivo, prever_arquivo, to_csv_bytes


ACOES = ("Escolher…", "Dar um nome", "Remover coluna")


def marcar_todas_para_remover(estado_sessao, chaves_acao: list[str]) -> None:
    """Define a ação "Remover coluna" para todas as colunas sem nome (usado como callback do botão)."""
    for k in chaves_acao:
        estado_sessao[k] = ACOES[2]


def _decidir_sem_nome(colunas: list[dict], chave: str) -> dict:
    """Pergunta, para cada coluna sem nome, se deve receber um nome ou ser removida.

    Devolve {chave_da_coluna: nome | None}; colunas ainda sem decisão ficam de fora.
    """
    st.warning(f"{len(colunas)} coluna(s) têm dados mas não têm nome no cabeçalho. "
               "Dê um nome a cada uma ou remova-a da base (os dados dela não serão importados).")
    chaves_acao = [f"acao_{chave}_{c['chave']}" for c in colunas]
    if len(colunas) > 1:
        st.button("Remover todas", key=f"remover_todas_{chave}", on_click=marcar_todas_para_remover,
                  args=(st.session_state, chaves_acao), help="Marca todas as colunas sem nome para remoção. "
                  "Você ainda pode mudar a escolha de colunas individuais.")
    decisoes: dict = {}
    for c in colunas:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2.2, 1.4, 2])
            c1.markdown(f"**Coluna {c['posicao']}**")
            c1.caption("Exemplos: " + (", ".join(c["exemplos"]) or "—"))
            acao = c2.selectbox("O que fazer?", ACOES, key=f"acao_{chave}_{c['chave']}")
            if acao == "Dar um nome":
                nome = c3.text_input("Nome da variável", key=f"nome_{chave}_{c['chave']}",
                                     placeholder="Ex.: idade_meses").strip()
                if nome:
                    decisoes[c["chave"]] = nome
            elif acao == "Remover coluna":
                decisoes[c["chave"]] = None
    return decisoes


def _importacao():
    st.markdown("##### 1. Traga seus dados")
    col_arq, col_cfg = st.columns([1.4, 1])
    with col_arq:
        arquivo = st.file_uploader("Arquivo .csv ou .xlsx", type=["csv", "xlsx"], key="entrada_dados")
    with col_cfg:
        sep = st.selectbox("Separador do CSV", ["Automático", ";", ",", "Tabulação"], index=0)
        decimal = st.selectbox("Decimal do CSV", ["Virgula", "Ponto"], index=0,
                               format_func=lambda s: "Vírgula (1,5)" if s == "Virgula" else "Ponto (1.5)")
    aba = 0
    if arquivo is not None and arquivo.name.lower().endswith(".xlsx"):
        try:
            with pd.ExcelFile(io.BytesIO(arquivo.getvalue()), engine="openpyxl") as xls:
                aba = st.selectbox("Aba do Excel", xls.sheet_names)
        except Exception as e:
            st.error(f"Não foi possível listar as abas: {e}")
    mapa_sep = {"Automático": "automático", "Tabulação": "\t"}
    opcoes = dict(sep=mapa_sep.get(sep, sep), decimal="," if decimal == "Virgula" else ".", aba=aba)
    linha_cab, previa, decisoes = 1, None, {}
    if arquivo is not None:
        st.markdown("**Linha do cabeçalho**")
        st.caption("Se o arquivo tiver títulos ou notas antes da tabela, informe em qual linha estão os "
                   "nomes das variáveis (1 = primeira linha). As linhas acima dela são ignoradas.")
        try:
            with st.expander("Ver as primeiras linhas do arquivo", expanded=True):
                st.dataframe(prever_arquivo(arquivo, aba=aba), width="stretch")
        except Exception as e:
            st.error(f"Não foi possível pré-visualizar o arquivo: {e}")
        linha_cab = int(st.number_input("Linha do cabeçalho", min_value=1, max_value=1000, value=1, step=1,
                                        key=f"linha_cab_{arquivo.name}"))
        chave = f"{arquivo.name}_{aba}_{linha_cab}"
        decisoes, previa = {}, None
        for _ in range(2):
            try:
                previa = ler_arquivo(arquivo, linha_cabecalho=linha_cab, colunas_sem_nome=decisoes, **opcoes)
                break
            except ColunasSemNomeError as e:
                decisoes = _decidir_sem_nome(e.colunas, chave)
                if len(decisoes) < len(e.colunas):
                    st.info("Defina o que fazer com todas as colunas sem nome para continuar.")
                    break
            except Exception as e:
                st.warning(f"Com a linha {linha_cab} como cabeçalho: {e}")
                break
        if previa is not None:
            st.success(f"Com a linha {linha_cab} como cabeçalho: {len(previa)} casos e {len(previa.columns)} variáveis.")
            st.caption("Variáveis encontradas: " + ", ".join(map(str, previa.columns)))
            if decisoes:
                nomeadas = sum(v is not None for v in decisoes.values())
                st.caption(f"Colunas sem nome: {nomeadas} nomeada(s), {len(decisoes) - nomeadas} removida(s).")
    b1, b2, b3 = st.columns([1.2, 1, 1])
    if b1.button("Importar arquivo", type="primary", disabled=arquivo is None or previa is None, width="stretch"):
        try:
            df_novo = ler_arquivo(arquivo, linha_cabecalho=linha_cab, colunas_sem_nome=decisoes, **opcoes)
            estado.mudar_base(df_novo, f"{arquivo.name}" + (f" · {aba}" if isinstance(aba, str) else ""))
        except Exception as e:
            st.error(f"Erro na importação: {e}")
    if b2.button("Usar exemplo", width="stretch", help="18 participantes fictícios"):
        estado.mudar_base(estado.carregar_exemplo(), estado.EXEMPLO[1])
    if b3.button("Base de validação", width="stretch", help="60 registros fictícios com resultados conhecidos"):
        estado.mudar_base(estado.carregar_validacao(), "Validação fictícia · 60 registros")


def _editor(raw: pd.DataFrame, schema: dict):
    st.markdown("##### 2. Confira e edite")
    st.caption("Linhas = casos; colunas = variáveis. Edite as células e clique em **Aplicar mudanças** para gravar.")
    if st.checkbox("Mostrar rótulos de valores no lugar dos códigos (somente leitura)", value=False, key="mostrar_rotulos"):
        visual = raw.copy()
        for col in visual.columns:
            m = variaveis.labels_valores(schema.get(str(col), {}).get("valores", ""))
            if m:
                visual[col] = visual[col].astype("string").map(
                    lambda v: variaveis.rotulo_valor(v, m) if pd.notna(v) else v)
        st.dataframe(visual, width="stretch")
        st.caption("A edição continua sendo feita nos códigos originais abaixo.")
    editado = st.data_editor(raw, key=f"dados_{st.session_state.revisao}", num_rows="dynamic",
                             width="stretch", hide_index=False)
    diferencas = not editado.equals(raw)
    if diferencas:
        st.warning("Há mudanças ainda não aplicadas. Elas só entram nas análises depois de **Aplicar mudanças**.")
    c1, c2, c3 = st.columns([1.3, 1.3, 1.4])
    if c1.button("Aplicar mudanças", type="primary", disabled=not diferencas, width="stretch"):
        if editado.columns.duplicated().any():
            st.error("Existem colunas com nomes duplicados.")
        else:
            novo_schema = {c: schema.get(c, variaveis.criar_dicionario(editado)[c]) for c in editado.columns}
            estado.mudar_base(editado, st.session_state.dataset_nome, novo_schema)
    c2.download_button("Baixar dados (.csv)", data=to_csv_bytes(raw), file_name="dados_estatistica_livre.csv",
                       mime="text/csv", width="stretch")
    with c3:
        st.caption("Códigos de ausentes definidos no dicionário não alteram os dados brutos.")


def _colunas(raw: pd.DataFrame, schema: dict):
    with st.expander("Adicionar ou excluir variáveis"):
        novo_nome = st.text_input("Nome da nova variável", placeholder="Ex.: copm_satisfacao", key="nome_col")
        c1, c2 = st.columns(2)
        if c1.button("Adicionar coluna", width="stretch"):
            nome = novo_nome.strip()
            if not nome or nome in raw.columns:
                st.error("Informe um nome novo e não vazio.")
            else:
                d = raw.copy()
                d[nome] = pd.Series([float("nan")] * len(d))
                estado.mudar_base(d, st.session_state.dataset_nome)
        excluir = c2.multiselect("Excluir variáveis", list(raw.columns), key="excluir_colunas")
        if st.button("Excluir variáveis selecionadas", disabled=not excluir):
            if len(excluir) == len(raw.columns):
                st.error("O projeto precisa ter ao menos uma variável.")
            else:
                d = raw.drop(columns=excluir)
                estado.mudar_base(d, st.session_state.dataset_nome, {c: schema[c] for c in d.columns})
    st.caption("Para renomear variáveis ou definir códigos de ausentes, use a etapa **Variáveis**.")


def render():
    raw, schema = st.session_state.df, st.session_state.schema
    _importacao()
    st.divider()
    _editor(raw, schema)
    _colunas(raw, schema)
