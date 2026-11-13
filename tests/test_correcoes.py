"""Regressões de bugs encontrados na revisão + referências independentes (sem usar scipy como oráculo)."""
import itertools
import math
import unittest

import numpy as np
import pandas as pd

import engine
from schema import (criar_dicionario, tabela_dicionario, aplicar_dicionario,
                    preparar_analise)


class TestesDicionario(unittest.TestCase):
    def test_aplicar_dicionario_com_linhas_diferentes_de_colunas(self):
        # Bug: comparava nº de variáveis com nº de CASOS; só funcionava se fossem iguais.
        df = pd.DataFrame({"a": range(10), "b": list("abcdefghij")})  # 10 casos, 2 variáveis
        ed = tabela_dicionario(df, criar_dicionario(df))
        ed.loc[0, "Nome"] = "idade"
        ed.loc[0, "Rótulo"] = "Idade em anos"
        d, dic = aplicar_dicionario(df, ed)
        self.assertEqual(list(d.columns), ["idade", "b"])
        self.assertEqual(dic["idade"]["rotulo"], "Idade em anos")
        self.assertEqual(len(d), 10)

    def test_dicionario_com_numero_errado_de_linhas_e_rejeitado(self):
        df = pd.DataFrame({"a": range(10), "b": list("abcdefghij")})
        ed = tabela_dicionario(df, criar_dicionario(df)).iloc[:1]
        with self.assertRaises(ValueError):
            aplicar_dicionario(df, ed)

    def test_codigo_ausente_em_coluna_float_convertida_para_texto(self):
        # Bug: "99.0" não casava com o código "99" e o valor continuava na análise.
        df = pd.DataFrame({"x": [1.0, 99.0, 3.0]})
        ed = tabela_dicionario(df, criar_dicionario(df))
        ed.loc[0, "Tipo"], ed.loc[0, "Medida"], ed.loc[0, "Ausentes definidos"] = "Texto", "Nominal", "99"
        d, dic = aplicar_dicionario(df, ed)
        out = preparar_analise(d, dic)
        self.assertEqual(int(out["x"].isna().sum()), 1)
        self.assertTrue(pd.isna(out["x"].iloc[1]))

    def test_codigo_ausente_inteiro_vira_nan_e_mantem_coluna_numerica(self):
        df = pd.DataFrame({"i": [30, 99, 50]})
        s = criar_dicionario(df); s["i"]["ausentes"] = "99"
        out = preparar_analise(df, s)
        self.assertTrue(pd.api.types.is_numeric_dtype(out["i"]))
        self.assertEqual(engine.descritiva(out, ["i"]).loc[0, "N válido"], 2)
        self.assertAlmostEqual(out["i"].mean(), 40.0)
        self.assertEqual(int(df["i"].iloc[1]), 99)  # dado bruto intacto

    def test_codigo_com_virgula_decimal(self):
        df = pd.DataFrame({"f": [1.5, 99.5, 2.0]})
        s = criar_dicionario(df); s["f"]["ausentes"] = "99,5"
        self.assertTrue(pd.isna(preparar_analise(df, s)["f"].iloc[1]))


class TestesMotor(unittest.TestCase):
    def test_wilcoxon_n_exclui_diferencas_zero(self):
        # Bug: N mostrado incluía diferenças zero que o teste descarta.
        d = pd.DataFrame({"a": [1, 2, 3, 4, 5, 6, 7, 8.], "b": [1, 2, 3, 5, 7, 9, 4, 2.]})
        r = engine.wilcoxon_pareado(d, "a", "b")
        self.assertEqual(r.n, 5)
        self.assertIn("zero descartadas: 3", r.observacoes)
        self.assertIn("N analisado", r.observacoes)

    def test_qui_quadrado_rejeita_variavel_continua(self):
        rng = np.random.default_rng(0)
        d = pd.DataFrame({"a": rng.random(200), "b": rng.random(200)})
        with self.assertRaisesRegex(ValueError, "categorias"):
            engine.qui_quadrado(d, "a", "b")

    # ---- referências independentes (fórmulas / enumeração exata) ----
    def test_welch_formula_manual(self):
        a = [5.1, 4.9, 6.2, 5.8, 6.0]; b = [4.2, 4.8, 5.0, 4.4, 4.1, 4.9]
        d = pd.DataFrame({"v": a + b, "g": ["A"] * 5 + ["B"] * 6})
        r = engine.t_independente(d, "v", "g", "A", "B")
        ma, mb = sum(a) / 5, sum(b) / 6
        va = sum((x - ma) ** 2 for x in a) / 4; vb = sum((x - mb) ** 2 for x in b) / 5
        t = (ma - mb) / math.sqrt(va / 5 + vb / 6)
        self.assertAlmostEqual(r.valor, t, places=10)
        sp = math.sqrt((4 * va + 5 * vb) / 9)
        self.assertAlmostEqual(r.efeito_valor, (ma - mb) / sp, places=10)

    def test_mann_whitney_u_por_contagem_direta(self):
        a = [1.1, 2.5, 3.7, 4.2]; b = [0.5, 2.0, 2.9, 5.5, 6.1]
        d = pd.DataFrame({"v": a + b, "g": ["A"] * 4 + ["B"] * 5})
        r = engine.mann_whitney(d, "v", "g", "A", "B")
        u = sum(1.0 if x > y else 0.5 if x == y else 0.0 for x in a for y in b)
        self.assertEqual(r.valor, u)
        # p exato por permutação de rótulos (sem empates)
        todos = a + b
        obs = abs(u - 4 * 5 / 2)
        cont = tot = 0
        for idx in itertools.combinations(range(9), 4):
            ga = [todos[i] for i in idx]; gb = [todos[i] for i in range(9) if i not in idx]
            uu = sum(1.0 if x > y else 0.0 for x in ga for y in gb)
            tot += 1; cont += abs(uu - 10) >= obs - 1e-12
        self.assertAlmostEqual(r.p, cont / tot, places=10)
        self.assertAlmostEqual(r.efeito_valor, 2 * u / 20 - 1, places=12)

    def test_wilcoxon_p_exato_por_enumeracao_de_sinais(self):
        dif = [1.5, -0.5, 2.0, 3.0, -1.0, 2.5, 4.0]
        d = pd.DataFrame({"a": dif, "b": [0.0] * 7})
        r = engine.wilcoxon_pareado(d, "a", "b")
        ordem = sorted(range(7), key=lambda i: abs(dif[i]))
        rank = {i: k + 1 for k, i in enumerate(ordem)}
        wmais = sum(rank[i] for i in range(7) if dif[i] > 0)
        w = min(wmais, 28 - wmais)
        cont = 0
        for sinais in itertools.product([0, 1], repeat=7):
            s = sum(k + 1 for k, f in enumerate(sinais) if f)
            cont += min(s, 28 - s) <= w
        self.assertEqual(r.valor, w)
        self.assertAlmostEqual(r.p, cont / 2 ** 7, places=12)

    def test_pearson_e_spearman_formula_manual(self):
        x = [1, 2, 3, 4, 5, 6.]; y = [2.1, 1.9, 4.2, 3.8, 6.5, 5.0]
        d = pd.DataFrame({"x": x, "y": y})
        mx, my = np.mean(x), np.mean(y)
        r_man = sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(
            sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
        self.assertAlmostEqual(engine.correlacao(d, "x", "y", "pearson").valor, r_man, places=12)
        rx = pd.Series(x).rank().to_numpy(); ry = pd.Series(y).rank().to_numpy()
        n = 6; rho = 1 - 6 * sum((rx - ry) ** 2) / (n * (n * n - 1))  # sem empates
        self.assertAlmostEqual(engine.correlacao(d, "x", "y", "spearman").valor, rho, places=12)

    def test_descritiva_quartis_e_dp_amostral(self):
        d = pd.DataFrame({"x": [2., 4, 4, 4, 5, 5, 7, 9]})
        r = engine.descritiva(d, ["x"]).iloc[0]
        self.assertAlmostEqual(r["Média"], 5.0)
        self.assertAlmostEqual(r["DP"], math.sqrt(32 / 7), places=12)  # ddof=1
        self.assertEqual(r["Mediana"], 4.5)


if __name__ == "__main__":
    unittest.main()
