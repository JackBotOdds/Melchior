"""
inference.py — Executa inferência ONNX e formata as respostas dos endpoints.

Fluxo por predição histórica (/v1/predict/*):
  1. Busca features do match_id no FeatureStore (dados já normalizados)
  2. Aplica get_dummies para competition_type
  3. Alinha colunas com os feature_names do modelo (ordem do treino)
  4. Executa sessão ONNX
  5. Formata response com campos derivados (over/under via Poisson, confidence)

Fluxo para predição ao vivo (/v1/predict/betsapi/*):
  1. Recebe LiveMatchRequest com features brutas da BetsAPI
  2. Deriva colunas de diferença (ht_shots_diff etc.)
  3. Normaliza via scaler do FeatureStore
  4. Executa sessão ONNX do modelo HT correspondente
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from scipy.stats import poisson

if TYPE_CHECKING:
    from delfos.api.schemas.request import LiveMatchRequest
    from delfos.api.services.feature_store import FeatureStore
    from delfos.api.services.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

# ── Features por modelo ───────────────────────────────────────────────────────

_MATCH_OUTCOME_FEATS = ["ht_goals_diff", "ht_shots_diff", "ht_sog_diff", "ht_fouls_diff"]
_TOTAL_GOALS_FEATS   = ["ht_shots_home", "ht_shots_away", "ht_sog_home", "ht_sog_away",
                        "ht_goals_home", "ht_goals_away"]
_CORNERS_FEATS       = ["ht_shots_home", "ht_shots_away", "ht_fouls_home", "ht_fouls_away",
                        "ht_corners_home", "ht_corners_away"]
_CARDS_FEATS         = ["ht_fouls_home", "ht_fouls_away",
                        "ht_yellow_cards_home", "ht_yellow_cards_away"]


# ── Helpers internos ──────────────────────────────────────────────────────────

def _build_input(row: pd.Series, numeric_feats: list[str], feature_names: list[str]) -> np.ndarray:
    data = {col: row[col] for col in numeric_feats if col in row.index}
    data["competition_type"] = row.get("competition_type", "Other")

    df = pd.DataFrame([data])
    df = pd.get_dummies(df, columns=["competition_type"])

    if feature_names:
        df = df.reindex(columns=feature_names, fill_value=0)

    return df.values.astype(np.float32)


def _run_session(session, X: np.ndarray):
    input_name = session.get_inputs()[0].name
    return session.run(None, {input_name: X})


def _extract_classifier_probs(outputs) -> list[float]:
    prob_output = outputs[1]
    if isinstance(prob_output, list) and isinstance(prob_output[0], dict):
        probs_dict = prob_output[0]
        return [probs_dict[k] for k in sorted(probs_dict.keys())]
    arr = np.array(prob_output)
    if arr.ndim == 2:
        return arr[0].tolist()
    return arr.tolist()


def _poisson_over_prob(lam: float, threshold: float) -> float:
    lam = max(lam, 0.01)
    return float(1.0 - poisson.cdf(int(threshold), lam))


def _most_likely_goals_range(expected: float) -> str:
    if expected < 1.5:
        return "0-1"
    elif expected < 3.5:
        return "2-3"
    return "4+"


def _row_from_live(req: "LiveMatchRequest", store: "FeatureStore", gran: str) -> pd.Series:
    """Converte LiveMatchRequest → pd.Series normalizado via scaler."""
    raw = req.to_series().to_dict()
    if gran == "team_sog":
        normalized = store.normalize_team_sog(raw)
    else:
        normalized = store.normalize_team_outcome(raw)
    return pd.Series(normalized)


# ── Predições históricas (match_id) ──────────────────────────────────────────

def predict_match_outcome(match_id: int, registry: "ModelRegistry", store: "FeatureStore") -> dict:
    if not registry.is_loaded("match_outcome"):
        raise RuntimeError("Modelo match_outcome não carregado.")
    row = store.get_team_outcome(match_id)
    if row is None:
        raise KeyError(f"match_id={match_id} não encontrado no dataset.")
    X = _build_input(row, _MATCH_OUTCOME_FEATS, registry.get_feature_names("match_outcome"))
    return _format_outcome(registry, _run_session(registry.get_session("match_outcome"), X))


def predict_total_goals(match_id: int, registry: "ModelRegistry", store: "FeatureStore") -> dict:
    if not registry.is_loaded("total_goals"):
        raise RuntimeError("Modelo total_goals não carregado.")
    row = store.get_team_sog(match_id)
    if row is None:
        raise KeyError(f"match_id={match_id} não encontrado no dataset.")
    X = _build_input(row, _TOTAL_GOALS_FEATS, registry.get_feature_names("total_goals"))
    return _format_goals(registry, _run_session(registry.get_session("total_goals"), X))


def predict_corners(match_id: int, registry: "ModelRegistry", store: "FeatureStore") -> dict:
    if not registry.is_loaded("corners"):
        raise RuntimeError("Modelo corners não carregado.")
    row = store.get_team_outcome(match_id)
    if row is None:
        raise KeyError(f"match_id={match_id} não encontrado no dataset.")
    X = _build_input(row, _CORNERS_FEATS, registry.get_feature_names("corners"))
    return _format_corners(registry, _run_session(registry.get_session("corners"), X))


def predict_cards(match_id: int, registry: "ModelRegistry", store: "FeatureStore") -> dict:
    if not registry.is_loaded("yellow_cards") or not registry.is_loaded("red_cards"):
        raise RuntimeError("Modelos yellow_cards e/ou red_cards não carregados.")
    row = store.get_team_outcome(match_id)
    if row is None:
        raise KeyError(f"match_id={match_id} não encontrado no dataset.")
    X_y = _build_input(row, _CARDS_FEATS, registry.get_feature_names("yellow_cards"))
    X_r = _build_input(row, _CARDS_FEATS, registry.get_feature_names("red_cards"))
    return _format_cards(
        registry,
        _run_session(registry.get_session("yellow_cards"), X_y),
        _run_session(registry.get_session("red_cards"), X_r),
    )


# ── Predições ao vivo / HT (features brutas via BetsAPI) ─────────────────────

def predict_match_outcome_live(req: "LiveMatchRequest", registry: "ModelRegistry", store: "FeatureStore") -> dict:
    if not registry.is_loaded("match_outcome"):
        raise RuntimeError("Modelo match_outcome não carregado.")
    if not store.has_scaler("team_outcome"):
        raise RuntimeError("Scaler team_outcome não disponível. Execute run_pipeline.py.")
    row = _row_from_live(req, store, "team_outcome")
    X = _build_input(row, _MATCH_OUTCOME_FEATS, registry.get_feature_names("match_outcome"))
    return _format_outcome(registry, _run_session(registry.get_session("match_outcome"), X))


def predict_total_goals_live(req: "LiveMatchRequest", registry: "ModelRegistry", store: "FeatureStore") -> dict:
    if not registry.is_loaded("total_goals"):
        raise RuntimeError("Modelo total_goals não carregado.")
    if not store.has_scaler("team_sog"):
        raise RuntimeError("Scaler team_sog não disponível. Execute run_pipeline.py.")
    row = _row_from_live(req, store, "team_sog")
    X = _build_input(row, _TOTAL_GOALS_FEATS, registry.get_feature_names("total_goals"))
    return _format_goals(registry, _run_session(registry.get_session("total_goals"), X))


def predict_corners_live(req: "LiveMatchRequest", registry: "ModelRegistry", store: "FeatureStore") -> dict:
    if not registry.is_loaded("corners"):
        raise RuntimeError("Modelo corners não carregado.")
    if not store.has_scaler("team_outcome"):
        raise RuntimeError("Scaler team_outcome não disponível. Execute run_pipeline.py.")
    row = _row_from_live(req, store, "team_outcome")
    X = _build_input(row, _CORNERS_FEATS, registry.get_feature_names("corners"))
    return _format_corners(registry, _run_session(registry.get_session("corners"), X))


def predict_cards_live(req: "LiveMatchRequest", registry: "ModelRegistry", store: "FeatureStore") -> dict:
    if not registry.is_loaded("yellow_cards") or not registry.is_loaded("red_cards"):
        raise RuntimeError("Modelos yellow_cards e/ou red_cards não carregados.")
    if not store.has_scaler("team_outcome"):
        raise RuntimeError("Scaler team_outcome não disponível. Execute run_pipeline.py.")
    row = _row_from_live(req, store, "team_outcome")
    X_y = _build_input(row, _CARDS_FEATS, registry.get_feature_names("yellow_cards"))
    X_r = _build_input(row, _CARDS_FEATS, registry.get_feature_names("red_cards"))
    return _format_cards(
        registry,
        _run_session(registry.get_session("yellow_cards"), X_y),
        _run_session(registry.get_session("red_cards"), X_r),
    )


# ── Formatadores de resposta ──────────────────────────────────────────────────

def _format_outcome(registry, outputs) -> dict:
    probs = _extract_classifier_probs(outputs)
    labels = ["HOME", "DRAW", "AWAY"]
    favorite_idx = int(np.argmax(probs))
    return {
        "home_win_probability": round(float(probs[0]), 4),
        "draw_probability":     round(float(probs[1]), 4),
        "away_win_probability": round(float(probs[2]), 4),
        "favorite_outcome":     labels[favorite_idx],
        "confidence_score":     round(float(max(probs)), 4),
        "model_version":        registry.manifest_version,
        "generated_at":         datetime.now(timezone.utc),
    }


def _format_goals(registry, outputs) -> dict:
    expected = float(outputs[0].flatten()[0])
    over_25  = _poisson_over_prob(expected, 2.5)
    under_25 = round(1.0 - over_25, 4)
    over_25  = round(over_25, 4)
    return {
        "expected_goals":       round(expected, 4),
        "over_25_probability":  over_25,
        "under_25_probability": under_25,
        "most_likely_range":    _most_likely_goals_range(expected),
        "confidence_score":     round(max(over_25, under_25), 4),
        "model_version":        registry.manifest_version,
        "generated_at":         datetime.now(timezone.utc),
    }


def _format_corners(registry, outputs) -> dict:
    expected = float(outputs[0].flatten()[0])
    over_9   = _poisson_over_prob(expected, 9.0)
    under_9  = round(1.0 - over_9, 4)
    over_9   = round(over_9, 4)
    return {
        "expected_corners":    round(expected, 4),
        "over_9_probability":  over_9,
        "under_9_probability": under_9,
        "confidence_score":    round(max(over_9, under_9), 4),
        "model_version":       registry.manifest_version,
        "generated_at":        datetime.now(timezone.utc),
    }


def _format_cards(registry, outputs_y, outputs_r) -> dict:
    exp_yellow = float(outputs_y[0].flatten()[0])
    exp_red    = float(outputs_r[0].flatten()[0])
    over_3_y   = _poisson_over_prob(exp_yellow, 3.0)
    under_3_y  = round(1.0 - over_3_y, 4)
    over_3_y   = round(over_3_y, 4)
    return {
        "expected_yellow_cards":      round(exp_yellow, 4),
        "expected_red_cards":         round(exp_red, 4),
        "over_3_yellow_probability":  over_3_y,
        "under_3_yellow_probability": under_3_y,
        "confidence_score":           round(max(over_3_y, under_3_y), 4),
        "model_version":              registry.manifest_version,
        "generated_at":               datetime.now(timezone.utc),
    }
