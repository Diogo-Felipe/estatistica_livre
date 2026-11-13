"""Catálogo de procedimentos e execução, sem dependência do Streamlit.

Concentra a ligação entre a interface e o engine para que possa ser testada sozinha.
Não contém cálculo estatístico: toda estatística vem de engine.py.
"""
from __future__ import annotations

import engine
import interpretacao
import reports

# objetivo do usuário -> procedimentos adequados
OBJETIVOS: dict[str, list[str]] = {
    "Descrever e explorar os dados": ["Descritiva", "Shapiro-Wilk"],
    "Comparar dois grupos independentes": ["t independente (Welch)", "Mann–Whitney U"],
    "Comparar duas medidas dos mesmos participantes": ["t pareado", "Wilcoxon pareado"],
    "Comparar três ou mais medidas dos mesmos participantes": ["Friedman"],
    "Comparar três ou mais grupos": ["ANOVA de uma via"],
    "Relacionar duas variáveis numéricas": ["Correlação (Pearson / Spearman)"],
    "Relacionar duas variáveis categóricas": ["Qui-quadrado / Fisher"],
}

GUIA: dict[str, dict[str, str]] = {
    "Descritiva": {
        "resumo": "Média, desvio-padrão, mediana, quartis, mínimo e máximo.",
        "quando": "Para resumir variáveis numéricas antes de qualquer teste.",
        "pressupostos": "Nenhum pressuposto inferencial.",
    },
    "Shapiro-Wilk": {
        "resumo": "Testa evidência contra a normalidade de uma variável.",
        "quando": "Para decidir entre métodos paramétricos e não paramétricos.",
        "pressupostos": "Amostra aleatória; N entre 3 e 5000. Não comprova normalidade.",
    },
    "t independente (Welch)": {
        "resumo": "Compara as médias de dois grupos independentes.",
        "quando": "Variável numérica aproximadamente normal em cada grupo.",
        "pressupostos": "Observações independentes; não exige variâncias iguais.",
    },
    "Mann–Whitney U": {
        "resumo": "Compara a distribuição (postos) de dois grupos independentes.",
        "quando": "Dados ordinais, com outliers ou fora da normalidade.",
        "pressupostos": "Observações independentes; formatos semelhantes para falar em medianas.",
    },
    "t pareado": {
        "resumo": "Compara duas medidas feitas nos mesmos participantes (média das diferenças).",
        "quando": "Antes/depois ou duas condições no mesmo indivíduo.",
        "pressupostos": "Diferenças entre pares aproximadamente normais.",
    },
    "Wilcoxon pareado": {
        "resumo": "Versão não paramétrica do teste t pareado (postos das diferenças).",
        "quando": "Pareamento com dados ordinais ou diferenças fora da normalidade.",
        "pressupostos": "Diferenças simétricas para interpretar como mediana das diferenças.",
    },
    "Friedman": {
        "resumo": "Compara três ou mais medidas repetidas nos mesmos participantes (postos dentro de cada participante).",
        "quando": "Ex.: tempo de reação em 4 ângulos, ou 3 ou mais momentos, quando os dados não são normais ou são ordinais.",
        "pressupostos": "Participantes independentes entre si; só entram os que têm TODAS as medidas. "
                        "Não inclui pós-testes entre pares.",
    },
    "ANOVA de uma via": {
        "resumo": "Compara as médias de três ou mais grupos independentes.",
        "quando": "Variável numérica e um fator categórico.",
        "pressupostos": "Independência, resíduos normais e variâncias semelhantes. Sem pós-testes.",
    },
    "Correlação (Pearson / Spearman)": {
        "resumo": "Mede a força e a direção da associação entre duas variáveis numéricas.",
        "quando": "Spearman para relações monotônicas ou dados ordinais; Pearson para relações lineares.",
        "pressupostos": "Pares independentes. Associação não implica causalidade.",
    },
    "Qui-quadrado / Fisher": {
        "resumo": "Testa associação entre duas variáveis categóricas.",
        "quando": "Tabelas de contagens; Fisher é usado em 2×2 com frequências esperadas baixas.",
        "pressupostos": "Contagens de participantes independentes.",
    },
}


def executar(metodo: str, analise, parametros: dict, alpha: float, fonte: str) -> dict:
    """Roda o procedimento e devolve o registro pronto para o histórico/relatório."""
    if metodo == "Descritiva":
        tabela = engine.descritiva(analise, parametros["Variáveis"])
        reg = reports.registrar_resultado(
            metodo, ", ".join(parametros["Variáveis"]), tabela, len(analise), alpha,
            nota="N válido/ausente indicado por variável; uma linha por caso.",
            fonte=fonte, tipo="descritiva")
        return reg
    if metodo == "Shapiro-Wilk":
        r = engine.normalidade(analise, parametros["Variável"])
    elif metodo == "Correlação (Pearson / Spearman)":
        r = engine.correlacao(analise, parametros["X"], parametros["Y"], parametros["Método"].lower())
    elif metodo == "t independente (Welch)":
        r = engine.t_independente(analise, parametros["Variável"], parametros["Grupo"],
                                  parametros["Grupo 1"], parametros["Grupo 2"])
    elif metodo == "Mann–Whitney U":
        r = engine.mann_whitney(analise, parametros["Variável"], parametros["Grupo"],
                                parametros["Grupo 1"], parametros["Grupo 2"])
    elif metodo == "t pareado":
        r = engine.t_pareado(analise, parametros["Medida 1"], parametros["Medida 2"])
    elif metodo == "Wilcoxon pareado":
        r = engine.wilcoxon_pareado(analise, parametros["Medida 1"], parametros["Medida 2"])
    elif metodo == "Friedman":
        r = engine.friedman(analise, parametros["Medidas"])
    elif metodo == "ANOVA de uma via":
        r = engine.anova(analise, parametros["Variável"], parametros["Grupo"])
    elif metodo == "Qui-quadrado / Fisher":
        r = engine.qui_quadrado(analise, parametros["Categoria 1"], parametros["Categoria 2"])
    else:
        raise ValueError(f"Procedimento desconhecido: {metodo}")
    texto_params = {k: (", ".join(v) if isinstance(v, list) else v) for k, v in parametros.items()}
    reg = reports.registrar_engine(r, texto_params, alpha, fonte)
    texto, tom = interpretacao.conclusao(r.tipo, r.p, alpha)
    reg["conclusao"], reg["tom"] = texto, tom
    reg["magnitude"] = interpretacao.descrever_efeito(r)
    return reg
