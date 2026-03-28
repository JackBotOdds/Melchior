"""
betsapi_client.py — Cliente HTTP para a BetsAPI (Bet365 inplay stats).

Responsabilidades:
  - Buscar estatísticas ao vivo por fixture ID (fi)
  - Ler o token de BETSAPI_TOKEN (variável de ambiente)
  - Traduzir erros HTTP em exceções específicas

Uso:
  results = await fetch_inplay_stats("12345")

Nota: sem retry — responsabilidade do chamador (Java Predictive Service).
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

BETSAPI_STATS_URL = "https://api.b365api.com/v1/bet365/inplay_stats"
_TIMEOUT_SECONDS  = 10.0


class BetsAPIError(Exception):
    """Exceção base para falhas do cliente BetsAPI."""


class BetsAPIUnavailableError(BetsAPIError):
    """BetsAPI offline, timeout ou erro HTTP 5xx."""


class BetsAPIMatchNotFoundError(BetsAPIError):
    """Fixture não encontrado ou BetsAPI retornou success=0."""


def _get_token() -> str:
    token = os.environ.get("BETSAPI_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "BETSAPI_TOKEN não configurado. "
            "Adicione ao .env: BETSAPI_TOKEN=seu_token"
        )
    return token


async def fetch_inplay_stats(fi: str) -> dict:
    """
    Busca as estatísticas ao vivo do fixture `fi` na BetsAPI.

    Retorna o dicionário `results` do payload de resposta.
    Lança BetsAPIUnavailableError em caso de falha de rede ou HTTP 5xx.
    Lança BetsAPIMatchNotFoundError se o fixture não for encontrado.
    """
    token = _get_token()
    params = {"token": token, "FI": fi}

    logger.info("BetsAPI: buscando inplay_stats para fi=%s", fi)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(BETSAPI_STATS_URL, params=params)
    except httpx.TimeoutException as exc:
        raise BetsAPIUnavailableError(f"BetsAPI timeout para fi={fi}: {exc}") from exc
    except httpx.RequestError as exc:
        raise BetsAPIUnavailableError(f"BetsAPI indisponível para fi={fi}: {exc}") from exc

    if response.status_code >= 500:
        raise BetsAPIUnavailableError(
            f"BetsAPI retornou HTTP {response.status_code} para fi={fi}."
        )

    if response.status_code == 404:
        raise BetsAPIMatchNotFoundError(f"Fixture fi={fi} não encontrado na BetsAPI.")

    try:
        data = response.json()
    except Exception as exc:
        raise BetsAPIUnavailableError(f"BetsAPI resposta inválida para fi={fi}: {exc}") from exc

    if data.get("success") != 1:
        raise BetsAPIMatchNotFoundError(
            f"BetsAPI retornou success=0 para fi={fi}. "
            f"Verifique se o fixture existe e está ao vivo."
        )

    results = data.get("results")
    if not results:
        raise BetsAPIMatchNotFoundError(
            f"BetsAPI não retornou dados para fi={fi}. O jogo pode ter encerrado."
        )

    logger.info("BetsAPI: dados recebidos para fi=%s", fi)
    return results
