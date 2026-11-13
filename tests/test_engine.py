import unittest
import numpy as np
import pandas as pd
from scipy import stats
import engine


class TestesEstatisticos(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "x":[1., 2, 3, 4, 5, 6, 7, 8],
            "y":[2., 4, 6, 8, 10, 12, 14, 16],
            "g":["A","A","A","A","B","B","B","B"],
            "cat1":["a","a","b","b","a","a","b","b"],
            "cat2":["q","r","q","r","q","r","q","r"],
        })

    def test_descritiva(self):
        r=engine.descritiva(self.df,["x"])
        self.assertEqual(int(r.iloc[0]["N válido"]),8)
        self.assertAlmostEqual(float(r.iloc[0]["Média"]),4.5)

    def test_pearson(self):
        r=engine.correlacao(self.df,"x","y","pearson")
        self.assertAlmostEqual(r.valor,1.0)
        self.assertEqual(r.n,8)

    def test_spearman(self):
        r=engine.correlacao(self.df,"x","y","spearman")
        self.assertAlmostEqual(r.valor,1.0)

    def test_welch(self):
        r=engine.t_independente(self.df,"x","g","A","B")
        expected=stats.ttest_ind(self.df.x[:4],self.df.x[4:],equal_var=False)
        self.assertAlmostEqual(r.valor,float(expected.statistic))
        self.assertAlmostEqual(r.p,float(expected.pvalue))

    def test_mannwhitney(self):
        r=engine.mann_whitney(self.df,"x","g","A","B")
        expected=stats.mannwhitneyu(self.df.x[:4],self.df.x[4:])
        self.assertAlmostEqual(r.p,float(expected.pvalue))

    def test_anova(self):
        r=engine.anova(self.df,"x","g")
        self.assertAlmostEqual(r.valor,float(stats.f_oneway(self.df.x[:4],self.df.x[4:]).statistic))
        self.assertAlmostEqual(r.efeito_valor, 32/42) # SSbetween 32, SStotal 42

    def test_fisher(self):
        d=pd.DataFrame({"a":["sim"]*4+["nao"]*4,"b":["x"]*4+["y"]*4})
        r=engine.qui_quadrado(d,"a","b")
        self.assertEqual(r.nome,"Exato de Fisher (2×2)")
        self.assertAlmostEqual(r.p,1/35)

    def test_t_pareado(self):
        d=self.df.copy(); d["y"]=[1,2,4,4,5,7,7,9]
        r=engine.t_pareado(d,"x","y")
        self.assertAlmostEqual(r.p,float(stats.ttest_rel(d.x,d.y).pvalue))

    def test_shapiro(self):
        r=engine.normalidade(self.df,"x")
        self.assertGreaterEqual(r.p,0)
        self.assertLessEqual(r.p,1)

    def test_missing_pairwise(self):
        d=self.df.copy();d.loc[0,"x"]=np.nan
        self.assertEqual(engine.correlacao(d,"x","y").n,7)

    def test_constant_error(self):
        d=self.df.copy();d["x"]=1.
        with self.assertRaises(ValueError):engine.correlacao(d,"x","y")


if __name__=="__main__":
    unittest.main()

class TestesDeImportacao(unittest.TestCase):
    def test_csv_decimal_virgula(self):
        import io
        from data_utils import ler_arquivo
        class Uploaded:
            name = "exemplo.csv"
            def getvalue(self): return 'nome;valor\nPessoa A;1,25\nPessoa B;3,50\n'.encode('utf-8')
        d=ler_arquivo(Uploaded(), sep=';', decimal=',')
        self.assertAlmostEqual(float(d.loc[0, "valor"]), 1.25)

    def test_estesiometria_nao_altera_n(self):
        d=pd.DataFrame({"id":[1,2,3],"t":[500,700,900]})
        self.assertEqual(engine.descritiva(d,["t"]).loc[0,"N válido"],3)
