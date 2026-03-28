"""
betsapi_mapper.py — Tradução do JSON da BetsAPI para LiveMatchRequest.

Funções puras (sem I/O). Aplica o mapeamento de campos BetsAPI → features HT
e valida se o jogo está na janela correta (1º tempo ou intervalo).

Mapeamento:
  on_target (home/away)              → ht_sog_home/away
  on_target + off_target (home/away) → ht_shots_home/away
  corners (home/away)                → ht_corners_home/away
  yellow_cards (home/away)           → ht_yellow_cards_home/away
  fouls (home/away)                  → ht_fouls_home/away
  scores home/away                   → ht_goals_home/away
"""

import logging

from delfos.api.schemas.request import LiveMatchRequest

logger = logging.getLogger(__name__)

# Períodos aceitos pelos modelos HT
_VALID_PERIODS = {"1", "HT", "1H", "45"}
# Períodos que indicam claramente que o jogo passou do intervalo
_INVALID_PERIODS = {"2", "2H", "FT", "ET", "P"}


def _safe_float(value, default: float = 0.0) -> float:
    """Converte string BetsAPI (ex: '5') para float, retornando default em caso de falha."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning("BetsAPI: valor inválido '%s', usando default=%s", value, default)
        return default


def _extract_stats(results: dict) -> tuple[dict, dict]:
    """
    Extrai os dicionários de stats home e away do payload BetsAPI.
    Tenta múltiplas estruturas conhecidas da API.
    """
    # Estrutura mais comum: results.stats.home / results.stats.away
    stats = results.get("stats", {})
    if isinstance(stats, dict) and "home" in stats:
        return stats.get("home", {}), stats.get("away", {})

    # Estrutura alternativa: results.Inplay_Match_Stats_1_Stats.home
    for key, val in results.items():
        if isinstance(val, dict) and "home" in val and "away" in val:
            return val.get("home", {}), val.get("away", {})

    return {}, {}


def _extract_scores(results: dict) -> tuple[float, float]:
    """Extrai placar atual (home_score, away_score) do payload BetsAPI."""
    scores = results.get("scores", results.get("score", {}))
    if isinstance(scores, dict):
        home = _safe_float(scores.get("home", scores.get("home_score", 0)))
        away = _safe_float(scores.get("away", scores.get("away_score", 0)))
        return home, away
    return 0.0, 0.0


def _extract_period(results: dict) -> str:
    """Extrai o identificador de período atual do payload BetsAPI."""
    timer = results.get("timer", {})
    if isinstance(timer, dict):
        # timer.q é o campo padrão do Bet365: "1", "HT", "2", "FT"
        period = str(timer.get("q", timer.get("period", ""))).strip()
        if period:
            return period

    # Fallback: campo direto no results
    return str(results.get("time_status", results.get("period", "UNKNOWN"))).strip()


def assert_halftime_window(results: dict) -> None:
    """
    Valida que o jogo está no 1º tempo ou no intervalo.
    Lança ValueError se estiver no 2º tempo, prorrogação ou encerrado.
    Os modelos HT foram treinados com estatísticas do 1º tempo — chamadas fora
    dessa janela produzem predições degradadas.
    """
    period = _extract_period(results)

    if period in _INVALID_PERIODS:
        raise ValueError(
            f"Jogo fora da janela HT (período='{period}'). "
            "Os modelos HT só aceitam dados do 1º tempo ou intervalo. "
            "Para o 2º tempo, aguarde os modelos FT."
        )

    if period not in _VALID_PERIODS and period != "UNKNOWN":
        logger.warning("BetsAPI: período desconhecido '%s' — prosseguindo.", period)


def map_inplay_stats_to_request(
    results: dict,
    competition_type: str = "Domestic League",
) -> LiveMatchRequest:
    """
    Converte o dicionário `results` da BetsAPI em um LiveMatchRequest normalizado.
    Valores ausentes na BetsAPI são substituídos por 0 com log de aviso.
    """
    home_stats, away_stats = _extract_stats(results)
    goals_home, goals_away = _extract_scores(results)

    def _home(key: str) -> float:
        val = home_stats.get(key)
        if val is None:
            logger.warning("BetsAPI: campo '%s' ausente para home — usando 0", key)
        return _safe_float(val)

    def _away(key: str) -> float:
        val = away_stats.get(key)
        if val is None:
            logger.warning("BetsAPI: campo '%s' ausente para away — usando 0", key)
        return _safe_float(val)

    # Shots = on_target + off_target (BetsAPI não tem campo "total shots")
    ht_shots_home = _home("on_target") + _home("off_target")
    ht_shots_away = _away("on_target") + _away("off_target")

    return LiveMatchRequest(
        competition_type=competition_type,
        ht_goals_home=goals_home,
        ht_goals_away=goals_away,
        ht_shots_home=ht_shots_home,
        ht_shots_away=ht_shots_away,
        ht_sog_home=_home("on_target"),
        ht_sog_away=_away("on_target"),
        ht_fouls_home=_home("fouls"),
        ht_fouls_away=_away("fouls"),
        ht_corners_home=_home("corners"),
        ht_corners_away=_away("corners"),
        ht_yellow_cards_home=_home("yellow_cards"),
        ht_yellow_cards_away=_away("yellow_cards"),
    )
