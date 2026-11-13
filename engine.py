"""Motor estatístico: independente da interface Streamlit.

Convenção: cada linha é uma unidade amostral independente; testes pareados
fazem pareamento dentro da linha. Remoção de dados faltantes por análise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats


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
    return Resultado(nome, simbolo, float(r), float(p), len(d),
                     observacoes=f"Pares completos: {len(d)}; exclusão por pares. Associação não implica causalidade.")


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
    return Resultado("Wilcoxon pareado", "W", float(w), float(p), len(d),
                     observacoes=f"Pares: {len(d)}; diferenças zero: {sum(dif==0)}. "
                                 "Para interpretação sobre a mediana das diferenças, considere a simetria da distribuição.")


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
