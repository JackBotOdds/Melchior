"""
feature_store.py — Lookup de features por match_id nos parquets processados.

Os parquets gerados pelo preprocessor.py já têm as features normalizadas
(StandardScaler aplicado no ETL). O competition_type é mantido como string
para que a inference.py aplique get_dummies na ordem correta do modelo.

Sprint 1: usa dados StatsBomb históricos.
Sprint futura: substituir por lookup na BetsAPI com features brutas + scaler.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT_DIR      = Path(__file__).resolve().parents[3]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

logger = logging.getLogger(__name__)

# Colunas relevantes por granularidade (features + identificadores)
_TEAM_OUTCOME_COLS = [
    "match_id", "competition_type",
    "ht_goals_diff", "ht_shots_diff", "ht_sog_diff", "ht_fouls_diff",
    "ht_shots_home", "ht_shots_away", "ht_fouls_home", "ht_fouls_away",
    "ht_corners_home", "ht_corners_away",
    "ht_yellow_cards_home", "ht_yellow_cards_away",
]

_TEAM_SOG_COLS = [
    "match_id", "competition_type",
    "ht_shots_home", "ht_shots_away",
    "ht_sog_home",   "ht_sog_away",
    "ht_goals_home", "ht_goals_away",
]


class FeatureStore:
    def __init__(self):
        self._team_outcome: Optional[pd.DataFrame] = None
        self._team_sog:     Optional[pd.DataFrame] = None

    def load(self):
        self._team_outcome = self._load_granularity("team_outcome", _TEAM_OUTCOME_COLS)
        self._team_sog     = self._load_granularity("team_sog",     _TEAM_SOG_COLS)

        if self._team_outcome is not None:
            logger.info("FeatureStore: team_outcome — %d partidas.", len(self._team_outcome))
        if self._team_sog is not None:
            logger.info("FeatureStore: team_sog — %d partidas.", len(self._team_sog))

    def _load_granularity(self, gran: str, cols: list[str]) -> Optional[pd.DataFrame]:
        """Carrega train + holdout e combina em um índice por match_id."""
        frames = []
        for split in ("train", "holdout"):
            path = PROCESSED_DIR / f"{gran}_{split}.parquet"
            if path.exists():
                df = pd.read_parquet(path)
                available = [c for c in cols if c in df.columns]
                frames.append(df[available])
            else:
                logger.warning("Parquet não encontrado: %s", path)

        if not frames:
            return None

        combined = pd.concat(frames, ignore_index=True)
        combined["match_id"] = combined["match_id"].astype(int)
        combined = combined.drop_duplicates(subset=["match_id"])
        combined = combined.set_index("match_id")
        return combined

    def get_team_outcome(self, match_id: int) -> Optional[pd.Series]:
        if self._team_outcome is None:
            return None
        return self._team_outcome.loc[match_id] if match_id in self._team_outcome.index else None

    def get_team_sog(self, match_id: int) -> Optional[pd.Series]:
        if self._team_sog is None:
            return None
        return self._team_sog.loc[match_id] if match_id in self._team_sog.index else None
