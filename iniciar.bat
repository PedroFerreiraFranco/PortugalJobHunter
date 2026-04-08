@echo off
echo ========================================
echo  Iniciando Portugal Job Hunter...
echo ========================================
echo.

if not exist .venv (
    echo ERRO: Ambiente virtual nao encontrado!
    echo Execute primeiro: setup.bat
    pause
    exit /b 1
)

echo Ativando ambiente virtual...
call .venv\Scripts\activate.bat

echo Iniciando servidor Flask...
echo.
echo Acesse: http://127.0.0.1:5000
echo.
echo Pressione Ctrl+C para parar o servidor
echo ========================================
echo.

python app.py
