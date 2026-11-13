@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title Estatistica Livre - Python 3.15

echo ================================================
echo   ESTATISTICA LIVRE - PYTHON 3.15.2 - WINDOWS
echo ================================================
echo.
echo Pasta atual: %CD%
echo.
where py >nul 2>nul
if errorlevel 1 goto PYTHON_ERRO
py -3.15 -c "import sys,struct; print('Python:',sys.version.split()[0]); print('Arquitetura:',struct.calcsize('P')*8,'bits'); assert sys.version_info[:2] == (3,15) and struct.calcsize('P')*8 == 64" 
if errorlevel 1 goto PYTHON_ERRO

if not exist ".venv315\Scripts\python.exe" (
  echo [1/4] Criando ambiente exclusivo do Python 3.15...
  py -3.15 -m venv .venv315
  if errorlevel 1 goto FALHA
) else (
  echo [1/4] Ambiente .venv315 ja existe.
)

echo [2/4] Atualizando pip...
".venv315\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto FALHA

echo [3/4] Instalando pacotes pre-compilados...
echo   Registro detalhado: instalacao_python315.log
".venv315\Scripts\python.exe" -m pip install --only-binary=:all: --log instalacao_python315.log -r requirements.txt
if errorlevel 1 goto FALHA

echo [4/4] Conferindo dependencias...
".venv315\Scripts\python.exe" -m pip check
if errorlevel 1 goto FALHA
".venv315\Scripts\python.exe" diagnostico.py
if errorlevel 1 goto FALHA

echo.
echo Iniciando aplicativo em http://localhost:8501
echo Se nao abrir automaticamente, copie o endereco acima no navegador.
echo Para parar, pressione Ctrl+C nesta janela.
".venv315\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto FALHA
pause
exit /b 0

:PYTHON_ERRO
echo.
echo ERRO: Python 3.15 de 64 bits nao encontrado.
echo Veja as versoes instaladas com: py --list-paths
echo Obtenha Python 3.15.2 64 bits em https://www.python.org/downloads/release/python-3152/
echo A instalacao exige Python 3.15 de 64 bits.
pause
exit /b 1

:FALHA
echo.
echo Falha na instalacao ou execucao.
echo Se for erro de pacote, veja instalacao_python315.log na mesma pasta.
echo Copie as ultimas linhas do erro e envie para diagnostico.
pause
exit /b 1
