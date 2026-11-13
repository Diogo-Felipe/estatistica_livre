"""Testes de regressão com resultados calculados por fórmulas independentes.

Os valores de referência não são obtidos chamando a mesma rotina testada.
Os dados de teste são inteiramente sintéticos.
"""
import math
import unittest
from pathlib import Path

import pandas as pd
from scipy import stats
import engine
from data_utils import ler_arquivo


class CSVLocal:
    def __init__(self, path):
        self.path=Path(path)
        self.name=self.path.name
    def getvalue(self):
        return self.path.read_bytes()


BASE = Path(__file__).resolve().parents[1] / 'validacao_estatistica_ficticia.csv'


class TestesDeReferencia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df=ler_arquivo(CSVLocal(BASE), sep=';', decimal=',')

    def test_formato_csv_e_ausentes(self):
        d=self.df
        self.assertEqual(d.shape, (60, 9))
        self.assertTrue(pd.api.types.is_numeric_dtype(d['pontuacao']))
        self.assertEqual(int(d['antes'].notna().sum()), 8)
        self.assertEqual(int(d['grupo_fisher'].notna().sum()), 12)

    def test_anova_referencia_analitica(self):
        # Grupos com media 10.5,13.5,16.5, N=20 em cada.
        # SSentre = 20*(9+0+9) =360; SSdentro =3*165=495.
        # F = (360/2)/(495/57) = 20.72727; eta2=360/855.
        r=engine.anova(self.df, 'pontuacao', 'grupo_anova')
        f_formula=(360.0/2)/(495.0/57)
        self.assertEqual(r.nome, 'ANOVA de uma via')
        self.assertEqual(r.n,60)
        self.assertAlmostEqual(r.valor,f_formula, places=12)
        self.assertAlmostEqual(r.efeito_valor,360/855,places=12)
        self.assertAlmostEqual(r.p,float(stats.f.sf(f_formula,2,57)),places=13)

    def test_t_pareado_referencia_analitica(self):
        # antes - depois = -1..-8, N=8, média -4.5, DP amostral sqrt(6).
        # t = -4.5/(sqrt(6)/sqrt(8)), gl=7, dz= -4.5/sqrt(6).
        r=engine.t_pareado(self.df,'antes','depois')
        t_formula=-4.5/math.sqrt(6/8)
        self.assertEqual(r.n,8)
        self.assertAlmostEqual(r.valor,t_formula, places=12)
        self.assertAlmostEqual(r.efeito_valor,-4.5/math.sqrt(6), places=12)
        self.assertAlmostEqual(r.p,2*stats.t.sf(abs(t_formula),7),places=12)

    def test_wilcoxon_referencia_exata(self):
        # Oito diferenças de mesmo sinal, postos 1..8 => W=0.
        # Dos 2**8 sinais possíveis, apenas 2 são tão extremos => p=2/256.
        r=engine.wilcoxon_pareado(self.df,'antes','depois')
        self.assertEqual(r.n,8)
        self.assertEqual(r.valor,0)
        self.assertAlmostEqual(r.p, 2/(2**8),places=12)

    def test_quiquadrado_referencia_contingencia(self):
        # Tabela 3x2: [12,8], [8,12], [4,16].
        # Esperado em cada linha: [8,12]; χ²= 20/3; gl=2.
        r=engine.qui_quadrado(self.df,'grupo_qui','resposta_qui')
        self.assertEqual(r.nome,'Qui-quadrado de Pearson')
        self.assertEqual(r.n,60)
        self.assertAlmostEqual(r.valor,20/3,places=12)
        self.assertAlmostEqual(r.p,math.exp(-(20/3)/2),places=12)  # gl=2, p=exp(-chi2/2)
        self.assertAlmostEqual(r.efeito_valor,1/3,places=12)
        self.assertIn('0/6',r.observacoes)

    def test_fisher_referencia_exata(self):
        # Tabela 2x2: [[5,1],[1,5]], marginais 6,6 e 6,6.
        # p bilateral = 2*(C(6,0)*C(6,6)+C(6,1)*C(6,5))/C(12,6)=74/924.
        r=engine.qui_quadrado(self.df,'grupo_fisher','resposta_fisher')
        self.assertEqual(r.nome,'Exato de Fisher (2×2)')
        self.assertEqual(r.n,12)
        self.assertAlmostEqual(r.valor,25,places=12)
        p_formula=2*(math.comb(6,0)*math.comb(6,6)+math.comb(6,1)*math.comb(6,5))/math.comb(12,6)
        self.assertAlmostEqual(r.p,p_formula,places=12)

    def test_dois_grupos_selecionados_consistem_em_observacoes_independentes(self):
        r=engine.mann_whitney(self.df,'pontuacao','grupo_anova','A','B')
        self.assertEqual(r.n,40)
        self.assertGreaterEqual(r.p,0)
        self.assertLessEqual(r.p,1)

    def test_pareamento_descarta_apenas_pares_incompletos(self):
        d=self.df.copy()
        d.loc[0,'depois']=float('nan')
        self.assertEqual(engine.t_pareado(d,'antes','depois').n,7)
        self.assertEqual(engine.wilcoxon_pareado(d,'antes','depois').n,7)

    def test_erros_esperados(self):
        with self.assertRaises(ValueError):
            engine.t_pareado(self.df,'antes','antes')
        with self.assertRaises(ValueError):
            engine.qui_quadrado(self.df,'grupo_anova','grupo_anova')


if __name__=='__main__':
    unittest.main()
