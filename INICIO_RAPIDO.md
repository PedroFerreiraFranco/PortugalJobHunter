# Guia de Início Rápido — Portugal Job Hunter

## 1) Ambiente virtual

```bash
python -m venv .venv
.venv\Scripts\activate
```

## 2) Dependências

```bash
pip install -r requirements.txt
```

## 3) Rodar a aplicação

```bash
python app.py
```

Abra no navegador:

- http://127.0.0.1:5000

## 4) Testar o scraper isolado

```bash
python scraper.py
```

## Solução de problemas

### PowerShell não executa .bat/.ps1 sem caminho

Use `./` no PowerShell:

```powershell
.\setup.ps1
.\iniciar.ps1
```

### Erro "No module named flask"

Ative a venv e reinstale:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### Nenhum resultado

- ITJobs é scraping HTML (seletores podem mudar)
- Net-Empregos usa RSS público (filtrado localmente)
- Verifique sua conectividade e tente novamente
