"""Importação com escolha da linha do cabeçalho (arquivos com notas acima da tabela)."""
import io
import unittest

import openpyxl
import pandas as pd

from data_utils import ler_arquivo, prever_arquivo


class Arq:
    def __init__(self, nome, conteudo):
        self.name, self._b = nome, conteudo

    def getvalue(self):
        return self._b


def xlsx(linhas, abas=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    for l in linhas:
        ws.append(l)
    for nome, ls in (abas or {}).items():
        w = wb.create_sheet(nome)
        for l in ls:
            w.append(l)
    buf = io.BytesIO()
    wb.save(buf)
    return Arq("dados.xlsx", buf.getvalue())


NOTAS = [["Estudo X — confidencial"], [], ["Coletado em 2026"],
         ["id", "grupo", "valor"], ["a", "G1", 1.5], ["b", "G2", 2.5], ["c", "G1", 3.0]]


class TestesLinhaCabecalhoExcel(unittest.TestCase):
    def test_cabecalho_na_linha_4(self):
        d = ler_arquivo(xlsx(NOTAS), linha_cabecalho=4)
        self.assertEqual(list(d.columns), ["id", "grupo", "valor"])
        self.assertEqual(d["valor"].tolist(), [1.5, 2.5, 3.0])
        self.assertEqual(len(d), 3)

    def test_padrao_e_linha_1(self):
        d = ler_arquivo(xlsx([["id", "v"], ["a", 1], ["b", 2]]))
        self.assertEqual(list(d.columns), ["id", "v"])

    def test_numeracao_da_previa_e_a_mesma_do_parser_com_linhas_em_branco(self):
        arq = xlsx(NOTAS)
        prev = prever_arquivo(arq)
        linha_id = int(prev.index[prev["Coluna 1"] == "id"][0])
        self.assertEqual(linha_id, 4)  # a linha em branco (2) conta
        self.assertEqual(list(ler_arquivo(arq, linha_cabecalho=linha_id).columns), ["id", "grupo", "valor"])

    def test_notas_como_cabecalho_gera_erro_claro_e_nao_dados_errados(self):
        with self.assertRaisesRegex(ValueError, "sem nome"):
            ler_arquivo(xlsx(NOTAS), linha_cabecalho=1)

    def test_linhas_e_colunas_vazias_de_formatacao_sao_ignoradas(self):
        linhas = [["x", "y", None], [1, 2, None], [3, 4, None], [None, None, None]]
        d = ler_arquivo(xlsx(linhas))
        self.assertEqual(list(d.columns), ["x", "y"])
        self.assertEqual(len(d), 2)

    def test_coluna_com_nome_mas_vazia_e_preservada(self):
        d = ler_arquivo(xlsx([["x", "pendente"], [1, None], [2, None]]))
        self.assertEqual(list(d.columns), ["x", "pendente"])
        self.assertEqual(int(d["pendente"].isna().sum()), 2)

    def test_linha_alem_do_fim_da_planilha(self):
        with self.assertRaises(ValueError):
            ler_arquivo(xlsx(NOTAS), linha_cabecalho=50)

    def test_cabecalho_na_ultima_linha_sem_dados(self):
        with self.assertRaisesRegex(ValueError, "não contém observações"):
            ler_arquivo(xlsx(NOTAS), linha_cabecalho=7)

    def test_escolha_de_aba_com_linha_de_cabecalho(self):
        arq = xlsx([["x"], [1]], abas={"Segunda": [["nota"], ["id", "v"], ["a", 9]]})
        d = ler_arquivo(arq, aba="Segunda", linha_cabecalho=2)
        self.assertEqual(list(d.columns), ["id", "v"])
        self.assertEqual(d["v"].tolist(), [9])

    def test_nomes_repetidos_sugerem_conferir_a_linha(self):
        with self.assertRaisesRegex(ValueError, "repetidos"):
            ler_arquivo(xlsx([["a", "a"], [1, 2]]))

    def test_valores_invalidos_de_linha(self):
        for ruim in (0, -3, "abc", None, 2.5 if False else "x"):
            with self.subTest(ruim=ruim), self.assertRaises(ValueError):
                ler_arquivo(xlsx(NOTAS), linha_cabecalho=ruim)


CSV_NOTAS = ("Notas do estudo\nOutra nota;com;vários;campos;extras\n"
             "id;grupo;valor\na;G1;1,5\nb;G2;2,5\n").encode("utf-8")


class TestesLinhaCabecalhoCSV(unittest.TestCase):
    def test_csv_com_notas_variando_numero_de_campos(self):
        d = ler_arquivo(Arq("t.csv", CSV_NOTAS), sep=";", decimal=",", linha_cabecalho=3)
        self.assertEqual(list(d.columns), ["id", "grupo", "valor"])
        self.assertEqual(d["valor"].tolist(), [1.5, 2.5])

    def test_csv_com_separador_automatico(self):
        d = ler_arquivo(Arq("t.csv", CSV_NOTAS), linha_cabecalho=3)
        self.assertEqual(list(d.columns), ["id", "grupo", "valor"])
        self.assertEqual(d["valor"].tolist(), [1.5, 2.5])

    def test_csv_cp1252_com_notas(self):
        raw = "Observação: coleta em São Paulo\nid;valor\na;1,5\n".encode("cp1252")
        d = ler_arquivo(Arq("t.csv", raw), sep=";", decimal=",", linha_cabecalho=2)
        self.assertEqual(list(d.columns), ["id", "valor"])

    def test_previa_do_csv_mostra_texto_bruto_numerado(self):
        prev = prever_arquivo(Arq("t.csv", CSV_NOTAS))
        self.assertEqual(prev.index.tolist(), [1, 2, 3, 4, 5])
        self.assertEqual(prev.loc[3, "Conteúdo da linha"], "id;grupo;valor")

    def test_previa_limita_linhas(self):
        raw = ("\n".join(["x"] + [str(i) for i in range(100)])).encode()
        self.assertEqual(len(prever_arquivo(Arq("t.csv", raw), linhas=10)), 10)

    def test_padrao_continua_igual_ao_comportamento_anterior(self):
        raw = "nome;valor\nPessoa A;1,25\nPessoa B;3,50\n".encode("utf-8")
        d = ler_arquivo(Arq("t.csv", raw), sep=";", decimal=",")
        self.assertAlmostEqual(float(d.loc[0, "valor"]), 1.25)

    def test_extensao_invalida(self):
        with self.assertRaises(ValueError):
            ler_arquivo(Arq("t.txt", b"x"))
        with self.assertRaises(ValueError):
            prever_arquivo(Arq("t.txt", b"x"))


if __name__ == "__main__":
    unittest.main()


class TestesNomesRepetidos(unittest.TestCase):
    def test_csv_com_cabecalho_repetido(self):
        with self.assertRaisesRegex(ValueError, "repetidos.*a"):
            ler_arquivo(Arq("t.csv", b"a;a;b\n1;2;3\n"), sep=";")
        with self.assertRaisesRegex(ValueError, "repetidos"):
            ler_arquivo(Arq("t.csv", b"a,a,b\n1,2,3\n"))  # separador automático

    def test_repetido_com_espacos_ao_redor(self):
        with self.assertRaisesRegex(ValueError, "repetidos"):
            ler_arquivo(Arq("t.csv", b"a; a ;b\n1;2;3\n"), sep=";")

    def test_nomes_parecidos_mas_distintos_sao_aceitos(self):
        d = ler_arquivo(Arq("t.csv", b"a;a1;A\n1;2;3\n"), sep=";")
        self.assertEqual(list(d.columns), ["a", "a1", "A"])

    def test_repetido_depois_das_notas(self):
        raw = b"nota\nx;x;y\n1;2;3\n"
        with self.assertRaisesRegex(ValueError, "linha 2"):
            ler_arquivo(Arq("t.csv", raw), sep=";", linha_cabecalho=2)


class TestesPrevia(unittest.TestCase):
    def test_previa_excel_em_branco_e_sem_ponto_zero(self):
        prev = prever_arquivo(xlsx(NOTAS))
        self.assertEqual(prev.loc[2, "Coluna 1"], "")          # linha em branco, não "None"/"nan"
        self.assertEqual(prev.loc[7, "Coluna 3"], "3")         # 3.0 -> "3"
        self.assertEqual(prev.loc[5, "Coluna 3"], "1.5")


from data_utils import ColunasSemNomeError  # noqa: E402


class TestesColunasSemNome(unittest.TestCase):
    def arq_meio(self):
        # coluna B sem nome no cabeçalho, mas com dados
        return xlsx([["a", None, "c"], [1, 10, 100], [2, 20, 200], [3, 30, 300]])

    def test_erro_informa_posicao_e_exemplos(self):
        with self.assertRaises(ColunasSemNomeError) as ctx:
            ler_arquivo(self.arq_meio())
        info = ctx.exception.colunas
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]["posicao"], 2)
        self.assertEqual(info[0]["exemplos"], ["10", "20", "30"])
        self.assertIsInstance(ctx.exception, ValueError)  # código antigo que captura ValueError continua valendo

    def test_dar_nome(self):
        chave = self._chave(self.arq_meio())
        d = ler_arquivo(self.arq_meio(), colunas_sem_nome={chave: "  valor_b "})
        self.assertEqual(list(d.columns), ["a", "valor_b", "c"])
        self.assertEqual(d["valor_b"].tolist(), [10, 20, 30])
        self.assertEqual(d["c"].tolist(), [100, 200, 300])

    def test_remover_coluna(self):
        chave = self._chave(self.arq_meio())
        d = ler_arquivo(self.arq_meio(), colunas_sem_nome={chave: None})
        self.assertEqual(list(d.columns), ["a", "c"])
        self.assertEqual(d["c"].tolist(), [100, 200, 300])

    def test_varias_colunas_decisoes_mistas(self):
        arq = xlsx([[None, "x", None], [1, 2, 3], [4, 5, 6]])
        with self.assertRaises(ColunasSemNomeError) as ctx:
            ler_arquivo(arq)
        k1, k2 = [c["chave"] for c in ctx.exception.colunas]
        d = ler_arquivo(arq, colunas_sem_nome={k1: "primeira", k2: None})
        self.assertEqual(list(d.columns), ["primeira", "x"])
        self.assertEqual(d["primeira"].tolist(), [1, 4])

    def test_decisao_parcial_ainda_pede_as_restantes(self):
        arq = xlsx([[None, "x", None], [1, 2, 3], [4, 5, 6]])
        with self.assertRaises(ColunasSemNomeError) as ctx:
            ler_arquivo(arq)
        k1, _ = [c["chave"] for c in ctx.exception.colunas]
        with self.assertRaises(ColunasSemNomeError) as ctx2:
            ler_arquivo(arq, colunas_sem_nome={k1: "primeira"})
        self.assertEqual(len(ctx2.exception.colunas), 1)

    def test_nome_novo_repetido_ou_invalido_e_recusado(self):
        chave = self._chave(self.arq_meio())
        for ruim in ("a", "c", "", "   ", "_oculta", "x" * 101, "com\nquebra"):
            with self.subTest(ruim=ruim), self.assertRaises(ValueError):
                ler_arquivo(self.arq_meio(), colunas_sem_nome={chave: ruim})

    def test_chaves_desconhecidas_sao_ignoradas(self):
        chave = self._chave(self.arq_meio())
        d = ler_arquivo(self.arq_meio(), colunas_sem_nome={chave: "b", "Unnamed: 99": "zzz"})
        self.assertEqual(list(d.columns), ["a", "b", "c"])

    def test_coluna_sem_nome_e_sem_dados_continua_sendo_descartada_sem_perguntar(self):
        d = ler_arquivo(xlsx([["a", None, "c"], [1, None, 100], [2, None, 200]]))
        self.assertEqual(list(d.columns), ["a", "c"])

    def test_com_notas_acima_e_linha_do_cabecalho(self):
        arq = xlsx([["Estudo"], [], ["a", None, "c"], [1, 10, 100], [2, 20, 200]])
        with self.assertRaises(ColunasSemNomeError) as ctx:
            ler_arquivo(arq, linha_cabecalho=3)
        d = ler_arquivo(arq, linha_cabecalho=3, colunas_sem_nome={ctx.exception.colunas[0]["chave"]: "b"})
        self.assertEqual(d["b"].tolist(), [10, 20])

    def _chave(self, arq):
        with self.assertRaises(ColunasSemNomeError) as ctx:
            ler_arquivo(arq)
        return ctx.exception.colunas[0]["chave"]


class TestesCSVCabecalhoCurto(unittest.TestCase):
    """Regressão: cabeçalho com MENOS campos que os dados fazia o pandas usar a 1ª coluna de dados
    como índice, deslocando silenciosamente todos os valores em relação aos nomes."""

    CSV = b"a;b\n1;2;3\n4;5;6\n"

    def test_nao_ha_mais_deslocamento_silencioso(self):
        with self.assertRaises(ColunasSemNomeError) as ctx:
            ler_arquivo(Arq("t.csv", self.CSV), sep=";")
        self.assertEqual(ctx.exception.colunas[0]["posicao"], 3)
        self.assertEqual(ctx.exception.colunas[0]["exemplos"], ["3", "6"])

    def test_valores_permanecem_alinhados_com_os_nomes(self):
        d = ler_arquivo(Arq("t.csv", self.CSV), sep=";", colunas_sem_nome={"Unnamed: 2": "c"})
        self.assertEqual(list(d.columns), ["a", "b", "c"])
        self.assertEqual(d["a"].tolist(), [1, 4])
        self.assertEqual(d["b"].tolist(), [2, 5])
        self.assertEqual(d["c"].tolist(), [3, 6])

    def test_remover_a_coluna_excedente_mantem_a_e_b_corretos(self):
        d = ler_arquivo(Arq("t.csv", self.CSV), sep=";", colunas_sem_nome={"Unnamed: 2": None})
        self.assertEqual(list(d.columns), ["a", "b"])
        self.assertEqual(d["a"].tolist(), [1, 4])
        self.assertEqual(d["b"].tolist(), [2, 5])

    def test_separador_automatico_e_dois_campos_excedentes(self):
        d = ler_arquivo(Arq("t.csv", b"a,b\n1,2,3,4\n5,6,7,8\n"),
                        colunas_sem_nome={"Unnamed: 2": "c", "Unnamed: 3": "d"})
        self.assertEqual(d["a"].tolist(), [1, 5])
        self.assertEqual(d["d"].tolist(), [4, 8])

    def test_cabecalho_com_campo_vazio_no_fim_ou_no_meio(self):
        d = ler_arquivo(Arq("t.csv", b"a;b;\n1;2;3\n"), sep=";", colunas_sem_nome={"Unnamed: 2": "c"})
        self.assertEqual(d.iloc[0].tolist(), [1, 2, 3])
        d = ler_arquivo(Arq("t.csv", b"a;;c\n1;2;3\n"), sep=";", colunas_sem_nome={"Unnamed: 1": "b"})
        self.assertEqual(list(d.columns), ["a", "b", "c"])
        self.assertEqual(d.iloc[0].tolist(), [1, 2, 3])

    def test_cabecalho_curto_depois_de_notas(self):
        raw = b"Nota qualquer\na;b\n1;2;3\n4;5;6\n"
        d = ler_arquivo(Arq("t.csv", raw), sep=";", linha_cabecalho=2, colunas_sem_nome={"Unnamed: 2": "c"})
        self.assertEqual(d["a"].tolist(), [1, 4])
        self.assertEqual(d["c"].tolist(), [3, 6])

    def test_decimais_com_virgula_no_cabecalho_curto(self):
        d = ler_arquivo(Arq("t.csv", b"a;b\n1,5;2,5;3,5\n"), sep=";", decimal=",",
                        colunas_sem_nome={"Unnamed: 2": "c"})
        self.assertEqual(d.iloc[0].tolist(), [1.5, 2.5, 3.5])

    def test_csv_normal_nao_e_afetado(self):
        d = ler_arquivo(Arq("t.csv", b"a;b\n1;2\n3;4\n"), sep=";")
        self.assertEqual(list(d.columns), ["a", "b"])
        self.assertEqual(d["a"].tolist(), [1, 3])


class TestesCasosDificeisCSV(unittest.TestCase):
    def test_primeira_coluna_de_dados_que_parece_indice_0_1_2(self):
        # Antes: o índice implícito [0, 1] era indistinguível de um índice normal.
        raw = b"a;b\n0;5;6\n1;7;8\n"
        with self.assertRaises(ColunasSemNomeError):
            ler_arquivo(Arq("t.csv", raw), sep=";")
        d = ler_arquivo(Arq("t.csv", raw), sep=";", colunas_sem_nome={"Unnamed: 2": "c"})
        self.assertEqual(d["a"].tolist(), [0, 1])
        self.assertEqual(d["b"].tolist(), [5, 7])

    def test_linha_mais_longa_depois_da_amostra_nao_passa_silenciosamente(self):
        linhas = ["a;b"] + ["1;2"] * 600 + ["3;4;5"]
        try:
            d = ler_arquivo(Arq("t.csv", "\n".join(linhas).encode()), sep=";")
        except Exception:
            return  # erro explícito do parser é aceitável
        # se não houve erro, nenhum valor pode ter sido deslocado
        self.assertEqual(d["a"].tolist()[-1], 3)
        self.assertEqual(d["b"].tolist()[-1], 4)

    def test_base_de_validacao_do_projeto_continua_igual(self):
        from pathlib import Path
        caminho = Path(__file__).resolve().parents[1] / "validacao_estatistica_ficticia.csv"
        d = ler_arquivo(Arq("validacao.csv", caminho.read_bytes()), sep=";", decimal=",")
        self.assertEqual(d.shape, (60, 9))
        self.assertEqual(d["pontuacao"].sum(), pd.read_csv(caminho, sep=";", decimal=",")["pontuacao"].sum())
        self.assertEqual(int(d["antes"].notna().sum()), 8)

    def test_arquivo_so_com_cabecalho(self):
        with self.assertRaises(ValueError):
            ler_arquivo(Arq("t.csv", b"a;b\n"), sep=";")

    def test_arquivo_vazio(self):
        with self.assertRaises(ValueError):
            ler_arquivo(Arq("t.csv", b""), sep=";")


class TestesRemoverTodas(unittest.TestCase):
    def test_marcar_todas_define_remover_em_cada_coluna(self):
        from paginas.dados import ACOES, marcar_todas_para_remover
        estado = {"acao_x_Unnamed: 1": ACOES[0], "acao_x_Unnamed: 3": ACOES[1], "outra_chave": "intacta"}
        marcar_todas_para_remover(estado, ["acao_x_Unnamed: 1", "acao_x_Unnamed: 3"])
        self.assertEqual(estado["acao_x_Unnamed: 1"], "Remover coluna")
        self.assertEqual(estado["acao_x_Unnamed: 3"], "Remover coluna")
        self.assertEqual(estado["outra_chave"], "intacta")  # não mexe em outros widgets

    def test_resultado_final_com_todas_removidas_mantem_so_as_colunas_nomeadas(self):
        arq = xlsx([["id", None, "grupo", None, "valor"], ["a", 1, "G1", "x", 1.5], ["b", 2, "G2", "y", 2.5]])
        with self.assertRaises(ColunasSemNomeError) as ctx:
            ler_arquivo(arq)
        todas = {c["chave"]: None for c in ctx.exception.colunas}
        d = ler_arquivo(arq, colunas_sem_nome=todas)
        self.assertEqual(list(d.columns), ["id", "grupo", "valor"])
        self.assertEqual(d["valor"].tolist(), [1.5, 2.5])
