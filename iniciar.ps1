# Script PowerShell para iniciar Portugal Job Hunter
Write-Host "========================================"
Write-Host " Iniciando Portugal Job Hunter..." -ForegroundColor Cyan
Write-Host "========================================"
Write-Host ""

# Navegar para o diretório do projeto (pasta do script)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Verificar se ambiente virtual existe
if (-not (Test-Path ".venv")) {
    Write-Host "ERRO: Ambiente virtual nao encontrado!" -ForegroundColor Red
    Write-Host "Execute primeiro: .\setup.ps1" -ForegroundColor Yellow
    pause
    exit 1
}

# Ativar ambiente virtual
Write-Host "Ativando ambiente virtual..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1

# Iniciar servidor
Write-Host "Iniciando servidor Flask..." -ForegroundColor Green
Write-Host ""
Write-Host "Acesse: http://127.0.0.1:5000" -ForegroundColor Yellow
Write-Host ""
Write-Host "Pressione Ctrl+C para parar o servidor" -ForegroundColor Cyan
Write-Host "========================================"
Write-Host ""

python app.py
