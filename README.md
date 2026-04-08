<<<<<<< HEAD
# Portugal Job Hunter

Agregador de vagas de tecnologia em Portugal, com interface web em Flask e coleta de dados em **ITJobs** e **Net-Empregos**.

## Visão geral

- **Backend:** Flask (Python)
- **Coleta:**
  - ITJobs: scraping HTML da listagem + (opcional) detalhes via JSON-LD
  - Net-Empregos: consumo do RSS público + pós-filtros
- **Frontend:** Bootstrap 5 + Jinja (SSR na home) + fetch para buscas

## Funcionalidades

- Busca agregada em ITJobs e Net-Empregos
- Filtros por **termo**, **localização** e **regime** (presencial/remoto/híbrido)
- Home com SSR das últimas vagas (melhor TTFB e UX)
- Cache TTL em memória + headers de cache para CDN

## Estrutura

```
.
├── app.py
├── scraper.py
├── requirements.txt
└── templates
    └── index.html
```

## Como rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Acesse: http://127.0.0.1:5000

## Endpoints

- `GET /` — home com SSR das últimas vagas
- `GET /ultimas` — JSON das últimas vagas (5 por fonte)
- `GET|POST /buscar` — busca agregada (retorna JSON)

## Notas importantes

- Scraping depende de HTML externo; seletores podem mudar.
- Use com moderação para evitar sobrecarga nas plataformas.

## Licença

Projeto pessoal para fins educacionais e portfólio.
=======
# PortugalJobHunter
>>>>>>> 69023794717ee38d52afa6815451a4a0be301b63
