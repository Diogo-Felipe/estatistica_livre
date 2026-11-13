"""Spearman com p exato (n pequeno) e teste de Friedman.

Oráculos independentes: enumeração por força bruta (itertools + numpy.corrcoef) e fórmulas fechadas,
nunca a mesma rotina que está sendo testada.
"""
import itertools
import math
import time
import unittest

import numpy as np
import pandas as pd
from scipy import stats

import engine
import procedimentos


def p_spearman_forca_bruta(x, y):
    """Referência: permuta explicitamente os postos de y e usa corrcoef para cada permutação."""
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    obs = abs(np.corrcoef(rx, ry)[0, 1])
    cont = tot = 0
    for perm in itertools.permutations(ry):
        tot += 1
        cont += abs(np.corrcoef(rx, perm)[0, 1]) >= obs - 1e-9
    return cont / tot


def p_friedman_forca_bruta(m):
    """Referência: percorre o produto cartesiano das permutações dos postos de cada participante."""
    m = np.asarray(m, float)
    n, k = m.shape
    ranks = [stats.rankdata(l) for l in m]
    obs = np.sum(np.sum(ranks, axis=0) ** 2)
    blocos = [sorted(set(itertools.permutations(r))) for r in ranks]
    cont = tot = 0
    for combo in itertools.product(*blocos):
        tot += 1
        cont += np.sum(np.sum(combo, axis=0) ** 2) >= obs - 1e-9
    return cont / tot


class TestesSpearmanExato(unittest.TestCase):
    def corr(self, x, y):
        return engine.correlacao(pd.DataFrame({"x": x, "y": y}), "x", "y", "spearman")

    def test_n4_valores_conhecidos_da_distribuicao_exata(self):
        # 24 permutações; contagens de |rho| >= observado (à mão, por soma de d²): 2, 8, 10, 18, 24
        x = [1, 2, 3, 4]
        # rho = 1 (p = 2/24); rho = 0,8 (8/24); rho = 0,6 (10/24); rho = 0,4 (18/24); rho = 0 (24/24)
        esperado = [((1, 2, 3, 4), 1.0, 2 / 24), ((1, 2, 4, 3), 0.8, 8 / 24), ((2, 1, 4, 3), 0.6, 10 / 24),
                    ((1, 3, 4, 2), 0.4, 18 / 24), ((2, 4, 1, 3), 0.0, 24 / 24)]
        for y, rho_esp, p_esp in esperado:
            with self.subTest(y=y):
                r = self.corr(x, list(y))
                self.assertAlmostEqual(r.valor, rho_esp, places=9)
                self.assertAlmostEqual(r.p, p_esp, places=12)
                # sinal negativo: mesma magnitude, mesmo p
                rneg = self.corr(x, [5 - v for v in y])
                self.assertAlmostEqual(rneg.valor, -rho_esp, places=9)
                self.assertAlmostEqual(rneg.p, p_esp, places=12)

    def test_n4_menor_p_possivel_e_aviso(self):
        r = self.corr([1, 2, 3, 4], [10, 20, 30, 40])
        self.assertAlmostEqual(r.p, 2 / 24, places=12)
        self.assertEqual(r.nome, "Correlação de Spearman (p exato)")
        self.assertIn("p exato por permutação", r.observacoes)
        self.assertIn("ATENÇÃO", r.observacoes)
        self.assertIn("0,0833", r.observacoes)

    def test_igual_a_forca_bruta_para_varios_n_com_e_sem_empates(self):
        rng = np.random.default_rng(42)
        for n in (3, 4, 5, 6, 7):
            for _ in range(4):
                x = rng.normal(size=n)
                y = rng.normal(size=n)
                with self.subTest(n=n, tipo="sem empates"):
                    if len(set(x)) > 1 and len(set(y)) > 1:
                        self.assertAlmostEqual(self.corr(x, y).p, p_spearman_forca_bruta(x, y), places=12)
        for x, y in [([1, 2, 2, 4, 5], [3, 1, 4, 4, 2]), ([1, 1, 2, 3, 3, 4], [2, 1, 3, 3, 5, 4])]:
            with self.subTest(x=x, y=y):
                self.assertAlmostEqual(self.corr(x, y).p, p_spearman_forca_bruta(x, y), places=12)

    def test_n3_p_minimo_e_0_33(self):
        self.assertAlmostEqual(self.corr([1, 2, 3], [1, 2, 3]).p, 2 / 6, places=12)

    def test_sem_aviso_quando_o_teste_consegue_alcancar_5_por_cento(self):
        r = self.corr(list(range(7)), list(range(7)))      # n=7: menor p = 2/5040
        self.assertAlmostEqual(r.p, 2 / 5040, places=12)
        self.assertNotIn("ATENÇÃO", r.observacoes)

    def test_n9_ainda_e_exato_e_rapido(self):
        t = time.time()
        r = self.corr(list(range(9)), [1, 0, 3, 2, 5, 4, 7, 6, 8])
        self.assertEqual(r.nome, "Correlação de Spearman (p exato)")
        self.assertLess(time.time() - t, 15)
        self.assertGreater(r.p, 0)
        self.assertLess(r.p, 0.001)

    def test_n10_usa_aproximacao_e_nome_simples(self):
        rng = np.random.default_rng(1)
        x, y = rng.normal(size=10), rng.normal(size=10)
        r = self.corr(x, y)
        self.assertEqual(r.nome, "Correlação de Spearman")
        self.assertAlmostEqual(r.p, float(stats.spearmanr(x, y).pvalue), places=12)
        self.assertIn("aproximação", r.observacoes)

    def test_pearson_nao_mudou(self):
        d = pd.DataFrame({"x": [1, 2, 3, 4.], "y": [2, 1, 4, 3.]})
        r = engine.correlacao(d, "x", "y", "pearson")
        self.assertAlmostEqual(r.p, float(stats.pearsonr(d.x, d.y).pvalue), places=12)
        self.assertEqual(r.nome, "Correlação de Pearson")

    def test_p_exato_diferente_da_aproximacao_em_n_pequeno(self):
        # com n=4 e rho=0,8 a aproximação t dá 0,20 e o exato é 0,3333: o app não pode usar a aproximação
        d = pd.DataFrame({"x": [1, 2, 3, 4.], "y": [1, 2, 4, 3.]})
        self.assertAlmostEqual(float(stats.spearmanr(d.x, d.y).pvalue), 0.2, places=6)
        self.assertAlmostEqual(engine.correlacao(d, "x", "y", "spearman").p, 1 / 3, places=12)


class TestesWilcoxonAvisoPMinimo(unittest.TestCase):
    def wil(self, dif):
        d = pd.DataFrame({"a": dif, "b": [0.0] * len(dif)})
        return engine.wilcoxon_pareado(d, "a", "b")

    def test_n4_nao_alcanca_5_por_cento(self):
        r = self.wil([2.4, 3.2, 7.6, 2.2])
        self.assertAlmostEqual(r.p, 0.125, places=12)
        self.assertIn("ATENÇÃO", r.observacoes)
        self.assertIn("0,1250", r.observacoes)

    def test_n6_alcanca_e_nao_avisa(self):
        r = self.wil([15.2, 741.3, 276.8, 521.4, 197.9, 134.4])
        self.assertAlmostEqual(r.p, 2 / 64, places=12)
        self.assertNotIn("ATENÇÃO", r.observacoes)

    def test_com_empates_nao_afirma_p_minimo(self):
        r = self.wil([1.0, 1.0, 2.0, 3.0])
        self.assertNotIn("ATENÇÃO", r.observacoes)


class TestesFriedman(unittest.TestCase):
    def fr(self, matriz, cols=None):
        m = np.asarray(matriz, float)
        cols = cols or [f"m{i}" for i in range(m.shape[1])]
        return engine.friedman(pd.DataFrame(m, columns=cols), cols)

    def test_estatistica_igual_ao_scipy_sem_e_com_empates(self):
        rng = np.random.default_rng(7)
        for m in (rng.normal(size=(6, 4)), rng.normal(size=(8, 3)),
                  np.array([[1, 2, 2, 5], [3, 3, 1, 4], [2, 2, 2, 7], [5, 1, 3, 3.]])):
            with self.subTest(forma=m.shape):
                r = self.fr(m)
                esp = stats.friedmanchisquare(*m.T)
                self.assertAlmostEqual(r.valor, float(esp.statistic), places=9)
                n, k = m.shape
                self.assertAlmostEqual(r.efeito_valor, r.valor / (n * (k - 1)), places=12)

    def test_p_exato_igual_a_forca_bruta(self):
        rng = np.random.default_rng(3)
        for forma in [(3, 3), (4, 3), (3, 4), (5, 3)]:
            m = rng.normal(size=forma)
            with self.subTest(forma=forma):
                self.assertAlmostEqual(self.fr(m).p, p_friedman_forca_bruta(m), places=12)

    def test_p_exato_igual_a_forca_bruta_com_empates(self):
        m = np.array([[1, 2, 2], [3, 3, 1], [2, 1, 3], [4, 4, 4.5]])
        self.assertAlmostEqual(self.fr(m).p, p_friedman_forca_bruta(m), places=12)

    def test_concordancia_perfeita_formula_fechada(self):
        # 4 participantes, mesma ordem de 3 medidas: chi2 = n(k-1) = 8; W = 1;
        # só 6 das 6^4 = 1296 configurações são tão extremas => p = 6/1296
        m = [[1, 2, 3]] * 4
        r = self.fr(np.array(m) + np.arange(4).reshape(-1, 1) * 10)
        self.assertAlmostEqual(r.valor, 8.0, places=12)
        self.assertAlmostEqual(r.efeito_valor, 1.0, places=12)
        self.assertAlmostEqual(r.p, 6 / 1296, places=12)

    def test_caso_6x4_do_estudo_de_lateralidade(self):
        # mesmos postos por participante da análise real (dados sintéticos com a mesma estrutura de postos)
        postos = np.array([[1, 3, 4, 2], [3, 2, 1, 4], [3, 4, 2, 1], [2, 1, 4, 3], [3, 2, 4, 1], [1, 3, 4, 2.]])
        r = self.fr(postos * 100.0)
        self.assertAlmostEqual(r.valor, 2.4, places=9)
        self.assertAlmostEqual(r.efeito_valor, 2.4 / 18, places=9)
        self.assertEqual(r.nome, "Teste de Friedman (p exato)")
        self.assertIn("0,4936", r.observacoes)          # aproximação χ² citada como comparação
        # p exato conferido por Monte Carlo independente (500 mil permutações, semente fixa)
        rng = np.random.default_rng(2024)
        n, k, passos = 6, 4, 25
        cont = tot = 0
        for _ in range(passos):
            perm = np.argsort(rng.random((20000, n, k)), axis=2).argsort(axis=2) + 1
            s = 12 / (n * k * (k + 1)) * np.sum(perm.sum(1) ** 2, axis=1) - 3 * n * (k + 1)
            cont += int(np.sum(s >= 2.4 - 1e-9)); tot += 20000
        self.assertAlmostEqual(r.p, cont / tot, delta=0.006)

    def test_tabela_de_detalhes(self):
        r = self.fr(np.array([[1, 2, 3], [2, 1, 3], [1, 3, 2], [1, 2, 3.]]), ["a", "b", "c"])
        t = r.detalhes
        self.assertEqual(list(t["Medida"]), ["a", "b", "c"])
        self.assertAlmostEqual(float(t["Ordem média"].sum()), 3 * 4 / 2, places=12)   # soma dos postos = k(k+1)/2
        self.assertEqual(set(t["N"]), {4})

    def test_caso_incompleto_sai_inteiro(self):
        m = pd.DataFrame({"a": [1, 2, 3, 4, 5.], "b": [2, 1, 4, 3, np.nan], "c": [3, 3.5, 1, 2, 9]})
        r = engine.friedman(m, ["a", "b", "c"])
        self.assertEqual(r.n, 4)

    def test_erros_esperados(self):
        d = pd.DataFrame({"a": [1, 2, 3.], "b": [2, 3, 1.], "c": [3, 1, 2.], "t": ["x", "y", "z"], "k": [1.0, 1.0, 1.0]})
        for cols in (["a", "b"], ["a", "a", "b"], ["a", "b", "inexistente"]):
            with self.subTest(cols=cols), self.assertRaises(ValueError):
                engine.friedman(d, cols)
        with self.assertRaises(ValueError):
            engine.friedman(d, ["a", "b", "t"])            # texto não numérico => NaN => sem casos completos
        with self.assertRaises(ValueError):
            engine.friedman(pd.DataFrame({"a": [1.], "b": [2.], "c": [3.]}), ["a", "b", "c"])  # n=1
        with self.assertRaises(ValueError):
            engine.friedman(pd.DataFrame({"a": [5, 5, 5.], "b": [5, 5, 5.], "c": [5, 5, 5.]}), ["a", "b", "c"])

    def test_amostra_grande_cai_na_aproximacao_qui_quadrado(self):
        rng = np.random.default_rng(9)
        m = rng.normal(size=(12, 6))
        t = time.time()
        r = self.fr(m)
        self.assertLess(time.time() - t, 6)                   # o abandono da enumeração é rápido
        self.assertEqual(r.nome, "Teste de Friedman (aproximação χ²)")
        self.assertAlmostEqual(r.p, float(stats.chi2.sf(r.valor, 5)), places=12)
        self.assertIn("aproximação χ²", r.observacoes)

    def test_casos_tipicos_continuam_exatos(self):
        rng = np.random.default_rng(11)
        for forma in [(6, 4), (15, 4), (30, 3), (8, 5)]:
            with self.subTest(forma=forma):
                self.assertEqual(self.fr(rng.normal(size=forma)).nome, "Teste de Friedman (p exato)")

    def test_desempenho_do_caso_6x4(self):
        postos = np.array([[1, 3, 4, 2], [3, 2, 1, 4], [3, 4, 2, 1], [2, 1, 4, 3], [3, 2, 4, 1], [1, 3, 4, 2.]])
        t = time.time()
        self.fr(postos)
        self.assertLess(time.time() - t, 5)

    def test_diferenca_clara_gera_p_pequeno(self):
        rng = np.random.default_rng(5)
        base = rng.normal(size=(8, 1))
        m = np.hstack([base, base + 5, base + 10]) + rng.normal(scale=.1, size=(8, 3))
        r = self.fr(m)
        self.assertLess(r.p, 0.001)
        self.assertGreater(r.efeito_valor, .9)


class TestesFriedmanNaInterface(unittest.TestCase):
    def test_catalogo(self):
        self.assertIn("Friedman", procedimentos.GUIA)
        self.assertIn("Friedman", sum(procedimentos.OBJETIVOS.values(), []))

    def test_registro_com_medidas_legiveis_e_magnitude(self):
        postos = np.array([[1, 3, 4, 2], [3, 2, 1, 4], [3, 4, 2, 1], [2, 1, 4, 3], [3, 2, 4, 1], [1, 3, 4, 2.]]) * 100
        df = pd.DataFrame(postos, columns=["TR 0°", "TR 90°", "TR 180°", "TR 270°"])
        reg = procedimentos.executar("Friedman", df, {"Medidas": list(df.columns)}, .05, "teste")
        self.assertEqual(reg["variaveis"], "Medidas: TR 0°, TR 90°, TR 180°, TR 270°")
        self.assertIn("W de Kendall = 0,133", reg["magnitude"])
        self.assertIn("pequeno", reg["magnitude"])           # 0,1 <= W < 0,3
        self.assertTrue(0 <= reg["p"] <= 1)
        self.assertEqual(reg["tabela"].shape[0], 4)

    def test_limiares_de_kendall(self):
        import interpretacao
        m = interpretacao.magnitude
        self.assertEqual(m("W de Kendall", .05), "desprezível")
        self.assertEqual(m("W de Kendall", .1), "pequeno")
        self.assertEqual(m("W de Kendall", .3), "médio")
        self.assertEqual(m("W de Kendall", .5), "grande")


class TestesFriedmanNoApp(unittest.TestCase):
    def test_executa_pela_interface_com_tres_medidas(self):
        import os
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        raiz = Path(__file__).resolve().parents[1]
        cwd = os.getcwd()
        os.chdir(raiz)
        try:
            at = AppTest.from_file(str(raiz / "app.py"), default_timeout=60).run()
            at.radio(key="objetivo").set_value("Comparar três ou mais medidas dos mesmos participantes").run()
            self.assertEqual([e.value for e in at.exception], [])
            btn = next(b for b in at.button if b.label == "Executar análise")
            btn.click().run()
            self.assertEqual([e.value for e in at.exception], [])
            self.assertEqual([e.value for e in at.error], [])
            self.assertTrue(at.session_state["historico"][0]["teste"].startswith("Teste de Friedman"))
            # menos de 3 medidas: botão desabilitado e aviso
            at.multiselect(key="Friedman_medidas").set_value(["idade", "tempo_reacao_ms"]).run()
            self.assertTrue(next(b for b in at.button if b.label == "Executar análise").disabled)
            self.assertTrue(any("pelo menos 3" in w.value for w in at.warning))
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()


class TestesRedacaoDoP(unittest.TestCase):
    def test_p_muito_pequeno_nao_gera_igual_menor_que(self):
        import interpretacao
        txt, _ = interpretacao.conclusao("inferencial", 0.00001, .05)
        self.assertIn("p < 0,0001 < α (0,05)", txt)
        self.assertNotIn("= <", txt)
        txt, _ = interpretacao.conclusao("inferencial", 0.0321, .05)
        self.assertIn("p = 0,0321 < α (0,05)", txt)
