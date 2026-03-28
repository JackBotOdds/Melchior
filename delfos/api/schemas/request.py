from __future__ import annotations

from typing import Optional

import pandas as pd
from pydantic import BaseModel


class PredictionRequest(BaseModel):
    """Predição a partir de um match_id histórico no feature store."""
    match_id: str
    season: Optional[str] = None


class LiveMatchRequest(BaseModel):
    """
    Predição a partir de features brutas de um jogo em andamento (via BetsAPI).

    Enviado no intervalo (timer.q == "HT") ou durante o 1º tempo (timer.q == "1").
    Os valores são normalizados automaticamente pelo scaler antes da inferência.
    """
    competition_type: str = "Domestic League"

    ht_goals_home:        float = 0.0
    ht_goals_away:        float = 0.0
    ht_shots_home:        float = 0.0
    ht_shots_away:        float = 0.0
    ht_sog_home:          float = 0.0
    ht_sog_away:          float = 0.0
    ht_fouls_home:        float = 0.0
    ht_fouls_away:        float = 0.0
    ht_corners_home:      float = 0.0
    ht_corners_away:      float = 0.0
    ht_yellow_cards_home: float = 0.0
    ht_yellow_cards_away: float = 0.0

    def to_series(self) -> pd.Series:
        data = self.model_dump()
        data["ht_goals_diff"] = self.ht_goals_home - self.ht_goals_away
        data["ht_shots_diff"] = self.ht_shots_home - self.ht_shots_away
        data["ht_sog_diff"]   = self.ht_sog_home   - self.ht_sog_away
        data["ht_fouls_diff"] = self.ht_fouls_home  - self.ht_fouls_away
        return pd.Series(data)
