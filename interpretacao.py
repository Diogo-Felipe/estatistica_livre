"""Textos de interpretação e magnitude de efeito, sem dependência do Streamlit.

Não calcula nenhuma estatística: apenas descreve, em linguagem simples, resultados
já calculados pelo engine. Limiares de magnitude são referências convencionais
(Cohen, 1988) e devem ser interpretados conforme o contexto da pesquisa.
"""
from __future__ import annotations

import math


def formatar_p(p) -> str:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "—"
    if p < .0001:
        return "< 0,0001"
    return f"{p:.4f}".replace(".", ",")


def _faixa(valor: float, limites: tuple[float, float, float], rotulos=("desprezível", "pequeno", "médio", "grande")) -> str:
    v = abs(valor)
    if v < limites[0]:
        return rotulos[0]
    if v < limites[1]:
        return rotulos[1]
    if v < limites[2]:
        return rotulos[2]
    return rotulos[3]


def magnitude(nome_efeito: str, valor: float, forma_tabela: tuple[int, int] | None = None) -> str:
    """Rótulo convencional do tamanho de efeito; '' quando não há referência segura."""
    if not nome_efeito or valor is None or not math.isfinite(valor):
        return ""
    n = nome_efeito.lower()
    if n.startswith("d de cohen"):
        return _faixa(valor, (.2, .5, .8), ("insignificante", "pequeno", "médio", "grande"))
    if n.startswith("η²"):
        return _faixa(valor, (.01, .06, .14))
    if n.startswith("w de kendall"):
        return _faixa(valor, (.1, .3, .5))
    if n.startswith("correlação bisserial"):
        return _faixa(valor, (.1, .3, .5))
    if n.startswith("v de cram"):
        if not forma_tabela:
            return ""
        gl = max(1, min(forma_tabela[0] - 1, forma_tabela[1] - 1))
        s = math.sqrt(gl)
        return _faixa(valor, (.1 / s, .3 / s, .5 / s))
    return ""


def magnitude_correlacao(r: float) -> str:
    if r is None or not math.isfinite(r):
        return ""
    return _faixa(r, (.1, .3, .5))


def conclusao(tipo: str, p, alpha: float) -> tuple[str, str]:
    """Devolve (texto, tom) com tom em {'sucesso','aviso','neutro'}."""
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "", "neutro"
    pt, at = formatar_p(p), str(alpha).replace(".", ",")
    ptxt = f"p {pt}" if pt.startswith("<") else f"p = {pt}"  # evita "p = < 0,0001"
    sinal = "<" if p < alpha else "≥"
    if tipo == "normalidade":
        if p < alpha:
            return (f"{ptxt} {sinal} α ({at}): há evidência contra a hipótese de normalidade. "
                    "Considere métodos não paramétricos.", "aviso")
        return (f"{ptxt} {sinal} α ({at}): não houve evidência suficiente contra a normalidade. "
                "Isso não comprova que os dados sejam normais.", "neutro")
    if p < alpha:
        return (f"{ptxt} {sinal} α ({at}): há evidência estatística contra a hipótese nula.", "sucesso")
    return (f"{ptxt} {sinal} α ({at}): não houve evidência suficiente contra a hipótese nula. "
            "Isso não demonstra que não haja diferença ou associação.", "neutro")


def descrever_efeito(resultado) -> str:
    """Texto curto com o tamanho de efeito e sua magnitude convencional."""
    forma = None
    if resultado.nome.startswith(("Qui-quadrado", "Exato de Fisher")) and not resultado.detalhes.empty:
        forma = (resultado.detalhes.shape[0], resultado.detalhes.shape[1] - 1)
    if resultado.efeito_nome and math.isfinite(resultado.efeito_valor):
        rotulo = magnitude(resultado.efeito_nome, resultado.efeito_valor, forma)
        base = f"{resultado.efeito_nome} = {resultado.efeito_valor:.3f}".replace(".", ",")
        return f"{base} ({rotulo})" if rotulo else base
    if resultado.nome.startswith("Correlação"):
        rotulo = magnitude_correlacao(resultado.valor)
        direcao = "positiva" if resultado.valor > 0 else "negativa" if resultado.valor < 0 else "nula"
        return f"Correlação {direcao}, magnitude {rotulo}" if rotulo else ""
    return ""
