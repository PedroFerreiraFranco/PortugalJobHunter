"""Portugal Job Hunter — agregador de vagas (Flask).

Rotas principais:
- GET /: home com SSR das últimas vagas (cache TTL)
- GET /ultimas: JSON das últimas vagas (cache TTL)
- GET/POST /buscar: busca agregada (ITJobs + Net-Empregos)
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List

from flask import Flask, jsonify, make_response, render_template, request

from scraper import buscar_todas_vagas, buscar_ultimas_itjobs, buscar_ultimas_net_empregos

CACHE_TTL_SECONDS = 180
CACHE_CONTROL = "public, max-age=0, s-maxage=60, stale-while-revalidate=300"
ULTIMAS_LIMITE_POR_FONTE = 20
ULTIMAS_PER_PAGE_PADRAO = 10

# ITJobs usa IDs numéricos para distrito. Usamos este mapa para converter o valor
# do dropdown em texto e reaproveitar como pós-filtro no Net-Empregos.
ITJOBS_LOCATION_ID_TO_NAME: Dict[str, str] = {
    "": "",
    "1": "Aveiro",
    "2": "Açores",
    "4": "Braga",
    "5": "Bragança",
    "6": "Castelo Branco",
    "8": "Coimbra",
    "9": "Faro",
    "10": "Évora",
    "13": "Leiria",
    "14": "Lisboa",
    "15": "Madeira",
    "17": "Setúbal",
    "18": "Porto",
    "20": "Santarém",
}


def _configure_utf8_stdio() -> None:
    """Configura stdout/stderr para UTF-8 (evita UnicodeEncodeError no Windows)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


_configure_utf8_stdio()

app = Flask(__name__)

_ULTIMAS_CACHE: Dict[str, Any] = {
    "atualizado_em": 0.0,
    "itjobs": [],
    "net_empregos": [],
    "erro": "",
}


def _parse_data_publicacao(valor: Any) -> float:
    """Converte diferentes formatos de data para timestamp; inválido vira 0."""
    s = str(valor or "").strip()
    if not s:
        return 0.0

    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        pass

    formatos = (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    )
    for fmt in formatos:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            continue

    return 0.0


def _ordenar_vagas_mais_recentes(vagas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ordena vagas por data de publicação desc (mais recentes primeiro)."""
    enumeradas = list(enumerate(vagas or []))
    enumeradas.sort(
        key=lambda item: (_parse_data_publicacao(item[1].get("data_publicacao")), item[0]),
        reverse=True,
    )
    return [vaga for _, vaga in enumeradas]


def _obter_ultimas_cached(ttl_segundos: int = CACHE_TTL_SECONDS) -> Dict[str, Any]:
    """Retorna as últimas vagas com cache TTL em memória."""
    agora = time.time()

    ts = float(_ULTIMAS_CACHE.get("atualizado_em") or 0.0)
    it = _ULTIMAS_CACHE.get("itjobs") or []
    ne = _ULTIMAS_CACHE.get("net_empregos") or []

    def _normalizar_vagas(lista: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for v in (lista or []):
            if not isinstance(v, dict):
                continue
            vv = dict(v)
            vv.pop("resumo", None)
            vv.setdefault("salario", "")
            out.append(vv)
        return out

    if (it or ne) and (agora - ts) < ttl_segundos:
        _ULTIMAS_CACHE["itjobs"] = _normalizar_vagas(it)
        _ULTIMAS_CACHE["net_empregos"] = _normalizar_vagas(ne)
        return _ULTIMAS_CACHE

    try:
        itjobs = buscar_ultimas_itjobs(
            limite=ULTIMAS_LIMITE_POR_FONTE,
            incluir_detalhes=True,
            max_detalhes=ULTIMAS_LIMITE_POR_FONTE,
        )
        net = buscar_ultimas_net_empregos(limite=ULTIMAS_LIMITE_POR_FONTE)

        _ULTIMAS_CACHE.update(
            {
                "atualizado_em": agora,
                "itjobs": _normalizar_vagas(itjobs),
                "net_empregos": _normalizar_vagas(net),
                "erro": "",
            }
        )
    except Exception as e:
        _ULTIMAS_CACHE["erro"] = str(e)

    return _ULTIMAS_CACHE


@app.route("/")
def index():
    """Página principal (SSR das últimas vagas)."""
    cache = _obter_ultimas_cached(ttl_segundos=CACHE_TTL_SECONDS)
    itjobs: List[dict] = list(cache.get("itjobs") or [])
    net: List[dict] = list(cache.get("net_empregos") or [])

    ultimas_todas = _ordenar_vagas_mais_recentes(itjobs + net)
    ultimas_vagas = ultimas_todas[:ULTIMAS_PER_PAGE_PADRAO]

    html = render_template(
        "index.html",
        ultimas_vagas=ultimas_vagas,
        ultimas_itjobs=itjobs,
        ultimas_net=net,
        ultimas_total=len(ultimas_todas),
        ultimas_page=1,
        ultimas_per_page=ULTIMAS_PER_PAGE_PADRAO,
        ultimas_has_more=len(ultimas_todas) > ULTIMAS_PER_PAGE_PADRAO,
        ultimas_erro=cache.get("erro") or "",
    )

    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    resp.headers["Cache-Control"] = CACHE_CONTROL
    return resp


@app.route("/ultimas", methods=["GET"])
def ultimas():
    """Retorna as últimas vagas (5 por plataforma)."""
    try:
        page = max(1, int((request.args.get("page") or "1").strip()))
        per_page = max(1, min(30, int((request.args.get("per_page") or str(ULTIMAS_PER_PAGE_PADRAO)).strip())))

        cache = _obter_ultimas_cached(ttl_segundos=CACHE_TTL_SECONDS)
        itjobs = list(cache.get("itjobs") or [])
        net = list(cache.get("net_empregos") or [])
        todas = _ordenar_vagas_mais_recentes(itjobs + net)

        inicio = (page - 1) * per_page
        fim = inicio + per_page
        vagas_pagina = todas[inicio:fim]
        has_more = fim < len(todas)

        resp = jsonify(
            {
                "sucesso": True,
                "vagas": vagas_pagina,
                "itjobs": itjobs,
                "net_empregos": net,
                "page": page,
                "per_page": per_page,
                "has_more": has_more,
                "total": len(todas),
                "cache_erro": cache.get("erro") or "",
            }
        )
        resp.headers["Content-Type"] = "application/json; charset=utf-8"
        resp.headers["Cache-Control"] = CACHE_CONTROL
        return resp
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": f"Erro ao obter últimas vagas: {str(e)}"})


@app.route("/buscar", methods=["GET", "POST"])
def buscar():
    """Endpoint para buscar vagas.

    Aceita GET ou POST.
    Campos esperados:
    - termo
    - localizacao (opcional)
    - modelo_trabalho (opcional)
    - plataforma (opcional: todas|itjobs|net_empregos)
    """
    try:
        data = request.form if request.method == "POST" else request.args

        termo_busca = (data.get("termo") or "").strip()
        localizacao = (data.get("localizacao") or "").strip()
        modelo_trabalho = (data.get("modelo_trabalho") or "").strip()
        plataforma = (data.get("plataforma") or "todas").strip().lower()

        plataformas_validas = {"todas", "itjobs", "net_empregos"}
        if plataforma not in plataformas_validas:
            return jsonify(
                {
                    "sucesso": False,
                    "mensagem": "Plataforma inválida. Use: todas, itjobs ou net_empregos.",
                }
            )

        if not termo_busca and not (localizacao or modelo_trabalho):
            return jsonify(
                {
                    "sucesso": False,
                    "mensagem": "Informe um termo de busca ou selecione pelo menos um filtro.",
                }
            )

        if localizacao and not localizacao.isdigit():
            localizacao_texto = localizacao
        else:
            localizacao_texto = ITJOBS_LOCATION_ID_TO_NAME.get(localizacao, "")

        if plataforma == "net_empregos" and not termo_busca and not localizacao_texto:
            return jsonify(
                {
                    "sucesso": False,
                    "mensagem": (
                        "Para buscar apenas no Net-Empregos, informe um termo ou localização. "
                        "O filtro de modelo é aplicado principalmente no ITJobs."
                    ),
                }
            )

        avisos: List[str] = []
        if plataforma == "net_empregos" and modelo_trabalho:
            avisos.append("Filtro de modelo ignorado para Net-Empregos.")

        vagas = buscar_todas_vagas(
            termo_busca=termo_busca,
            localizacao=localizacao,
            modelo_trabalho=modelo_trabalho,
            localizacao_texto=localizacao_texto,
            plataforma=plataforma,
        )

        resp = jsonify(
            {
                "sucesso": True,
                "total": len(vagas),
                "termo": termo_busca,
                "plataforma": plataforma,
                "avisos": avisos,
                "vagas": vagas,
            }
        )
        resp.headers["Content-Type"] = "application/json; charset=utf-8"
        return resp

    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": f"Erro ao buscar vagas: {str(e)}"})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
