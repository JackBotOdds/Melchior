from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import Literal


class MatchOutcomeResponse(BaseModel):
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    favorite_outcome: Literal["HOME", "DRAW", "AWAY"]
    confidence_score: float
    model_version: str
    generated_at: datetime

    @model_validator(mode="after")
    def check_probabilities_sum(self):
        total = self.home_win_probability + self.draw_probability + self.away_win_probability
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Soma das probabilidades = {total:.6f}, esperado 1.0 ± 0.001")
        return self


class TotalGoalsResponse(BaseModel):
    expected_goals: float
    over_25_probability: float
    under_25_probability: float
    most_likely_range: Literal["0-1", "2-3", "4+"]
    confidence_score: float
    model_version: str
    generated_at: datetime


class CornersResponse(BaseModel):
    expected_corners: float
    over_9_probability: float
    under_9_probability: float
    confidence_score: float
    model_version: str
    generated_at: datetime


class CardsResponse(BaseModel):
    expected_yellow_cards: float
    expected_red_cards: float
    over_3_yellow_probability: float
    under_3_yellow_probability: float
    confidence_score: float
    model_version: str
    generated_at: datetime
