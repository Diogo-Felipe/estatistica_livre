"""Salva/restaura um projeto Estatística Livre em um ZIP de arquivos seguros.

Não extrai caminhos fornecidos pelo usuário no sistema de arquivos.
"""
from __future__ import annotations
import io
import json
import zipfile
import pandas as pd

MAX_PROJECT_SIZE = 30 * 1024 * 1024


def exportar_projeto(df: pd.DataFrame, schema: dict, nome: str) -> bytes:
    if df.empty:
        raise ValueError("Não há dados para salvar.")
    manifest = {"aplicativo": "Estatística Livre", "formato": 1, "versao": "0.2", "nome": nome}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifesto.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        z.writestr("dados.json", df.to_json(orient="table", date_format="iso", force_ascii=False, index=False))
        z.writestr("variaveis.json", json.dumps(schema, ensure_ascii=False, indent=2))
    return buf.getvalue()


def importar_projeto(content: bytes) -> tuple[pd.DataFrame, dict, str]:
    if len(content) > MAX_PROJECT_SIZE:
        raise ValueError("Projeto muito grande para importação (limite: 30 MB).")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            required = {"manifesto.json", "dados.json", "variaveis.json"}
            if not required.issubset(z.namelist()):
                raise ValueError("Arquivo ZIP não é um projeto Estatística Livre válido.")
            if any(z.getinfo(f).file_size > MAX_PROJECT_SIZE for f in required):
                raise ValueError("Projeto descompactado acima do limite de segurança.")
            manifest = json.loads(z.read("manifesto.json"))
            if manifest.get("aplicativo") != "Estatística Livre" or manifest.get("formato") != 1:
                raise ValueError("Formato de projeto não reconhecido.")
            df = pd.read_json(io.StringIO(z.read("dados.json").decode("utf-8")), orient="table")
            schema = json.loads(z.read("variaveis.json"))
            if not isinstance(schema, dict) or list(schema) != list(df.columns):
                raise ValueError("O dicionário de variáveis não corresponde aos dados.")
            for key, entry in schema.items():
                if not isinstance(entry, dict) or any(k not in entry for k in ("rotulo", "tipo", "medida", "ausentes", "valores")):
                    raise ValueError("Metadados de variáveis inválidos.")
            if df.empty:
                raise ValueError("O projeto está vazio.")
            return df, schema, str(manifest.get("nome") or "Projeto restaurado")
    except (zipfile.BadZipFile, UnicodeDecodeError, KeyError, ValueError, TypeError) as err:
        raise ValueError(f"Não foi possível restaurar o projeto: {err}") from err
