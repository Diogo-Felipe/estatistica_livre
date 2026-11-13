@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
echo ===================================================
echo    ESTATISTICA LIVRE 0.2 - ATUALIZAR SEM REINSTALAR
 echo ===================================================
echo.
echo Este utilitario atualiza a pasta da VERSAO ANTERIOR
 echo que ja funciona com Python 3.15.2.
echo Nao copia nem modifica o ambiente .venv315.
echo.
set /p "DEST=Cole o caminho completo da pasta Estatistica_Livre antiga: "
set "DEST=%DEST:"=%"
if not exist "%DEST%\.venv315\Scripts\python.exe" (
 echo.
 echo ERRO: pasta incorreta ou ambiente .venv315 ausente.
 echo Nenhum arquivo foi alterado.
 pause
 exit /b 1
)
if not exist "%DEST%\app.py" (
 echo ERRO: app.py nao encontrado na pasta de destino.
 pause
 exit /b 1
)
echo.
echo Salvando copia dos arquivos antigos...
if not exist "%DEST%\backup_antes_0_2" mkdir "%DEST%\backup_antes_0_2"
copy /Y "%DEST%\app.py" "%DEST%\backup_antes_0_2\app.py" >nul
copy /Y "%DEST%\data_utils.py" "%DEST%\backup_antes_0_2\data_utils.py" >nul
if errorlevel 1 goto FALHA
echo Atualizando codigo da interface e novos modulos...
for %%F in (app.py schema.py reports.py project_io.py data_utils.py abrir_programa.bat) do (
 copy /Y "%~dp0%%F" "%DEST%\%%F" >nul
 if errorlevel 1 goto FALHA
)
if not exist "%DEST%\tests" mkdir "%DEST%\tests"
copy /Y "%~dp0tests\test_v02.py" "%DEST%\tests\test_v02.py" >nul
if errorlevel 1 goto FALHA
 echo.
echo Verificando dependencias e 35 testes automatizados...
"%DEST%\.venv315\Scripts\python.exe" -m pip check
if errorlevel 1 goto FALHA
pushd "%DEST%"
".venv315\Scripts\python.exe" -m unittest discover -s tests -v > "validacao_v02.log" 2>&1
set "CODE=%ERRORLEVEL%"
popd
if not "%CODE%"=="0" (
 echo AVISO: testes falharam. Veja "%DEST%\validacao_v02.log".
 pause
 exit /b 1
)
echo.
echo Versao 0.2 atualizada com sucesso.
echo Para abrir, execute: "%DEST%\abrir_programa.bat"
echo Ou use o terminal nessa pasta com:
echo .venv315\Scripts\python.exe -m streamlit run app.py
pause
exit /b 0
:FALHA
echo.
echo ERRO: nao foi possivel concluir a atualizacao.
echo Confira permissoes e os arquivos na pasta de destino.
pause
exit /b 1
