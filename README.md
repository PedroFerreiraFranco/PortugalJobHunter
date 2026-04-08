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

    .
    ├── app.py
    ├── scraper.py
    ├── requirements.txt
    └── templates
        └── index.html

## Como rodar localmente

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python app.py

Acesse: http://127.0.0.1:5000

## Deploy na Vercel

Este projeto já está configurado para Vercel com:

- `api/index.py` como entrada serverless Python
- `vercel.json` roteando todas as rotas para o app Flask

Passo a passo:

1. Suba este repositório para o GitHub.
2. Na Vercel, clique em **Add New Project** e selecione o repositório.
3. Mantenha as configurações padrão de Python e faça o deploy.

Observação importante:

- O cache em memória (TTL) funciona por instância serverless e pode ser reiniciado a qualquer momento.
  Ou seja, no ambiente da Vercel ele não é persistente/global entre invocações.

## Endpoints

- `GET /` — home com SSR das últimas vagas
- `GET /ultimas` — JSON das últimas vagas (5 por fonte)
- `GET|POST /buscar` — busca agregada (retorna JSON)

## Notas importantes

- Scraping depende de HTML externo; seletores podem mudar.
- Use com moderação para evitar sobrecarga nas plataformas.

## Licença

Projeto pessoal para fins educacionais e portfólio.
