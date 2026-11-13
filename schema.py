"""Dicionário de variáveis; altera metadados sem corromper dados brutos.

Códigos de ausentes são aplicados somente na *visão para análise*,
sem modificar as células originais da tabela.
"""
from __future__ import annotations

import re
import pandas as pd

TIPOS = ("Numérica", "Texto")
MEDIDAS = ("Escala", "Ordinal", "Nominal")
COLUNAS_EDITOR = ("Nome", "Rótulo", "Tipo", "Medida", "Ausentes definidos", "Rótulos de valores")


def criar_dicionario(df: pd.DataFrame) -> dict[str, dict[str, str]]:
    return {
        str(c): {
            "rotulo": str(c),
            "tipo": "Numérica" if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c]) else "Texto",
            "medida": "Escala" if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c]) else "Nominal",
            "ausentes": "",
            "valores": "",
        }
        for c in df.columns
    }


def tabela_dicionario(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        info = schema.get(str(c), criar_dicionario(df)[str(c)])
        rows.append({
            "Nome": str(c), "Rótulo": info.get("rotulo", str(c)),
            "Tipo": info.get("tipo", "Texto"), "Medida": info.get("medida", "Nominal"),
            "Ausentes definidos": info.get("ausentes", ""),
            "Rótulos de valores": info.get("valores", ""),
        })
    return pd.DataFrame(rows, columns=list(COLUNAS_EDITOR))


def _numero(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    raw = s.astype("string").str.strip()
    # Aceita decimal com vírgula ou ponto, mas não deduz separador de milhares.
    raw = raw.str.replace(",", ".", regex=False)
    return pd.to_numeric(raw, errors="coerce")


def _validar_valores_labels(texto: str) -> None:
    if not texto.strip():
        return
    for parte in texto.split(";"):
        if parte.strip() and ("=" not in parte or not parte.split("=", 1)[0].strip() or not parte.split("=", 1)[1].strip()):
            raise ValueError("Rótulos de valores precisam ter formato '0=Não;1=Sim'.")


def aplicar_dicionario(df: pd.DataFrame, editado: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Valida renomeação, tipo, escala e metadados. Lança erro antes de aplicar parcialmente."""
    if len(editado) != len(df.columns) or set(COLUNAS_EDITOR) - set(editado.columns):
        raise ValueError("O dicionário precisa manter uma linha por variável e todas as colunas de definição.")
    nomes = editado["Nome"].fillna("").astype(str).str.strip().tolist()
    if not all(nomes) or len(set(nomes)) != len(nomes):
        raise ValueError("Os nomes das variáveis devem ser únicos e não podem estar vazios.")
    if any(len(n) > 100 or n.startswith("_") for n in nomes):
        raise ValueError("Use nomes com até 100 caracteres, sem começar com sublinhado.")
    if any("\n" in n or "\r" in n for n in nomes):
        raise ValueError("Os nomes das variáveis não podem conter quebras de linha.")

    novas = {}
    infos = {}
    for i, antigo in enumerate(df.columns):
        linha = editado.iloc[i]
        novo = nomes[i]
        tipo = str(linha["Tipo"]).strip()
        medida = str(linha["Medida"]).strip()
        if tipo not in TIPOS or medida not in MEDIDAS:
            raise ValueError(f"Tipo ou medida inválidos na variável '{novo}'.")
        ausentes = "" if pd.isna(linha["Ausentes definidos"]) else str(linha["Ausentes definidos"]).strip()
        valores = "" if pd.isna(linha["Rótulos de valores"]) else str(linha["Rótulos de valores"]).strip()
        rotulo = "" if pd.isna(linha["Rótulo"]) else str(linha["Rótulo"]).strip()
        _validar_valores_labels(valores)
        if tipo == "Numérica":
            convertido = _numero(df[antigo])
            invalidos = df[antigo].notna() & convertido.isna() & df[antigo].astype(str).str.strip().ne("")
            # Códigos de ausentes declarados podem ser texto; têm tratamento especial abaixo.
            codigos = {x.strip() for x in ausentes.split(";") if x.strip()}
            invalidos &= ~df[antigo].astype(str).str.strip().isin(codigos)
            if invalidos.any():
                raise ValueError(f"'{novo}': {int(invalidos.sum())} valor(es) não numérico(s). Corrija ou declare códigos ausentes.")
            novas[novo] = convertido
        else:
            novas[novo] = df[antigo].astype("string")
        infos[novo] = {"rotulo": rotulo or novo, "tipo": tipo, "medida": medida,
                       "ausentes": ausentes, "valores": valores}
    return pd.DataFrame(novas, index=df.index), infos


def preparar_analise(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """Transforma os códigos definidos em ausentes numa cópia da base."""
    out = df.copy(deep=True)
    for c in out.columns:
        dados = schema.get(str(c), {})
        ausentes = [x.strip() for x in dados.get("ausentes", "").split(";") if x.strip()]
        if not ausentes:
            continue
        mascara = pd.Series(False, index=out.index)
        if pd.api.types.is_numeric_dtype(out[c]):
            valores = pd.to_numeric(pd.Series([x.replace(",", ".") for x in ausentes]), errors="coerce")
            for v in valores.dropna():
                mascara |= out[c].eq(v)
        else:
            texto = out[c].astype("string").str.strip()
            mascara |= texto.isin(ausentes).fillna(False)
            # Código numérico também casa com texto numérico equivalente ("99" = "99.0" = "99,0").
            codigos_num = pd.to_numeric(pd.Series([x.replace(",", ".") for x in ausentes]), errors="coerce").dropna()
            if len(codigos_num):
                convertido = _numero(out[c])
                for v in codigos_num:
                    mascara |= convertido.eq(v).fillna(False)
        out.loc[mascara, c] = pd.NA
    return out


def estatisticas_variaveis(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    analise = preparar_analise(df, schema)
    tabela = tabela_dicionario(df, schema)
    tabela["Válidos"] = [int(analise[c].notna().sum()) for c in df.columns]
    tabela["Ausentes"] = [int(analise[c].isna().sum()) for c in df.columns]
    tabela["Distintos"] = [int(analise[c].nunique(dropna=True)) for c in df.columns]
    return tabela


def labels_valores(texto: str) -> dict[str, str]:
    pares = {}
    for parte in str(texto).split(";"):
        if "=" in parte:
            a, b = parte.split("=", 1)
            if a.strip() and b.strip():
                pares[a.strip()] = b.strip()
    return pares


def rotulo_valor(valor, mapa: dict[str,str]):
    """Apresentação amigável de códigos (0 e 0.0 usam o mesmo rótulo)."""
    chave = str(valor).strip()
    if chave in mapa:
        return mapa[chave]
    try:
        numero = float(chave)
        if numero.is_integer() and str(int(numero)) in mapa:
            return mapa[str(int(numero))]
    except (TypeError, ValueError, OverflowError):
        pass
    return valor
