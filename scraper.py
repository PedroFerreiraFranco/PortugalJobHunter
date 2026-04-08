"""Scrapers utilizados pelo Portugal Job Hunter.

Este módulo centraliza a coleta de vagas em duas fontes:

- ITJobs: scraping do HTML da listagem e, opcionalmente, leitura de detalhes via JSON-LD
  para campos mais estáveis (ex.: data de publicação e salário quando existir).
- Net-Empregos: consumo do RSS público e aplicação de pós-filtros por termo/localização.

As funções retornam uma lista padronizada de dicionários (ver TypedDict :class:`Vaga`).
"""

from __future__ import annotations

import html as html_lib
import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, TypedDict
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class Vaga(TypedDict):
    """Representa uma vaga normalizada para consumo no frontend."""

    titulo: str
    empresa: str
    link: str
    localizacao: str
    modelo_trabalho: str
    data_publicacao: str
    salario: str
    fonte: str


def _safe_print(msg: str) -> None:
    """Print resiliente a UnicodeEncodeError (comum no Windows/cp1252).

    Isso evita que uma simples mensagem de log que contenha emoji derrube a requisição.
    """
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode("utf-8", "backslashreplace").decode("utf-8"))
        except Exception:
            pass


def _normalizar_work_model(modelo_trabalho: str) -> str:
    """Normaliza a entrada do usuário para o parâmetro `work_model` do ITJobs.

    ITJobs (observado em produção):
    - work_model=0 -> Presencial
    - work_model=1 -> Remoto
    - work_model=2 -> Híbrido

    Também aceitamos alguns aliases por compatibilidade.
    """
    if not modelo_trabalho:
        return ""

    valor = str(modelo_trabalho).strip().lower()

    if valor in {"0", "presencial", "presencialmente"}:
        return "0"
    if valor in {"1", "remoto", "remote", "100% remoto", "100%remoto"}:
        return "1"
    if valor in {"2", "hibrido", "híbrido", "hybrid"}:
        return "2"

    if valor in {"remote=1", "remote:1"}:
        return "1"
    if valor in {"remote=2", "remote:2"}:
        return "2"

    return ""


def _criar_headers() -> Dict[str, str]:
    """Headers básicos para reduzir bloqueios/HTML incompleto."""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        ),
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
    }


def _limpar_texto(texto: Optional[str]) -> str:
    """Normaliza texto extraído do HTML/RSS.

    - Decodifica entidades HTML (ex: "&#129346;" -> emoji) para evitar aparecer como
      "&amp;#129346;" no frontend.
    - Corrige alguns casos com caractere de substituição (� / U+FFFD).
    """
    if not texto:
        return ""

    texto = html_lib.unescape(str(texto))
    texto = html_lib.unescape(texto)

    t = re.sub(r"\s+", " ", texto).strip()
    t = re.sub(r"H\uFFFD+brido", "Híbrido", t, flags=re.I)

    return t


def _extrair_detalhes_itjobs(link: str) -> Dict[str, str]:
    """Extrai detalhes de uma oferta do ITJobs via JSON-LD.

    Mantemos apenas campos que o ITJobs fornece com boa estabilidade.
    Atualmente usamos:
    - data_publicacao (datePosted)
    - salario (baseSalary), quando existir
    """

    def _formatar_salario(base_salary) -> str:
        if not base_salary:
            return ""

        if isinstance(base_salary, dict):
            unit = base_salary.get("unitText") or ""
            value = base_salary.get("value")

            currency = base_salary.get("currency") or ""
            txt = ""

            if isinstance(value, dict):
                unit = unit or value.get("unitText") or ""
                currency = currency or value.get("currency") or ""

                min_v = value.get("minValue")
                max_v = value.get("maxValue")
                v = value.get("value")

                if min_v is not None and max_v is not None:
                    txt = f"{min_v} - {max_v}"
                elif v is not None:
                    txt = str(v)
                elif min_v is not None:
                    txt = str(min_v)
                elif max_v is not None:
                    txt = str(max_v)
            else:
                txt = str(value) if value is not None else ""

            partes = [p for p in [txt, currency, unit] if p]
            return _limpar_texto(" ".join(partes))

        return _limpar_texto(str(base_salary))

    try:
        response = requests.get(link, headers=_criar_headers(), timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        script = soup.find("script", attrs={"type": "application/ld+json"})
        if not script or not script.string:
            return {}

        data = json.loads(script.string)
        out: Dict[str, str] = {}

        data_publicacao = data.get("datePosted") or ""
        if data_publicacao:
            out["data_publicacao"] = _limpar_texto(data_publicacao)

        salario = _formatar_salario(data.get("baseSalary"))
        if salario:
            out["salario"] = salario

        return out

    except requests.exceptions.Timeout:
        return {}
    except requests.exceptions.RequestException:
        return {}
    except Exception:
        return {}


def buscar_vagas_itjobs(
    termo: str = "",
    localizacao: str = "",
    modelo_trabalho: str = "",
    incluir_detalhes: bool = False,
    max_detalhes: int = 10,
    limite: int = 30,
) -> List[Vaga]:
    """Busca vagas no ITJobs (título, empresa, link e tags).

    Endpoint: https://www.itjobs.pt/emprego

    Parâmetros (GET):
    - q: termo de pesquisa
    - location: id do distrito (string)
    - work_model: 0 (presencial), 1 (remoto), 2 (híbrido)
    """
    vagas: List[Vaga] = []

    termo = (termo or "").strip()

    params: Dict[str, str] = {}
    if termo:
        params["q"] = termo

    localizacao_texto_filtro = ""
    if localizacao:
        if str(localizacao).strip().isdigit():
            params["location"] = str(localizacao).strip()
        else:
            localizacao_texto_filtro = str(localizacao).strip()

    if not params and not localizacao_texto_filtro:
        return vagas

    work_model = _normalizar_work_model(modelo_trabalho)
    if work_model:
        params["work_model"] = work_model

    url = "https://www.itjobs.pt/emprego"

    try:
        response = requests.get(url, params=params, headers=_criar_headers(), timeout=20)
        response.raise_for_status()

        if not response.encoding:
            response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")
        anchors = soup.select("div.list-title a.title[href]")

        vistos = set()
        for a in anchors:
            href = a.get("href", "").strip()
            if not href.startswith("/oferta/"):
                continue

            link = urljoin("https://www.itjobs.pt", href)
            if link in vistos:
                continue
            vistos.add(link)

            card = a.find_parent("li")

            titulo = _limpar_texto(a.get_text(" ", strip=True))

            empresa_el = card.select_one("div.list-name a") if card else None
            empresa = _limpar_texto(empresa_el.get_text(" ", strip=True) if empresa_el else "")

            detalhes_el = card.select_one("div.list-details") if card else None
            detalhes_txt = _limpar_texto(
                detalhes_el.get_text(" ", strip=True) if detalhes_el else ""
            )

            modelo_txt = ""
            if re.search(r"\bremoto\b", detalhes_txt, flags=re.I):
                modelo_txt = "Remoto"
            elif re.search(r"\bh[íi]brido\b", detalhes_txt, flags=re.I):
                modelo_txt = "Híbrido"
            elif re.search(r"\bpresencial\b", detalhes_txt, flags=re.I):
                modelo_txt = "Presencial"

            local_txt = detalhes_txt
            if modelo_txt:
                local_txt = re.sub(
                    rf"\b{re.escape(modelo_txt)}\b", "", local_txt, flags=re.I
                ).strip()
            local_txt = _limpar_texto(local_txt)

            if localizacao_texto_filtro and localizacao_texto_filtro.lower() not in local_txt.lower():
                continue

            vagas.append(
                {
                    "titulo": titulo,
                    "empresa": empresa,
                    "link": link,
                    "localizacao": local_txt,
                    "modelo_trabalho": modelo_txt,
                    "data_publicacao": "",
                    "salario": "",
                    "fonte": "ITJobs",
                }
            )

            if limite and len(vagas) >= limite:
                break

    except requests.exceptions.Timeout:
        _safe_print("ITJobs: timeout ao tentar obter resultados.")
    except requests.exceptions.RequestException as e:
        _safe_print(f"ITJobs: erro na requisição HTTP: {repr(e)}")
    except Exception as e:
        _safe_print(f"ITJobs: erro inesperado: {repr(e)}")

    if incluir_detalhes and vagas:
        # Busca detalhes apenas para as primeiras N vagas, para manter performance.
        for vaga in vagas[: max(0, int(max_detalhes))]:
            detalhes = _extrair_detalhes_itjobs(vaga["link"])
            if detalhes.get("data_publicacao"):
                vaga["data_publicacao"] = detalhes["data_publicacao"]
            if detalhes.get("salario"):
                vaga["salario"] = detalhes["salario"]

    return vagas


def _termo_bate_no_titulo(titulo: str, termo: str) -> bool:
    """Valida se o título parece relevante para o termo pesquisado.

    Regra simples e eficaz: todos os tokens do termo devem aparecer no título.
    Ex: "data engineer" exige "data" e "engineer".
    """
    termo = (termo or "").strip().lower()
    if not termo:
        return True

    tokens = [t for t in re.split(r"\s+", termo) if t]
    titulo_norm = (titulo or "").lower()

    return all(tok in titulo_norm for tok in tokens)


def _extrair_campos_rss_net_empregos(descricao: str) -> Dict[str, str]:
    """Extrai campos do RSS do Net-Empregos.

    O RSS traz `description` com HTML escapado, geralmente no formato:
    <b>Empresa: </b>Nome<br><b>Zona: </b>Lisboa<br><b>Data: </b>8-4-2026<br>
    """
    if not descricao:
        return {"empresa": "", "localizacao": "", "data_publicacao": "", "salario": ""}

    try:
        html_desc = html_lib.unescape(descricao)
        soup = BeautifulSoup(html_desc, "html.parser")

        empresa = ""
        local_txt = ""
        data_publicacao = ""
        salario = ""

        for b in soup.find_all("b"):
            label = _limpar_texto(b.get_text(" ", strip=True)).lower().rstrip(":")

            # Normalmente o valor está no próximo irmão (texto) após o <b>
            raw_val = b.next_sibling
            val = _limpar_texto(str(raw_val)) if raw_val is not None else ""

            if label == "empresa":
                empresa = val
            elif label == "zona":
                local_txt = val
            elif label == "data":
                data_publicacao = val
            elif label in {"salário", "salario", "vencimento", "remuneração", "remuneracao"}:
                salario = val

        categoria = ""
        for b in soup.find_all("b"):
            label = _limpar_texto(b.get_text(" ", strip=True)).lower().rstrip(":")
            raw_val = b.next_sibling
            val = _limpar_texto(str(raw_val)) if raw_val is not None else ""

            if label == "categoria":
                categoria = val

        return {
            "empresa": empresa,
            "localizacao": local_txt,
            "data_publicacao": data_publicacao,
            "salario": salario,
            "categoria": categoria,
        }

    except Exception:
        return {"empresa": "", "localizacao": "", "data_publicacao": "", "salario": ""}


def _parece_vaga_tech(texto: str) -> bool:
    """Heurística simples para manter o Net-Empregos focado em tecnologia.

    Quando o usuário não informa termo (ex: filtra só por localização), o RSS do Net-Empregos
    pode trazer vagas de qualquer área. Aqui tentamos restringir para vagas com sinais claros
    de TI/tech.

    Observação: existem falsos positivos clássicos por causa de termos como "programador"
    (ex: "Programador CNC"). Por isso há um bloqueio explícito para termos industriais.
    """
    t = (texto or "").lower()

    # Bloqueia casos industriais muito comuns (ex: CNC), mesmo que contenham "programador".
    negativos = {
        "cnc",
        "tornos",
        "fresadoras",
        "máquina",
        "maquina",
        "fabril",
        "produção",
        "producao",
    }
    if any(n in t for n in negativos):
        return False

    substrings = {
        "developer",
        "desenvolvedor",
        "programador",
        "engenheiro de software",
        "software",
        "frontend",
        "backend",
        "fullstack",
        "full stack",
        "devops",
        "dados",
        "quality assurance",
        "tester",
        "testes",
        "ciberseguran",
        "cybersecurity",
        "infosec",
        "segurança da informa",
        "cloud",
        "azure",
        "kubernetes",
        "docker",
        "linux",
        "sysadmin",
        "administrador de sistemas",
        "informát",
        "telecom",
    }

    if any(p in t for p in substrings):
        return True

    if re.search(r"\bdata\s+(engineer|analyst|scientist)\b", t, flags=re.I):
        return True

    if re.search(r"\b(qa|it|aws|gcp)\b", t, flags=re.I):
        return True

    return False


def buscar_ultimas_itjobs(
    limite: int = 5,
    incluir_detalhes: bool = True,
) -> List[Vaga]:
    """Retorna as últimas vagas do ITJobs (primeira página)."""
    vagas: List[Vaga] = []

    try:
        response = requests.get(
            "https://www.itjobs.pt/emprego",
            headers=_criar_headers(),
            timeout=20,
        )
        response.raise_for_status()
        if not response.encoding:
            response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")
        anchors = soup.select("div.list-title a.title[href]")

        vistos = set()
        for a in anchors:
            href = a.get("href", "").strip()
            if not href.startswith("/oferta/"):
                continue

            link = urljoin("https://www.itjobs.pt", href)
            if link in vistos:
                continue
            vistos.add(link)

            card = a.find_parent("li")
            titulo = _limpar_texto(a.get_text(" ", strip=True))

            empresa_el = card.select_one("div.list-name a") if card else None
            empresa = _limpar_texto(empresa_el.get_text(" ", strip=True) if empresa_el else "")

            detalhes_el = card.select_one("div.list-details") if card else None
            detalhes_txt = _limpar_texto(detalhes_el.get_text(" ", strip=True) if detalhes_el else "")

            modelo_txt = ""
            if re.search(r"\bremoto\b", detalhes_txt, flags=re.I):
                modelo_txt = "Remoto"
            elif re.search(r"\bh[íi]brido\b", detalhes_txt, flags=re.I):
                modelo_txt = "Híbrido"
            elif re.search(r"\bpresencial\b", detalhes_txt, flags=re.I):
                modelo_txt = "Presencial"

            local_txt = detalhes_txt
            if modelo_txt:
                local_txt = re.sub(rf"\b{re.escape(modelo_txt)}\b", "", local_txt, flags=re.I).strip()
            local_txt = _limpar_texto(local_txt)

            vaga = {
                "titulo": titulo,
                "empresa": empresa,
                "link": link,
                "localizacao": local_txt,
                "modelo_trabalho": modelo_txt,
                "data_publicacao": "",
                "salario": "",
                "fonte": "ITJobs",
            }

            vagas.append(vaga)
            if limite and len(vagas) >= limite:
                break

    except requests.exceptions.Timeout:
        _safe_print("ITJobs: timeout ao tentar obter últimas vagas.")
    except requests.exceptions.RequestException as e:
        _safe_print(f"ITJobs: erro na requisição HTTP (últimas): {repr(e)}")
    except Exception as e:
        _safe_print(f"ITJobs: erro inesperado (últimas): {repr(e)}")

    if incluir_detalhes and vagas:
        for vaga in vagas:
            detalhes = _extrair_detalhes_itjobs(vaga["link"])
            if detalhes.get("data_publicacao"):
                vaga["data_publicacao"] = detalhes["data_publicacao"]
            if detalhes.get("salario"):
                vaga["salario"] = detalhes["salario"]

    return vagas


def buscar_ultimas_net_empregos(limite: int = 5) -> List[Vaga]:
    """Retorna as últimas vagas do Net-Empregos via RSS, filtrando para tecnologia."""
    vagas: List[Vaga] = []

    try:
        response = requests.get(
            "https://www.net-empregos.com/rssfeed.asp",
            headers=_criar_headers(),
            timeout=20,
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)
        channel = root.find("channel")
        if channel is None:
            return vagas

        vistos = set()
        for item in channel.findall("item"):
            titulo = _limpar_texto(item.findtext("title", ""))
            link = _limpar_texto(item.findtext("link", ""))
            pub_date = _limpar_texto(item.findtext("pubDate", ""))
            descricao = item.findtext("description", "") or ""

            if not titulo or not link:
                continue

            campos = _extrair_campos_rss_net_empregos(descricao)
            empresa = campos.get("empresa", "")
            local_txt = campos.get("localizacao", "")
            data_publicacao = campos.get("data_publicacao", "") or pub_date
            salario = campos.get("salario", "")
            categoria = campos.get("categoria", "")

            if not _parece_vaga_tech(f"{titulo} {categoria}"):
                continue

            if link in vistos:
                continue
            vistos.add(link)

            vagas.append(
                {
                    "titulo": titulo,
                    "empresa": empresa,
                    "link": link,
                    "localizacao": local_txt,
                    "modelo_trabalho": "",
                    "data_publicacao": data_publicacao,
                    "salario": salario,
                    "fonte": "Net-Empregos",
                }
            )

            if limite and len(vagas) >= limite:
                break

    except requests.exceptions.Timeout:
        _safe_print("Net-Empregos: timeout ao tentar obter RSS (últimas).")
    except requests.exceptions.RequestException as e:
        _safe_print(f"Net-Empregos: erro na requisição HTTP (últimas): {repr(e)}")
    except Exception as e:
        _safe_print(f"Net-Empregos: erro inesperado (últimas): {repr(e)}")

    return vagas


def buscar_vagas_net_empregos(
    termo: str,
    localizacao_filtro: str = "",
    limite: int = 30,
) -> List[Vaga]:
    """Busca vagas no Net-Empregos via RSS público e aplica pós-filtros.

    RSS: https://www.net-empregos.com/rssfeed.asp
    """
    vagas: List[Vaga] = []

    termo = (termo or "").strip()
    localizacao_filtro = (localizacao_filtro or "").strip()

    # Evita listar "tudo" sem nenhum filtro.
    if not termo and not localizacao_filtro:
        return vagas

    url = "https://www.net-empregos.com/rssfeed.asp"

    try:
        response = requests.get(url, headers=_criar_headers(), timeout=20)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        channel = root.find("channel")
        if channel is None:
            return vagas

        vistos = set()
        for item in channel.findall("item"):
            titulo = _limpar_texto(item.findtext("title", ""))
            link = _limpar_texto(item.findtext("link", ""))
            pub_date = _limpar_texto(item.findtext("pubDate", ""))
            descricao = item.findtext("description", "") or ""

            if not titulo or not link:
                continue

            if termo and not _termo_bate_no_titulo(titulo, termo):
                texto_desc = _limpar_texto(html_lib.unescape(descricao))
                if not _termo_bate_no_titulo(texto_desc, termo):
                    continue

            campos = _extrair_campos_rss_net_empregos(descricao)
            empresa = campos.get("empresa", "")
            local_txt = campos.get("localizacao", "")
            data_publicacao = campos.get("data_publicacao", "") or pub_date
            salario = campos.get("salario", "")
            categoria = campos.get("categoria", "")

            if localizacao_filtro and localizacao_filtro.lower() not in local_txt.lower():
                continue

            if not termo and not _parece_vaga_tech(f"{titulo} {categoria}"):
                continue

            if link in vistos:
                continue
            vistos.add(link)

            vagas.append(
                {
                    "titulo": titulo,
                    "empresa": empresa,
                    "link": link,
                    "localizacao": local_txt,
                    "modelo_trabalho": "",
                    "data_publicacao": data_publicacao,
                    "salario": salario,
                    "fonte": "Net-Empregos",
                }
            )

            if limite and len(vagas) >= limite:
                break

    except requests.exceptions.Timeout:
        _safe_print("Net-Empregos: timeout ao tentar obter RSS.")
    except requests.exceptions.RequestException as e:
        _safe_print(f"Net-Empregos: erro na requisição HTTP: {repr(e)}")
    except Exception as e:
        _safe_print(f"Net-Empregos: erro inesperado: {repr(e)}")

    return vagas


def buscar_todas_vagas(
    termo_busca: str = "",
    localizacao: str = "",
    modelo_trabalho: str = "",
    localizacao_texto: str = "",
    verbose: bool = False,
) -> List[Vaga]:
    """Agrega vagas de ITJobs e Net-Empregos.

    Regras principais:
    - Permite busca sem termo desde que exista ao menos um filtro.
    - O filtro de regime (presencial/remoto/híbrido) é aplicado apenas no ITJobs.
    - O Net-Empregos é consumido via RSS e filtrado localmente.

    Args:
        termo_busca: Termo de busca (ex.: "Python").
        localizacao: ID (ITJobs) ou texto (pós-filtro) da localização.
        modelo_trabalho: Regime desejado (aplicado no ITJobs).
        localizacao_texto: Nome do distrito (usado para pós-filtro no Net-Empregos).
        verbose: Quando True, emite logs no console.
    """
    todas_vagas: List[Vaga] = []

    termo_busca = (termo_busca or "").strip()

    if not termo_busca and not (localizacao or modelo_trabalho):
        return todas_vagas

    if verbose:
        _safe_print(f"Buscando vagas no ITJobs (termo={termo_busca!r})...")

    vagas_itjobs = buscar_vagas_itjobs(
        termo=termo_busca,
        localizacao=localizacao,
        modelo_trabalho=modelo_trabalho,
        incluir_detalhes=True,
        max_detalhes=10,
    )
    todas_vagas.extend(vagas_itjobs)

    if verbose:
        _safe_print(f"OK - Encontradas {len(vagas_itjobs)} vagas no ITJobs")

    if not modelo_trabalho and (termo_busca or localizacao_texto):
        if verbose:
            _safe_print(
                f"Buscando vagas no Net-Empregos (termo={termo_busca!r}, local={localizacao_texto!r})..."
            )

        vagas_net = buscar_vagas_net_empregos(
            termo_busca,
            localizacao_filtro=localizacao_texto,
        )
        todas_vagas.extend(vagas_net)

        if verbose:
            _safe_print(f"OK - Encontradas {len(vagas_net)} vagas no Net-Empregos")

    return todas_vagas


if __name__ == "__main__":
    resultado = buscar_todas_vagas("Python", verbose=True)
    print(f"\nTotal de vagas encontradas: {len(resultado)}")

    for i, vaga in enumerate(resultado[:5], 1):
        print(f"\n{i}. {vaga.get('titulo', '')}")
        if vaga.get("empresa"):
            print(f"   Empresa: {vaga['empresa']}")
        if vaga.get("localizacao"):
            print(f"   Local: {vaga['localizacao']}")
        if vaga.get("modelo_trabalho"):
            print(f"   Modelo: {vaga['modelo_trabalho']}")
        if vaga.get("salario"):
            print(f"   Salário: {vaga['salario']}")
        print(f"   Fonte: {vaga.get('fonte', '')}")
        print(f"   Link: {vaga.get('link', '')}")
