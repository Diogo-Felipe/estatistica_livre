import io
import unittest
import pandas as pd
import numpy as np

from schema import criar_dicionario, tabela_dicionario, aplicar_dicionario, preparar_analise, estatisticas_variaveis, rotulo_valor
from reports import registrar_resultado, gerar_html, gerar_excel, tabela_resumo
from project_io import exportar_projeto, importar_projeto


class TestesVersao02(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "idade": [30, 99, 50],
            "escore": ["1,5", "2,3", None],
            "grupo": ["controle", "tratamento", "controle"],
        })
        self.schema = criar_dicionario(self.df)

    def test_dic_inicial(self):
        self.assertEqual(self.schema['idade']['tipo'], 'Numérica')
        self.assertEqual(self.schema['grupo']['medida'], 'Nominal')

    def test_editar_nomes_e_tipo(self):
        ed = tabela_dicionario(self.df, self.schema)
        ed.loc[0, 'Nome'] = 'anos'
        ed.loc[1, 'Tipo'] = 'Numérica'
        ed.loc[1, 'Medida'] = 'Escala'
        d, dic = aplicar_dicionario(self.df, ed)
        self.assertEqual(list(d.columns), ['anos','escore','grupo'])
        self.assertAlmostEqual(d['escore'].iloc[1], 2.3)
        self.assertIn('anos', dic)
        self.assertNotIn('idade', dic)

    def test_nome_duplicado_impedido(self):
        ed = tabela_dicionario(self.df, self.schema)
        ed.loc[0, 'Nome'] = 'grupo'
        with self.assertRaisesRegex(ValueError, 'únicos'):
            aplicar_dicionario(self.df, ed)

    def test_invalido_numerico_impedido(self):
        ed = tabela_dicionario(self.df, self.schema)
        ed.loc[2, 'Tipo'] = 'Numérica'
        with self.assertRaises(ValueError):
            aplicar_dicionario(self.df, ed)

    def test_rotulos_formatados(self):
        ed = tabela_dicionario(self.df, self.schema)
        ed.loc[0,'Rótulos de valores'] = '1 ='
        with self.assertRaisesRegex(ValueError, 'Rótulos de valores'):
            aplicar_dicionario(self.df, ed)

    def test_ausentes_nao_alteram_brutos(self):
        self.schema['idade']['ausentes'] = '99'
        masked = preparar_analise(self.df, self.schema)
        self.assertTrue(pd.isna(masked['idade'].iloc[1]))
        self.assertEqual(int(self.df['idade'].iloc[1]), 99)
        table = estatisticas_variaveis(self.df,self.schema)
        self.assertEqual(int(table.loc[0,'Ausentes']), 1)

    def test_codigos_textuais(self):
        self.schema['grupo']['ausentes'] = 'tratamento'
        masked = preparar_analise(self.df,self.schema)
        self.assertTrue(pd.isna(masked['grupo'].iloc[1]))
        self.assertEqual(self.df['grupo'].iloc[1],'tratamento')

    def test_gerar_html_escapa_entradas(self):
        tab = pd.DataFrame({'valor': ['<script>alert(1)</script>']})
        record = registrar_resultado('Teste <b>', 'x & y', tab, 3, .05, 't = 1', .045,
                                     nota='<svg onload=alert(1)>', fonte='test & source')
        html = gerar_html([record], 'Pesquisa <img>', 'Fonte & local').decode('utf-8')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;img&gt;', html)
        self.assertIn('x &amp; y', html)
        self.assertIn('p:</b> 0,0450', html)
        self.assertEqual(tabela_resumo([record]).shape, (1,8))

    def test_excel_e_resumo(self):
        record = registrar_resultado('Descritiva', 'idade', pd.DataFrame({'N': [3], 'Média': [50.]}),
                                     3, .05, fonte='Teste')
        raw = gerar_excel([record], estatisticas_variaveis(self.df,self.schema))
        self.assertTrue(raw[:2] == b'PK')
        wb = pd.ExcelFile(io.BytesIO(raw))
        self.assertEqual(wb.sheet_names, ['Resumo', 'Variáveis', 'Teste_01'])
        resumo = pd.read_excel(io.BytesIO(raw), sheet_name='Resumo')
        self.assertEqual(resumo.iloc[0]['Análise'], 'Descritiva')

    def test_projeto_roundtrip(self):
        raw = exportar_projeto(self.df, self.schema,'Estudo demo')
        self.assertTrue(raw.startswith(b'PK'))
        result, dic, nome = importar_projeto(raw)
        pd.testing.assert_frame_equal(result.fillna(""), self.df.fillna(""), check_dtype=False)
        self.assertEqual(dic, self.schema)
        self.assertEqual(nome,'Estudo demo')

    def test_rotulo_numerico_inteiro(self):
        self.assertEqual(rotulo_valor(1.0, {"1":"Sim"}), "Sim")

    def test_zip_aleatorio_rejeitado(self):
        with self.assertRaises(ValueError):
            importar_projeto(b'not a zip')

    def test_sem_analise_nao_gera_relatorio(self):
        with self.assertRaises(ValueError):
            gerar_html([], 'titulo', 'fonte')

if __name__ == '__main__':
    unittest.main()
