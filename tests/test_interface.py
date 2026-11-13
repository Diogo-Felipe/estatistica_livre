"""Testes da camada de interface: lógica pura (interpretação/procedimentos) e Streamlit AppTest."""
import os
import unittest
from pathlib import Path

import pandas as pd

import interpretacao
import procedimentos
import reports
import schema as variaveis

RAIZ = Path(__file__).resolve().parents[1]


class TestesInterpretacao(unittest.TestCase):
    def test_formatar_p(self):
        self.assertEqual(interpretacao.formatar_p(0.03214), "0,0321")
        self.assertEqual(interpretacao.formatar_p(0.00001), "< 0,0001")
        self.assertEqual(interpretacao.formatar_p(None), "—")
        self.assertEqual(interpretacao.formatar_p(float("nan")), "—")

    def test_limiares_cohen(self):
        m = interpretacao.magnitude
        self.assertEqual(m("d de Cohen", .1), "insignificante")
        self.assertEqual(m("d de Cohen", -.3), "pequeno")      # sinal ignorado
        self.assertEqual(m("d de Cohen", .5), "médio")         # limite inferior inclusivo
        self.assertEqual(m("d de Cohen (dz)", 1.2), "grande")
        self.assertEqual(m("η²", .05), "pequeno")
        self.assertEqual(m("η²", .14), "grande")
        self.assertEqual(m("Correlação bisserial de postos", .35), "médio")
        self.assertEqual(m("nome desconhecido", .9), "")
        self.assertEqual(m("d de Cohen", float("nan")), "")

    def test_v_de_cramer_depende_dos_graus_de_liberdade(self):
        # 2x2 (gl*=1): 0.3 = médio; 3x3 (gl*=2): limiar médio = 0.3/sqrt(2)
        self.assertEqual(interpretacao.magnitude("V de Cramér", .3, (2, 2)), "médio")
        self.assertEqual(interpretacao.magnitude("V de Cramér", .22, (3, 3)), "médio")
        self.assertEqual(interpretacao.magnitude("V de Cramér", .22, (2, 2)), "pequeno")

    def test_conclusao_nunca_afirma_que_nao_ha_efeito(self):
        txt, tom = interpretacao.conclusao("inferencial", .30, .05)
        self.assertEqual(tom, "neutro")
        self.assertIn("Isso não demonstra", txt)
        txt, tom = interpretacao.conclusao("inferencial", .01, .05)
        self.assertEqual(tom, "sucesso")
        self.assertIn("p = 0,0100 < α (0,05)", txt)

    def test_conclusao_normalidade(self):
        txt, tom = interpretacao.conclusao("normalidade", .20, .05)
        self.assertIn("não comprova", txt)
        txt, tom = interpretacao.conclusao("normalidade", .01, .05)
        self.assertEqual(tom, "aviso")

    def test_p_igual_a_alpha_nao_e_significativo(self):
        txt, tom = interpretacao.conclusao("inferencial", .05, .05)
        self.assertEqual(tom, "neutro")
        self.assertIn("≥", txt)


class TestesProcedimentos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ex = pd.read_csv(RAIZ / "exemplo_ficticio.csv")
        cls.val = pd.read_csv(RAIZ / "validacao_estatistica_ficticia.csv", sep=";", decimal=",")

    def _executar(self, metodo, df, params):
        return procedimentos.executar(metodo, df, params, .05, "teste")

    def test_todo_procedimento_do_catalogo_tem_guia_e_objetivo(self):
        todos = [m for lista in procedimentos.OBJETIVOS.values() for m in lista]
        self.assertEqual(sorted(todos), sorted(procedimentos.GUIA))

    def test_executar_todos_os_procedimentos(self):
        ex, val = self.ex, self.val
        casos = [
            ("Descritiva", ex, {"Variáveis": ["idade", "tempo_reacao_ms"]}),
            ("Shapiro-Wilk", ex, {"Variável": "idade"}),
            ("Correlação (Pearson / Spearman)", ex, {"X": "idade", "Y": "tempo_reacao_ms", "Método": "Pearson"}),
            ("Correlação (Pearson / Spearman)", ex, {"X": "idade", "Y": "tempo_reacao_ms", "Método": "Spearman"}),
            ("t independente (Welch)", ex, {"Variável": "idade", "Grupo": "grupo",
                                           "Grupo 1": "Lado direito", "Grupo 2": "Lado esquerdo"}),
            ("Mann–Whitney U", ex, {"Variável": "idade", "Grupo": "grupo",
                                   "Grupo 1": "Lado direito", "Grupo 2": "Lado esquerdo"}),
            ("t pareado", ex, {"Medida 1": "copm_desempenho", "Medida 2": "copm_satisfacao"}),
            ("Wilcoxon pareado", ex, {"Medida 1": "copm_desempenho", "Medida 2": "copm_satisfacao"}),
            ("ANOVA de uma via", val, {"Variável": "pontuacao", "Grupo": "grupo_anova"}),
            ("Qui-quadrado / Fisher", val, {"Categoria 1": "grupo_qui", "Categoria 2": "resposta_qui"}),
        ]
        for metodo, df, params in casos:
            with self.subTest(metodo=metodo, params=params):
                reg = self._executar(metodo, df, params)
                self.assertTrue(reg["teste"])
                if metodo != "Descritiva":
                    self.assertTrue(0 <= reg["p"] <= 1)
                    self.assertTrue(reg["conclusao"])

    def test_magnitude_registrada_para_anova_de_referencia(self):
        reg = self._executar("ANOVA de uma via", self.val, {"Variável": "pontuacao", "Grupo": "grupo_anova"})
        self.assertIn("η² = 0,421", reg["magnitude"])   # 360/855
        self.assertIn("grande", reg["magnitude"])

    def test_cramer_do_qui_quadrado_de_referencia(self):
        reg = self._executar("Qui-quadrado / Fisher", self.val,
                             {"Categoria 1": "grupo_qui", "Categoria 2": "resposta_qui"})
        self.assertIn("V de Cramér = 0,333", reg["magnitude"])  # tabela 3x2 => gl*=1 => 0,3 = médio
        self.assertIn("médio", reg["magnitude"])

    def test_erro_do_engine_chega_a_interface_como_valueerror(self):
        with self.assertRaises(ValueError):
            self._executar("t pareado", self.ex, {"Medida 1": "idade", "Medida 2": "idade"})

    def test_procedimento_desconhecido(self):
        with self.assertRaises(ValueError):
            self._executar("Inventado", self.ex, {})

    def test_html_inclui_interpretacao_escapada(self):
        reg = self._executar("Shapiro-Wilk", self.ex, {"Variável": "idade"})
        reg["conclusao"] = "<b>x</b>"
        html = reports.gerar_html([reg], "t", "f").decode()
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
        self.assertNotIn("<b>x</b>", html)


class TestesTema(unittest.TestCase):
    def test_config_define_temas_claro_e_escuro_sem_tema_fixo(self):
        import tomllib
        cfg = tomllib.loads((RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
        tema = cfg["theme"]
        self.assertIn("light", tema)
        self.assertIn("dark", tema)
        # sem chaves de cor na raiz de [theme]: um tema fixo impediria o modo escuro automático
        self.assertFalse({"backgroundColor", "textColor", "base"} & set(tema))
        self.assertNotEqual(tema["light"]["backgroundColor"], tema["dark"]["backgroundColor"])

    def test_css_nao_usa_cores_claras_fixas_nos_componentes(self):
        import re
        import estilo
        # fundo/texto de componentes devem vir de tokens; #fff só é aceito no cabeçalho, no
        # painel do gráfico e na definição dos tokens claros.
        fora_dos_tokens = re.sub(r"\.stApp\{.*?\}\n", "", estilo.CSS, flags=re.S)
        fora_dos_tokens = re.sub(r"@supports.*?\n\}\n", "", fora_dos_tokens, flags=re.S)
        for linha in fora_dos_tokens.splitlines():
            if "background:#fff" in linha.replace(" ", "") and "stImage" not in linha:
                self.fail(f"fundo claro fixo: {linha.strip()}")
        self.assertIn("light-dark(", estilo.CSS)

    def test_botao_primario_desabilitado_nao_recebe_cor_forcada(self):
        # Regressão: texto branco forçado deixava o botão desabilitado (fundo claro) ilegível.
        import re
        import estilo
        regras = [l for l in estilo.CSS.splitlines() if "stBaseButton-primary" in l and "!important" in l]
        self.assertTrue(regras)
        for regra in regras:
            for seletor in regra.split("{")[0].split(","):
                self.assertIn(":not(:disabled)", seletor)

    def test_tokens_claro_e_escuro_tem_o_mesmo_conjunto(self):
        import re
        import estilo
        claros = set(re.findall(r"(--el-[a-z-]+):", estilo.CSS.split("@supports")[0]))
        escuros = set(re.findall(r"(--el-[a-z-]+):", estilo.CSS.split("@supports")[1]))
        self.assertEqual(claros - {"--el-primary-dark"} - escuros, set())


class TestesAppStreamlit(unittest.TestCase):
    """Executa o app real sem navegador (streamlit.testing)."""

    @classmethod
    def setUpClass(cls):
        try:
            from streamlit.testing.v1 import AppTest
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"streamlit indisponível: {exc}")
        cls.AppTest = AppTest

    def setUp(self):
        self._cwd = os.getcwd()
        os.chdir(RAIZ)
        self.at = self.AppTest.from_file(str(RAIZ / "app.py"), default_timeout=60).run()

    def tearDown(self):
        os.chdir(self._cwd)

    def _sem_erros(self, at=None):
        at = at or self.at
        self.assertEqual([e.value for e in at.exception], [])
        self.assertEqual([e.value for e in at.error], [])

    def _botao(self, rotulo):
        return next(b for b in self.at.button if b.label == rotulo)

    def test_abre_sem_erros_com_cinco_etapas(self):
        self._sem_erros()
        self.assertEqual([t.label for t in self.at.tabs],
                         ["1 · Dados", "2 · Variáveis", "3 · Análises", "4 · Gráficos", "5 · Relatório"])

    def test_cada_objetivo_renderiza_sem_erros(self):
        for objetivo in procedimentos.OBJETIVOS:
            with self.subTest(objetivo=objetivo):
                self.at.radio(key="objetivo").set_value(objetivo).run()
                self._sem_erros()

    def test_executar_analise_de_ponta_a_ponta(self):
        self.at.radio(key="objetivo").set_value("Comparar dois grupos independentes").run()
        self.at.radio(key="proc_Comparar dois grupos independentes").set_value("Mann–Whitney U").run()
        self._botao("Executar análise").click().run()
        self._sem_erros()
        self.assertEqual(len(self.at.session_state["historico"]), 1)
        self.assertEqual(self.at.session_state["historico"][0]["teste"], "Mann–Whitney U")
        self.assertTrue(any("Análise concluída" in s.value for s in self.at.success))

    def _html(self):
        return " ".join(m.value for m in self.at.markdown)

    def test_cabecalho_compacto_mostra_contadores_com_plural_correto(self):
        html = self._html()
        self.assertIn("Estatística Livre", html)
        self.assertIn("<b>18</b> casos", html)
        self.assertIn("<b>8</b> variáveis", html)
        self.assertIn("<b>0</b> análises", html)

    def test_contador_de_analises_atualiza_na_mesma_execucao(self):
        self.assertIn("<b>0</b> análises", self._html())
        self._botao("Executar análise").click().run()
        html = self._html()
        self.assertIn("<b>1</b> análise<", html)      # singular
        self.assertNotIn("<b>1</b> análises", html)
        self._botao("Executar análise").click().run()
        self.assertIn("<b>2</b> análises", self._html())

    def test_barra_lateral_lista_analises_e_permite_salvar_projeto(self):
        labels = [d.label for d in self.at.get("download_button")]
        self.assertTrue(any("Salvar projeto" in l for l in labels))
        self.assertTrue(any("Nenhuma ainda" in c.value for c in self.at.sidebar.caption))
        self._botao("Executar análise").click().run()
        lateral = " ".join(m.value for m in self.at.sidebar.markdown)
        self.assertIn("1. Descritiva", lateral)
        self.assertIn("N = 18", lateral)
        self.assertNotIn("p = —", lateral)             # descritiva não tem p-valor

    def test_limpar_analises_pela_barra_lateral(self):
        self._botao("Executar análise").click().run()
        self.at.sidebar.button(key="limpar_lateral").click().run()
        self.assertEqual(self.at.session_state["historico"], [])
        self.assertIn("<b>0</b> análises", self._html())

    def test_projeto_so_aparece_na_barra_lateral(self):
        salvar = [d for d in self.at.get("download_button") if "Salvar projeto" in d.label]
        self.assertEqual(len(salvar), 1)

    def test_erro_de_analise_e_mostrado_sem_derrubar_o_app(self):
        # Variável constante: o engine recusa o Shapiro-Wilk; o app deve mostrar a mensagem.
        df = self.at.session_state["df"].copy()
        df["constante"] = 5.0
        self.at.session_state["df"] = df
        self.at.session_state["schema"] = variaveis.criar_dicionario(df)
        self.at.radio(key="objetivo").set_value("Descrever e explorar os dados").run()
        self.at.radio(key="proc_Descrever e explorar os dados").set_value("Shapiro-Wilk").run()
        self.at.selectbox(key="Shapiro-Wilk_v").set_value("constante").run()
        self._botao("Executar análise").click().run()
        self.assertEqual([e.value for e in self.at.exception], [])
        self.assertTrue(any("constante" in e.value for e in self.at.error))
        self.assertEqual(len(self.at.session_state["historico"]), 0)

    def test_trocar_base_apaga_historico(self):
        self._botao("Executar análise").click().run()
        self.assertEqual(len(self.at.session_state["historico"]), 1)
        self._botao("Base de validação").click().run()
        self._sem_erros()
        self.assertEqual(self.at.session_state["historico"], [])
        self.assertEqual(len(self.at.session_state["df"]), 60)

    def test_aplicar_dicionario_com_mais_casos_que_variaveis(self):
        # Regressão do bug de len(df) vs len(colunas): exemplo tem 18 casos e 8 variáveis.
        df, sch = self.at.session_state["df"], self.at.session_state["schema"]
        ed = variaveis.tabela_dicionario(df, sch)
        ed.loc[0, "Rótulo"] = "ID do participante"
        novo_df, novo_sch = variaveis.aplicar_dicionario(df, ed)
        self.assertEqual(novo_sch["id_participante"]["rotulo"], "ID do participante")
        self.assertEqual(len(novo_df), 18)

    def test_pagina_de_graficos_e_relatorio_com_historico(self):
        self._botao("Executar análise").click().run()
        self._sem_erros()
        self.assertTrue(any(d.label.startswith("Relatório HTML") for d in self.at.get("download_button")))


if __name__ == "__main__":
    unittest.main()
