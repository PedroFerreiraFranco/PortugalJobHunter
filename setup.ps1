# Script PowerShell para configurar Portugal Job Hunter
Write-Host "========================================"
Write-Host " Portugal Job Hunter - Setup Automatico" -ForegroundColor Cyan
Write-Host "========================================"
Write-Host ""

# Navegar para o diretório do projeto (pasta do script)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
Write-Host "[*] Diretorio: $PWD" -ForegroundColor Yellow
Write-Host ""

# Criar ambiente virtual
Write-Host "[1/4] Criando ambiente virtual..." -ForegroundColor Green
python -m venv .venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO ao criar ambiente virtual!" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "OK - Ambiente virtual criado!" -ForegroundColor Green
Write-Host ""

# Ativar ambiente virtual
Write-Host "[2/4] Ativando ambiente virtual..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1
Write-Host "OK - Ambiente ativado!" -ForegroundColor Green
Write-Host ""

# Instalar dependências
Write-Host "[3/4] Instalando dependencias..." -ForegroundColor Green
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO ao instalar dependencias!" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "OK - Dependencias instaladas!" -ForegroundColor Green
Write-Host ""

Write-Host "[4/4] Tudo pronto!" -ForegroundColor Green
Write-Host ""
Write-Host "========================================"
Write-Host " Para iniciar a aplicacao, execute:" -ForegroundColor Cyan
Write-Host " .\iniciar.ps1" -ForegroundColor Yellow
Write-Host "========================================"
Write-Host ""

pause
