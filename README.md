# Estatística Livre 0.2 — editor e relatórios

Aplicativo local, de código aberto (MIT), com aparência e fluxo de trabalho **inspirados em** softwares estatísticos com editor de casos e variáveis. Não usa código do IBM SPSS Statistics, não é um clone integral e não recebeu certificação estatística.

## Como executar

O programa roda **no seu computador**, pelo navegador. Não precisa de Docker nem de ambiente virtual.

### Requisitos

- **Python 3.11 ou mais novo**, 64 bits ([python.org/downloads](https://www.python.org/downloads/)). Na instalação, marque **"Add python.exe to PATH"**. Python 3.10 ou anterior **não** serve (o pandas 3 exige 3.11+).
- Internet apenas na primeira vez, para baixar as bibliotecas.
- Para conferir a versão instalada, abra o PowerShell e digite `py --list` (ou `python --version`).

### Passo a passo (Windows, PowerShell)

1. **Abra o PowerShell na pasta do projeto** (a que contém o `app.py`). No Explorador de Arquivos, clique na barra de endereço, digite `powershell` e tecle Enter. Ou digite:

   ```powershell
   cd "C:\caminho\para\Estatistica_Livre"
   ```

2. **Instale as bibliotecas (somente na primeira vez):**

   ```powershell
   py -3.11 -m pip install streamlit pandas numpy scipy matplotlib openpyxl pyarrow
   ```

   Se você usa outra versão (3.12, 3.13...), troque `-3.11` por ela, ou use `python -m pip install ...`.

3. **Inicie o programa:**

   ```powershell
   py -3.11 -m streamlit run app.py
   ```

   O navegador abre sozinho em **http://localhost:8501**. Se não abrir, copie esse endereço para a barra do navegador.

4. **Para encerrar**, volte à janela do PowerShell e pressione **Ctrl+C**.

Nas próximas vezes, repita apenas os passos **1, 3 e 4**.

> **Nada é salvo automaticamente.** Ao fechar o programa, dados e análises somem, a menos que você use **Salvar projeto (.elproj)** na barra lateral e exporte o relatório na etapa **5 · Relatório**.

### Conferir se está tudo funcionando (opcional)

```powershell
py -3.11 -m unittest discover -s tests -v
```

O resultado esperado termina em **`Ran 152 tests ... OK`** (leva cerca de 1 minuto).

### Versões em que foi testado

Windows 11, Python 3.11, Streamlit 1.67, pandas 3.1, NumPy 2.4, SciPy 1.17, matplotlib 3.11, openpyxl 3.1. Outras versões do Python (3.12 em diante) não foram testadas. Para publicar resultados, registre as versões exatas que você usou (`py -3.11 -m pip freeze`).

> O arquivo `requirements.txt` foi escrito para o Python 3.15 (versões mínimas mais altas) e **não foi testado com o Python 3.11**; por isso o passo 2 lista as bibliotecas diretamente.

### Atalhos `.bat` (alternativa)

Quem tem **Python 3.15 de 64 bits** pode usar os atalhos de duplo clique: `instalar_e_abrir_python315.bat` na primeira vez e `abrir_programa.bat` nas seguintes (veja a Opção B mais abaixo). Esses atalhos **não funcionam com outras versões do Python**.

### Problemas comuns

| Mensagem ou sintoma | O que fazer |
|---|---|
| `py` não é reconhecido | Reinstale o Python marcando "Add python.exe to PATH", ou use `python` no lugar de `py -3.11`. |
| `ModuleNotFoundError: No module named 'streamlit'` (ou pandas, scipy...) | Faça o passo 2 com **a mesma versão** do Python usada no passo 3. |
| A página não abre / "porta em uso" | Use outra porta: `py -3.11 -m streamlit run app.py --server.port 8502` e abra `http://localhost:8502`. |
| Alterei o código e a tela não mudou | Pare com Ctrl+C e inicie de novo (módulos importados ficam em cache). |
| O PowerShell não deixa executar | Rode os comandos acima sem `.ps1`; não é necessário alterar a política de execução. |

Uso local: evite publicar bases com dados pessoais ou clínicos identificáveis e não exponha o Streamlit à internet sem autenticação.

## O que mudou na 0.2

- **Visão de dados**: editar células, adicionar linhas, criar/excluir colunas, aplicar alterações, exportar CSV.
- **Visão de variáveis**: renomear colunas, escrever rótulos, definir tipo numérico/texto, escala/ordinal/nominal, códigos de ausentes e rótulos de valores (`0=Não;1=Sim`). Valores originais permanecem na tabela; códigos de ausentes são excluídos apenas na cópia de análise.
- **Análises estatísticas**: descritiva, Shapiro-Wilk, Pearson, Spearman, Welch, t pareado, Mann–Whitney, Wilcoxon, **Friedman** (3 ou mais medidas repetidas, com W de Kendall), ANOVA de uma via, χ² e Fisher 2×2. O **Spearman usa p exato por permutação quando N ≤ 9** (a aproximação pela distribuição t é imprecisa em amostras pequenas), e Spearman/Wilcoxon avisam quando o N é tão pequeno que o teste não consegue alcançar p < 0,05.
- **Relatórios estatísticos**: painel com testes executados, variáveis escolhidas, N, p-valor, tamanho de efeito (quando disponível), tabelas e notas de pressupostos. Exportação HTML, Excel (.xlsx), resumo CSV; o HTML pode ser impresso em PDF pelo navegador.
- **Projetos locais**: salvar/restaurar dados e metadados em `.elproj` (ZIP interno com JSON). **O histórico de análises não é salvo no arquivo de projeto**; exporte o relatório separadamente.
- **Testes de regressão**: 152 testes automatizados (motor estatístico, dicionário, relatórios, projeto, importação, interface e tema), incluindo resultados estatísticos de referência, dados ausentes, renomeação, segurança básica do HTML, round-trip do projeto e Excel de relatórios.

### Opção A — atualizar a instalação anterior, sem reinstalar as bibliotecas (recomendado)

1. **Feche o programa antigo** no PowerShell pressionando Ctrl+C; salve seus dados/relatórios antes de fechar, pois a sessão não persiste automaticamente.
2. Extraia o ZIP completo da versão 0.2 em uma **pasta nova**.
3. Dentro da pasta nova, abra `ATUALIZAR_INSTALACAO_EXISTENTE.bat`.
4. Quando solicitado, cole o caminho da pasta `Estatistica_Livre` **antiga** que já tem `.venv315` funcionando. Exemplo:

   `C:\Users\usuario\Downloads\Estatistica_Livre_codigo_fonte\Estatistica_Livre`

5. O atualizador cria backup de `app.py` e `data_utils.py`, copia os módulos novos e executa os testes usando o **seu ambiente existente**.
6. Abra `abrir_programa.bat` na pasta antiga; ou abra PowerShell nela e execute:

   ```powershell
   .\.venv315\Scripts\python.exe -m streamlit run app.py
   ```

Se preferir atualização manual, copie `app.py`, `schema.py`, `reports.py`, `project_io.py`, `data_utils.py` e `abrir_programa.bat` da versão nova **para a pasta antiga**, mantendo `.venv315`, `engine.py` e seus arquivos pessoais intactos. Isso não reinstala bibliotecas.

### Opção B — instalação nova no Windows 11 (Python 3.15.2 64 bits)

1. Extraia o ZIP e abra a pasta `Estatistica_Livre`.
2. Execute `instalar_e_abrir_python315.bat` (requer internet para a primeira instalação).
3. Aguarde; o app abrirá em `http://localhost:8501`.
4. Nas próximas vezes, use `abrir_programa.bat`.

O instalador usa `--only-binary=:all:` para evitar compilação de dependências no Windows. O executável Python precisa ser de 64 bits.

### Entradas e saídas

- Importação: `.csv` (`;`/`,`/TAB/automático, vírgula ou ponto decimal), `.xlsx` (seleção de aba). **Linha do cabeçalho configurável** (1 = primeira linha) para arquivos com títulos ou notas acima da tabela, com pré-visualização das primeiras linhas; as linhas acima do cabeçalho são ignoradas. **Colunas com dados mas sem nome no cabeçalho** podem receber um nome ou ser removidas no momento da importação (nunca são descartadas em silêncio).
- Exportação: dados em `.csv` UTF-8-sig; relatórios em `.html`, `.xlsx` e `.csv`; projeto em `.elproj`.
- Não abre `.sav` e não gera arquivo `.spv`; não executa sintaxe SPSS.
- Não executa dados no servidor da IBM. A execução é **local**, salvo se você configurar manualmente publicação remota.

### Importante sobre dados e análises

- Modificações do editor só são efetivadas quando você clicar em **Aplicar mudanças**.
- Alterar os dados ou o dicionário limpa o histórico para evitar relatórios desatualizados.
- A base de demonstração e a base de validação são **fictícias**. Dados novos aparecem ao importar seu arquivo.
- Rótulos de valores são metadados exibidos na prévia; os testes usam os códigos originais, para evitar alteração de tipos.
- O `α` representa critério de decisão, **não altera** o p-valor calculado.
- O programa não oferece modelos mistos, pós-testes de ANOVA, ajustes de multiplicidade, intervalos de confiança automáticos, controle avançado de outliers nem valores ausentes múltiplos. Implementações futuras exigem validação.
- **Cada linha deve representar uma unidade amostral independente**, exceto quando o teste é explicitamente pareado. Não trate diversas tentativas de uma mesma pessoa como participantes independentes.
- TCC e dados clínicos: evite importar identificadores pessoais em ambiente compartilhado. Não exponha o Streamlit à internet sem autenticação e avaliação de segurança.

### Testes automatizados

Na pasta com o ambiente Python ativo:

```powershell
.\.venv315\Scripts\python.exe -m unittest discover -s tests -v
```

Ou clique em `validar_windows.bat`. Resultado esperado: **Ran 152 tests ... OK**.

Estes testes foram executados neste ambiente de desenvolvimento com **Python 3.13**, não no Windows com Python 3.15.2. A interface Streamlit precisa ser conferida na sua máquina; testes automatizados não substituem validação científica.

### Estrutura do projeto

```text
Estatistica_Livre/
├── app.py                     # Streamlit: ponto de entrada (fluxo em 5 etapas)
├── paginas/                   # uma página por etapa (dados, variáveis, análises, gráficos, relatório)
├── componentes.py, estilo.py, estado.py, barra_lateral.py  # cabeçalho/cartões, CSS (claro/escuro), estado da sessão e painel lateral
├── interpretacao.py           # textos de interpretação e magnitude de efeito (sem Streamlit)
├── procedimentos.py           # catálogo de procedimentos e ligação com o engine
├── engine.py                  # motor estatístico preservado da 0.1.1
├── schema.py                  # metadados de variáveis e códigos de ausentes
├── data_utils.py              # CSV/Excel e exportação CSV
├── reports.py                 # histórico, HTML e Excel
├── project_io.py              # arquivo de projeto .elproj
├── tests/                     # 152 testes automatizados
├── requirements.txt           # dependências compatíveis com Python 3.15
├── exemplo_ficticio.csv       # teste visual
├── validacao_estatistica_ficticia.csv
├── instalar_e_abrir_python315.bat
├── ATUALIZAR_INSTALACAO_EXISTENTE.bat
├── abrir_programa.bat
└── validar_windows.bat
```

Licença: MIT. Projeto educacional independente.
