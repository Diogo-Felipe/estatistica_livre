"""Importação e exportação de tabelas, sem dependência de interface."""
from __future__ import annotations
import io
import pandas as pd


def ler_arquivo(uploaded, sep: str = "automático", decimal: str = ",", aba=0) -> pd.DataFrame:
    name = uploaded.name.lower()
    raw = uploaded.getvalue()
    if name.endswith(".csv"):
        kwargs = {"decimal": decimal, "encoding": "utf-8-sig"}
        if sep == "automático":
            kwargs.update({"sep": None, "engine": "python"})
        else:
            kwargs["sep"] = sep
        try:
            df = pd.read_csv(io.BytesIO(raw), **kwargs)
        except UnicodeDecodeError:
            kwargs["encoding"] = "cp1252"
            df = pd.read_csv(io.BytesIO(raw), **kwargs)
    elif name.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(raw), sheet_name=aba, engine="openpyxl")
    else:
        raise ValueError("Use arquivos .csv ou .xlsx.")
    if df.empty:
        raise ValueError("Arquivo não contém observações.")
    df.columns = [str(c).strip() for c in df.columns]
    if len(set(df.columns)) != len(df.columns):
        raise ValueError("Há nomes de colunas repetidos. Renomeie as variáveis no arquivo.")
    return df


def variaveis_numericas(df: pd.DataFrame) -> list[str]:
    return [col for col in df if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col])]


def dicionario(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{"Variável": col,
                          "Tipo": "Numérica" if col in variaveis_numericas(df) else "Categórica/texto",
                          "Válidos": int(df[col].notna().sum()),
                          "Ausentes": int(df[col].isna().sum()),
                          "Categorias/valores distintos": int(df[col].nunique(dropna=True))}
                         for col in df.columns])


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    # Excel brasileiro reconhece facilmente CSV com ; e , decimal
    return df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")
