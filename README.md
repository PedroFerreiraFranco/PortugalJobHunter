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

```text
.
├── app.py
├── scraper.py
├── requirements.txt
└── templates
    └── index.html
