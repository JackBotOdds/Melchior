from pydantic import BaseModel
from typing import Optional


class PredictionRequest(BaseModel):
    match_id: str
    season: Optional[str] = None
