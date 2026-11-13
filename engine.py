"""Motor estatístico: independente da interface Streamlit.

Convenção: cada linha é uma unidade amostral independente; testes pareados
fazem pareamento dentro da linha. Remoção de dados faltantes por análise.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import stats


MAX_CATEGORIAS = 30
SPEARMAN_EXATO_MAX_N = 9          # 9! = 362.880 permutações; acima disso usa-se a aproximação
FRIEDMAN_EXATO_MAX_OPERACOES = 2_000_000   # ~2 s no pior caso; acima disso usa-se a aproximação χ²
PMIN_ALERTA = 0.05


@lru_cache(maxsize=None)
def _permutacoes(n: int) -> np.ndarray:
    """Todas as permutações dos índices 0..n-1 (n! linhas)."""
    return np.array(list(itertools.permutations(range(n))), dtype=np.int8)


def spearman_exato(x, y) -> tuple[float, float, float, int]:
    """Teste de permutação exato para o ρ de Spearman (bilateral).

    Permuta os postos de y contra os de x (postos médios em caso de empates, condicionando
    nos empates observados). Devolve (rho, p exato, menor p possível, nº de permutações).
    """
    rx = stats.rankdata(np.asarray(x, dtype=float))
    ry = stats.rankdata(np.asarray(y, dtype=float))
    n = len(rx)
    rxc, ryc = rx - rx.mean(), ry - ry.mean()
    denom = math.sqrt(float(rxc @ rxc) * float(ryc @ ryc))
    perms = _permutacoes(n)
    rhos = (ryc[perms] @ rxc) / denom
    obs = float(rxc @ ryc) / denom
    tol = 1e-9
    p = float(np.mean(np.abs(rhos) >= abs(obs) - tol))
    p_min = float(np.mean(np.abs(rhos) >= np.max(np.abs(rhos)) - tol))
    return obs, p, p_min, len(perms)


@dataclass
class Resultado:
    nome: str
    estatistica: str
    valor: float
    p: float
    n: int
    efeito_nome: str = ""
    efeito_valor: float = float("nan")
    detalhes: pd.DataFrame = field(default_factory=pd.DataFrame)
    observacoes: str = ""
    tipo: str = "inferencial"  # 'normalidade' para interpretação específica


def _numeric(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        raise ValueError(f"A variável '{column}' não existe na base.")
    return pd.to_numeric(df[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def _pairs(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    if a == b:
        raise ValueError("Selecione duas variáveis diferentes.")
    return pd.DataFrame({"x": _numeric(df, a), "y": _numeric(df, b)}).dropna()


def _grouped(df: pd.DataFrame, variable: str, group: str, level1, level2):
    if group not in df.columns:
        raise ValueError("A coluna de agrupamento não existe.")
    if level1 == level2:
        raise ValueError("Escolha dois grupos distintos.")
    d = pd.DataFrame({"valor": _numeric(df, variable), "grupo": df[group]}).dropna()
    a = d.loc[d["grupo"] == level1, "valor"].to_numpy(dtype=float)
    b = d.loc[d["grupo"] == level2, "valor"].to_numpy(dtype=float)
    if len(a) < 2 or len(b) < 2:
        raise ValueError("Cada grupo deve ter pelo menos 2 valores válidos.")
    return a, b


def descritiva(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if not columns:
        raise ValueError("Selecione pelo menos uma variável numérica.")
    rows = []
    for col in columns:
        x = _numeric(df, col).dropna()
        rows.append({
            "Variável": col, "N válido": len(x), "Ausentes": len(df)-len(x),
            "Média": x.mean() if len(x) else np.nan,
            "DP": x.std(ddof=1) if len(x)>1 else np.nan,
            "Mediana": x.median() if len(x) else np.nan,
            "Q1": x.quantile(.25) if len(x) else np.nan,
            "Q3": x.quantile(.75) if len(x) else np.nan,
            "Mínimo": x.min() if len(x) else np.nan,
            "Máximo": x.max() if len(x) else np.nan,
        })
    return pd.DataFrame(rows)


def normalidade(df: pd.DataFrame, col: str) -> Resultado:
    x = _numeric(df, col).dropna().to_numpy(dtype=float)
    if len(x) < 3:
        raise ValueError("Shapiro-Wilk exige pelo menos 3 observações válidas.")
    if np.ptp(x) == 0:
        raise ValueError("A variável é constante; não é possível testar normalidade.")
    w, p = stats.shapiro(x)
    obs = "Shapiro-Wilk não comprova normalidade; testa evidência contra ela."
    if len(x) > 5000:
        obs += " Atenção: para N > 5000, o p-valor pode ser impreciso."
    return Resultado("Shapiro-Wilk", "W", float(w), float(p), len(x),
                     observacoes=obs, tipo="normalidade")


def correlacao(df: pd.DataFrame, a: str, b: str, metodo: str = "spearman") -> Resultado:
    d = _pairs(df, a, b)
    if len(d) < 3:
        raise ValueError("A correlação exige pelo menos 3 pares válidos.")
    if d.x.nunique() < 2 or d.y.nunique() < 2:
        raise ValueError("Não é possível correlacionar variáveis constantes.")
    if metodo == "pearson":
        r, p = stats.pearsonr(d.x, d.y)
        nome, simbolo = "Correlação de Pearson", "r"
    elif metodo == "spearman":
        r, p = stats.spearmanr(d.x, d.y)
        nome, simbolo = "Correlação de Spearman", "ρ"
    else:
        raise ValueError("Método de correlação inválido.")
    obs = f"Pares completos: {len(d)}; exclusão por pares. Associação não implica causalidade."
    if metodo == "spearman":
        if len(d) <= SPEARMAN_EXATO_MAX_N:
            # A aproximação pela distribuição t é imprecisa em amostras pequenas: usa-se o p exato.
            r, p, p_min, n_perm = spearman_exato(d.x, d.y)
            nome = "Correlação de Spearman (p exato)"
            obs += f" p exato por permutação ({n_perm:,} permutações dos postos)".replace(",", ".") + "."
            if p_min > PMIN_ALERTA:
                pm = _vir(p_min, 4)
                obs += (f" ATENÇÃO: com N = {len(d)} o menor p possível é {pm}; o teste não consegue "
                        "indicar significância a 5%, mesmo com correlação perfeita.")
        else:
            obs += " p-valor pela aproximação da distribuição t (amostra grande o bastante)."
    return Resultado(nome, simbolo, float(r), float(p), len(d), observacoes=obs)


def t_independente(df: pd.DataFrame, var: str, group: str, level1, level2) -> Resultado:
    a, b = _grouped(df, var, group, level1, level2)
    if np.var(a, ddof=1) == 0 and np.var(b, ddof=1) == 0:
        raise ValueError("Ambos os grupos têm variância zero; teste t inadequado.")
    t, p = stats.ttest_ind(a, b, equal_var=False)
    n1, n2 = len(a), len(b)
    v1, v2 = np.var(a, ddof=1), np.var(b, ddof=1)
    sp = math.sqrt(((n1-1)*v1+(n2-1)*v2)/(n1+n2-2))
    d = (a.mean()-b.mean())/sp if sp else float("nan")
    delta = float(a.mean()-b.mean())
    df_welch = ((v1/n1+v2/n2)**2)/((v1/n1)**2/(n1-1)+(v2/n2)**2/(n2-1))
    detalhes = pd.DataFrame([
        {"Grupo": str(level1), "N": n1, "Média": a.mean(), "DP": np.std(a, ddof=1)},
        {"Grupo": str(level2), "N": n2, "Média": b.mean(), "DP": np.std(b, ddof=1)},
    ])
    return Resultado("Teste t de Welch (independente)", "t", float(t), float(p), n1+n2,
                     "d de Cohen", float(d), detalhes,
                     f"Diferença de médias ({level1} − {level2}): {delta:.4g}; gl≈{df_welch:.2f}. "
                     "Welch não pressupõe variâncias iguais; exige grupos independentes.")


def t_pareado(df: pd.DataFrame, a: str, b: str) -> Resultado:
    d = _pairs(df, a, b)
    if len(d) < 2:
        raise ValueError("O teste t pareado exige pelo menos 2 pares completos.")
    delta = d.x.to_numpy() - d.y.to_numpy()
    if np.std(delta, ddof=1) == 0:
        raise ValueError("As diferenças pareadas são constantes; teste t inadequado.")
    t, p = stats.ttest_rel(d.x, d.y)
    dz = float(np.mean(delta)/np.std(delta, ddof=1))
    return Resultado("Teste t pareado", "t", float(t), float(p), len(d),
                     "d de Cohen (dz)", dz,
                     observacoes=f"Diferença média: {np.mean(delta):.4g}; gl={len(d)-1}. "
                                 "A suposição de normalidade se refere às diferenças entre pares.")


def mann_whitney(df: pd.DataFrame, var: str, group: str, level1, level2) -> Resultado:
    a, b = _grouped(df, var, group, level1, level2)
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided", method="auto")
    r_rb = 2*float(u)/(len(a)*len(b))-1
    tab = pd.DataFrame([
        {"Grupo": str(level1), "N": len(a), "Mediana": np.median(a)},
        {"Grupo": str(level2), "N": len(b), "Mediana": np.median(b)},
    ])
    return Resultado("Mann–Whitney U", "U (1º grupo)", float(u), float(p), len(a)+len(b),
                     "Correlação bisserial de postos", float(r_rb), tab,
                     "Grupos independentes. O teste compara distribuições; interpretação como "
                     "diferença de medianas requer distribuições de formato semelhante.")


def wilcoxon_pareado(df: pd.DataFrame, a: str, b: str) -> Resultado:
    d = _pairs(df, a, b)
    if len(d) < 3:
        raise ValueError("Requer pelo menos 3 pares completos.")
    dif = d.x.to_numpy() - d.y.to_numpy()
    if np.all(dif == 0):
        raise ValueError("Todas as diferenças são zero; não há teste aplicável.")
    w, p = stats.wilcoxon(dif, zero_method="wilcox", alternative="two-sided")
    # zero_method="wilcox" descarta diferenças nulas: o N do teste é o de diferenças não nulas.
    zeros = int(np.sum(dif == 0))
    n_teste = len(dif) - zeros
    obs = (f"Pares completos: {len(d)}; diferenças zero descartadas: {zeros}; "
           f"N analisado (diferenças não nulas): {n_teste}. "
           "Para interpretação sobre a mediana das diferenças, considere a simetria da distribuição.")
    nao_nulas = np.abs(dif[dif != 0])
    if len(np.unique(nao_nulas)) == len(nao_nulas):  # sem empates: p exato por enumeração de sinais
        p_min = 2 / 2 ** n_teste
        if p_min > PMIN_ALERTA:
            pm = _vir(p_min, 4)
            obs += (f" ATENÇÃO: com N = {n_teste} o menor p bilateral possível é {pm}; o teste não consegue "
                    "indicar significância a 5%, mesmo que todas as diferenças tenham o mesmo sinal.")
    return Resultado("Wilcoxon pareado", "W", float(w), float(p), n_teste, observacoes=obs)


def anova(df: pd.DataFrame, var: str, group: str) -> Resultado:
    if group not in df.columns:
        raise ValueError("Coluna de grupo inexistente.")
    d = pd.DataFrame({"valor": _numeric(df, var), "grupo": df[group]}).dropna()
    levels = list(pd.unique(d.grupo))
    if len(levels) < 2:
        raise ValueError("ANOVA exige pelo menos dois grupos válidos.")
    vals = [d.loc[d.grupo==level, "valor"].to_numpy(dtype=float) for level in levels]
    if any(len(v) < 2 for v in vals):
        raise ValueError("Todos os grupos devem possuir ao menos 2 observações válidas.")
    if np.ptp(d.valor.to_numpy()) == 0:
        raise ValueError("Todos os valores são iguais; não é possível executar ANOVA.")
    f, p = stats.f_oneway(*vals)
    overall = float(d.valor.mean())
    ss_between = sum(len(v)*(float(np.mean(v))-overall)**2 for v in vals)
    ss_total = float(np.sum((d.valor.to_numpy()-overall)**2))
    eta2 = ss_between/ss_total if ss_total else float("nan")
    lev_stat, lev_p = stats.levene(*vals, center="median")
    details = pd.DataFrame([{"Grupo": str(l), "N": len(v), "Média": float(np.mean(v)),
                             "DP": float(np.std(v, ddof=1))} for l, v in zip(levels, vals)])
    return Resultado("ANOVA de uma via", "F", float(f), float(p), len(d), "η²", float(eta2), details,
                     f"gl=({len(vals)-1}, {len(d)-len(vals)}); Levene (mediana) p={lev_p:.4g}. "
                     "Verifique normalidade dos resíduos e homogeneidade das variâncias. "
                     "ANOVA significativa não identifica quais grupos diferem (pós-teste não incluído).")


def qui_quadrado(df: pd.DataFrame, a: str, b: str) -> Resultado:
    if a == b:
        raise ValueError("Selecione variáveis categóricas distintas.")
    if a not in df.columns or b not in df.columns:
        raise ValueError("Coluna inexistente.")
    d = df[[a,b]].dropna()
    tab = pd.crosstab(d[a].astype(str), d[b].astype(str))
    if tab.shape[0] < 2 or tab.shape[1] < 2:
        raise ValueError("O teste exige ao menos duas categorias por variável.")
    if tab.shape[0] > MAX_CATEGORIAS or tab.shape[1] > MAX_CATEGORIAS:
        raise ValueError(f"Variável com mais de {MAX_CATEGORIAS} categorias ({tab.shape[0]}×{tab.shape[1]}). "
                         "Provavelmente não é categórica (ex.: variável contínua); escolha outra variável.")
    chi, p, gl, expected = stats.chi2_contingency(tab, correction=False)
    n = int(tab.to_numpy().sum())
    v = math.sqrt(float(chi)/(n*min(tab.shape[0]-1, tab.shape[1]-1)))
    baixo = int(np.sum(expected < 5))
    obs = (f"χ²: gl={gl}; {baixo}/{expected.size} frequências esperadas <5 "
           f"({100*baixo/expected.size:.1f}%). ")
    test, stat, p_selected = "Qui-quadrado de Pearson", "χ²", float(p)
    stat_val = float(chi)
    if tab.shape == (2, 2):
        odds, p_fisher = stats.fisher_exact(tab.to_numpy())
        obs += f"Fisher bilateral p={p_fisher:.4g}; χ² sem correção p={p:.4g}. "
        if baixo:
            test, stat, stat_val, p_selected = "Exato de Fisher (2×2)", "Odds ratio", float(odds), float(p_fisher)
    elif baixo/expected.size > .20 or np.any(expected < 1):
        obs += "A aproximação do χ² pode ser inadequada; considere agrupar categorias justificadamente ou teste exato/Monte Carlo. "
    return Resultado(test, stat, stat_val, p_selected, n, "V de Cramér", float(v),
                     tab.reset_index(), obs + "Frequências são contagens de participantes independentes.")


def _vir(valor: float, casas: int) -> str:
    """Número com vírgula decimal, para textos em português."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _friedman_p_exato(ranks: np.ndarray, chi_obs_s2: int) -> float | None:
    """p exato do Friedman por convolução das somas de postos, condicional aos empates observados.

    Usa postos dobrados (inteiros) para evitar erro de ponto flutuante. Estados equivalentes por
    permutação das condições são fundidos (a estatística é simétrica nas condições). Devolve None
    se o custo estimado passar de FRIEDMAN_EXATO_MAX_OPERACOES.
    """
    n, k = ranks.shape
    estados = {tuple([0] * k): 1}
    operacoes = 0
    for i in range(n):
        perms = set(itertools.permutations(tuple(int(round(2 * r)) for r in ranks[i])))
        operacoes += len(estados) * len(perms)
        if operacoes > FRIEDMAN_EXATO_MAX_OPERACOES:
            return None
        novos: dict[tuple, int] = {}
        for est, cont in estados.items():
            for perm in perms:
                chave = tuple(sorted(a + b for a, b in zip(est, perm)))
                novos[chave] = novos.get(chave, 0) + cont
        estados = novos
    total = sum(estados.values())
    favoraveis = sum(c for est, c in estados.items() if sum(s * s for s in est) >= chi_obs_s2)
    return favoraveis / total


def friedman(df: pd.DataFrame, columns: list[str]) -> Resultado:
    """Teste de Friedman para k ≥ 3 medidas repetidas nos mesmos participantes (casos completos)."""
    if len(set(columns)) != len(columns):
        raise ValueError("Selecione medidas diferentes.")
    if len(columns) < 3:
        raise ValueError("O teste de Friedman exige pelo menos 3 medidas (para 2 medidas use Wilcoxon pareado).")
    d = pd.DataFrame({c: _numeric(df, c) for c in columns}).dropna()
    n, k = d.shape
    if n < 2:
        raise ValueError("O teste de Friedman exige pelo menos 2 participantes com todas as medidas válidas.")
    m = d.to_numpy(dtype=float)
    ranks = np.apply_along_axis(stats.rankdata, 1, m)
    if np.all(ranks == (k + 1) / 2):
        raise ValueError("Todas as medidas são iguais em todos os participantes; o teste não é aplicável.")
    soma = ranks.sum(axis=0)
    # correção de empates (a mesma usada por scipy.stats.friedmanchisquare)
    termo_empates = 0.0
    for linha in ranks:
        _, cont = np.unique(linha, return_counts=True)
        termo_empates += float(np.sum(cont ** 3 - cont))
    c = 1 - termo_empates / (n * k * (k * k - 1))
    chi = (12 / (n * k * (k + 1)) * float(np.sum(soma ** 2)) - 3 * n * (k + 1)) / c
    kendall_w = chi / (n * (k - 1))
    p_assint = float(stats.chi2.sf(chi, k - 1))
    s2_obs = int(round(float(np.sum((2 * soma) ** 2))))
    p_exato = _friedman_p_exato(ranks, s2_obs)
    if p_exato is not None:
        nome, p = "Teste de Friedman (p exato)", p_exato
        metodo = f"p exato por enumeração dos postos (aproximação χ² com gl = {k - 1}: p = {_vir(p_assint, 4)})."
    else:
        nome, p = "Teste de Friedman (aproximação χ²)", p_assint
        metodo = (f"p pela aproximação χ² com gl = {k - 1} (a enumeração exata seria grande demais para "
                  f"N = {n} e {k} medidas).")
    detalhes = pd.DataFrame({
        "Medida": columns, "N": n,
        "Mediana": [float(np.median(m[:, j])) for j in range(k)],
        "Média": [float(np.mean(m[:, j])) for j in range(k)],
        "Ordem média": [float(np.mean(ranks[:, j])) for j in range(k)],
    })
    obs = (f"Participantes com todas as {k} medidas válidas: {n} (o caso inteiro sai se faltar alguma). "
           f"χ² = {_vir(chi, 4)} com gl = {k - 1}. {metodo} "
           "O teste indica se há diferença global entre as medidas; pós-testes entre pares não estão incluídos "
           "(se usar vários Wilcoxon, corrija a multiplicidade). Com N pequeno, o poder é baixo.")
    return Resultado(nome, "χ²", float(chi), float(p), n, "W de Kendall", float(kendall_w), detalhes, obs)
