@echo off
setlocal
cd /d "%~dp0"
set "PY=.venv315\Scripts\python.exe"
if not exist "%PY%" (
  echo ERRO: o ambiente .venv315 nao foi encontrado nesta pasta.
  echo Abra o programa pelo instalador ou crie o ambiente Python 3.15.2 antes.
  echo.
  pause
  exit /b 1
)
echo Validando os calculos do Estatistica Livre...
"%PY%" -m unittest discover -s tests -v > "validacao_resultados.log" 2>&1
set "CODIGO=%ERRORLEVEL%"
type "validacao_resultados.log"
echo.
if "%CODIGO%"=="0" (
 echo TODOS OS TESTES PASSARAM. Consulte validacao_resultados.log.
) else (
 echo FALHA NA VALIDACAO. Envie validacao_resultados.log para diagnostico.
)
pause
exit /b %CODIGO%
