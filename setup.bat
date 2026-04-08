@echo off
echo ========================================
echo  Portugal Job Hunter - Setup Automatico
echo ========================================
echo.

echo [1/4] Criando ambiente virtual...
python -m venv .venv
if %errorlevel% neq 0 (
    echo ERRO ao criar ambiente virtual!
    pause
    exit /b 1
)
echo OK - Ambiente virtual criado!
echo.

echo [2/4] Ativando ambiente virtual...
call .venv\Scripts\activate.bat
echo OK - Ambiente ativado!
echo.

echo [3/4] Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERRO ao instalar dependencias!
    pause
    exit /b 1
)
echo OK - Dependencias instaladas!
echo.

echo [4/4] Tudo pronto!
echo.
echo ========================================
echo  Para iniciar a aplicacao, execute:
echo  python app.py
echo ========================================
echo.

pause
