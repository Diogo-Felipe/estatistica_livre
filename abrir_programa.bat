@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv315\Scripts\python.exe" (
 echo O ambiente Python 3.15 nao foi encontrado nesta pasta.
 echo Iniciando o instalador...
 call "%~dp0instalar_e_abrir_python315.bat"
 exit /b %errorlevel%
)
echo Iniciando Estatistica Livre 0.2 no navegador...
".venv315\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 (
 echo.
 echo Falha ao iniciar. Copie a mensagem exibida acima.
 pause
)
