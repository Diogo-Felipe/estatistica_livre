"""Importação e exportação de tabelas, sem dependência de interface."""
from __future__ import annotations
import io
import pandas as pd


def _decodificar(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def _validar_linha(linha_cabecalho) -> int:
    try:
        n = int(linha_cabecalho)
    except (TypeError, ValueError):
        raise ValueError("A linha do cabeçalho deve ser um número inteiro (1 = primeira linha).") from None
    if n < 1:
        raise ValueError("A linha do cabeçalho deve ser 1 ou maior (1 = primeira linha).")
    return n


def prever_arquivo(uploaded, aba=0, linhas: int = 25) -> pd.DataFrame:
    """Primeiras linhas do arquivo SEM interpretar cabeçalho, para o usuário escolher a linha.

    O índice é o número da linha (1 = primeira linha do arquivo/aba).
    """
    name = uploaded.name.lower()
    raw = uploaded.getvalue()
    if name.endswith(".csv"):
        texto = _decodificar(raw).splitlines()[:linhas]
        prev = pd.DataFrame({"Conteúdo da linha": texto})
    elif name.endswith(".xlsx"):
        prev = pd.read_excel(io.BytesIO(raw), sheet_name=aba, header=None, nrows=linhas, engine="openpyxl")
        prev.columns = [f"Coluna {i + 1}" for i in range(prev.shape[1])]
    else:
        raise ValueError("Use arquivos .csv ou .xlsx.")
    # Pré-visualização é só texto: células vazias em branco e inteiros sem ".0".
    def _txt(v):
        if pd.isna(v):
            return ""
        return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)
    prev = prev.map(_txt)
    prev.index = range(1, len(prev) + 1)
    prev.index.name = "Linha"
    return prev


class ColunasSemNomeError(ValueError):
    """Há colunas com dados mas sem nome no cabeçalho; o chamador decide nomear ou remover.

    `colunas`: lista de dicts {chave, posicao (1 = primeira coluna), exemplos}.
    """

    def __init__(self, mensagem: str, colunas: list[dict]):
        super().__init__(mensagem)
        self.colunas = colunas


def _validar_nome_novo(nome: str) -> str:
    nome = str(nome).strip()
    if not nome:
        raise ValueError("O nome da coluna não pode ficar vazio.")
    if len(nome) > 100 or "\n" in nome or "\r" in nome or nome.startswith("_"):
        raise ValueError(f"Nome inválido: '{nome[:30]}'. Use até 100 caracteres, sem quebra de linha e sem "
                         "começar com sublinhado.")
    return nome


def _opcoes_csv(sep: str, decimal: str, encoding: str, linha: int) -> dict:
    kw = {"decimal": decimal, "encoding": encoding, "skiprows": linha - 1}
    kw.update({"sep": None, "engine": "python"} if sep == "automático" else {"sep": sep})
    return kw


MAX_COLUNAS = 500


def _ler_csv(raw: bytes, sep: str, decimal: str, linha: int) -> tuple[pd.DataFrame, str]:
    """Lê o CSV contando os campos reais.

    Se o cabeçalho tiver MENOS campos que as linhas de dados, o pandas usaria silenciosamente a(s)
    primeira(s) coluna(s) de dados como índice e deslocaria os valores em relação aos nomes. Por isso o
    número de colunas é medido numa amostra (com nomes provisórios) e a leitura final usa exatamente
    esse número; campos do cabeçalho ausentes ou vazios viram "Unnamed: i".
    """
    for enc in ("utf-8-sig", "cp1252"):
        try:
            kw = _opcoes_csv(sep, decimal, enc, linha)
            amostra = pd.read_csv(io.BytesIO(raw), **kw, header=None, names=range(MAX_COLUNAS),
                                  dtype=str, nrows=500)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - cp1252 decodifica quase tudo
        raise ValueError("Não foi possível decodificar o arquivo (use UTF-8 ou Windows-1252).")
    em_uso = amostra.notna().any(axis=0).to_numpy().nonzero()[0]
    if len(em_uso) == 0:
        raise ValueError("Arquivo não contém observações a partir da linha de cabeçalho escolhida.")
    total = int(em_uso.max()) + 1
    if total >= MAX_COLUNAS:
        raise ValueError(f"O arquivo tem mais de {MAX_COLUNAS - 1} colunas; confira o separador escolhido.")
    cab = [None if pd.isna(v) or not str(v).strip() else str(v).strip() for v in amostra.iloc[0, :total]]
    df = pd.read_csv(io.BytesIO(raw), **kw, header=0, names=range(total))
    df.columns = [n if n else f"Unnamed: {i}" for i, n in enumerate(cab)]
    return df, enc


def ler_arquivo(uploaded, sep: str = "automático", decimal: str = ",", aba=0,
                linha_cabecalho: int = 1, colunas_sem_nome: dict | None = None) -> pd.DataFrame:
    """Lê .csv/.xlsx. `linha_cabecalho` é 1-based: linhas anteriores (ex.: notas) são ignoradas.

    Colunas com dados mas sem nome no cabeçalho levantam `ColunasSemNomeError`, a menos que
    `colunas_sem_nome` diga o que fazer com cada uma: {chave: "novo nome"} para nomear ou
    {chave: None} para removê-la da base importada.
    """
    linha = _validar_linha(linha_cabecalho)
    decisoes = colunas_sem_nome or {}
    name = uploaded.name.lower()
    raw = uploaded.getvalue()
    if name.endswith(".csv"):
        df, encoding = _ler_csv(raw, sep, decimal, linha)
    elif name.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(raw), sheet_name=aba, header=linha - 1, engine="openpyxl")
    else:
        raise ValueError("Use arquivos .csv ou .xlsx.")
    # O pandas renomeia silenciosamente cabeçalhos repetidos ("a", "a" -> "a", "a.1"); por isso a
    # checagem é feita na linha de cabeçalho bruta, antes dessa renomeação.
    if name.endswith(".csv"):
        bruto = pd.read_csv(io.BytesIO(raw), **{**_opcoes_csv(sep, decimal, encoding, linha), "skiprows": linha - 1},
                            header=None, nrows=1, dtype=str)
    else:
        bruto = pd.read_excel(io.BytesIO(raw), sheet_name=aba, header=None, skiprows=linha - 1, nrows=1,
                              dtype=str, engine="openpyxl")
    nomes = [str(v).strip() for v in bruto.iloc[0].dropna()] if len(bruto) else []
    repetidos = sorted({n for n in nomes if nomes.count(n) > 1})
    if repetidos:
        raise ValueError(f"Há nomes de colunas repetidos na linha {linha}: {', '.join(repetidos)}. "
                         "Renomeie as variáveis no arquivo ou confira se a linha do cabeçalho está correta.")
    # Resíduos de formatação de planilhas: linhas totalmente vazias e colunas vazias SEM nome.
    # Colunas com nome, mesmo vazias, são variáveis reais e permanecem.
    vazias_sem_nome = [c for c in df.columns if str(c).startswith("Unnamed:") and df[c].isna().all()]
    df = df.drop(columns=vazias_sem_nome).dropna(axis=0, how="all")
    if df.empty:
        raise ValueError("Arquivo não contém observações a partir da linha de cabeçalho escolhida.")

    # Colunas com dados e sem nome: o usuário decide entre nomear e remover.
    semnome = [c for c in df.columns if str(c).startswith("Unnamed:")]
    pendentes = [c for c in semnome if c not in decisoes]
    if pendentes:
        info = []
        for c in pendentes:
            exemplos = [str(v) for v in df[c].dropna().head(3)]
            info.append({"chave": c, "posicao": int(str(c).split(":")[1]) + 1, "exemplos": exemplos})
        raise ColunasSemNomeError(
            f"Há {len(pendentes)} coluna(s) com dados mas sem nome na linha {linha}. "
            "Dê um nome a cada uma ou remova-a, ou confira se a linha do cabeçalho está correta.", info)
    remover = [c for c in semnome if decisoes[c] is None]
    novos = {c: _validar_nome_novo(decisoes[c]) for c in semnome if decisoes[c] is not None}
    df = df.drop(columns=remover).rename(columns=novos)
    df.columns = [str(c).strip() for c in df.columns]
    repetidos = sorted({c for c in df.columns if list(df.columns).count(c) > 1})
    if repetidos:
        raise ValueError(f"Nome(s) repetido(s) após nomear as colunas: {', '.join(repetidos)}. "
                         "Cada variável precisa de um nome único.")
    if df.empty or len(df.columns) == 0:
        raise ValueError("Não restaram colunas para importar.")
    return df.reset_index(drop=True)


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
