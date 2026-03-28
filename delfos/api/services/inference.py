"""
inference.py — Executa inferência ONNX e formata as respostas dos endpoints.

Fluxo por predição:
  1. Busca features do match_id no FeatureStore (dados já normalizados)
  2. Aplica get_dummies para competition_type
  3. Alinha colunas com os feature_names do modelo (ordem do treino)
  4. Executa sessão ONNX
  5. Formata response com campos derivados (over/under via Poisson, confidence)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from scipy.stats import poisson

if TYPE_CHECKING:
    from delfos.api.services.feature_store import FeatureStore
    from delfos.api.services.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

# Features brutas (antes do get_dummies) por endpoint
_MATCH_OUTCOME_FEATS = ["ht_goals_diff", "ht_shots_diff", "ht_sog_diff", "ht_fouls_diff"]
_TOTAL_GOALS_FEATS   = ["ht_shots_home", "ht_shots_away", "ht_sog_home", "ht_sog_away",
                        "ht_goals_home", "ht_goals_away"]
_CORNERS_FEATS       = ["ht_shots_home", "ht_shots_away", "ht_fouls_home", "ht_fouls_away",
                        "ht_corners_home", "ht_corners_away"]
_CARDS_FEATS         = ["ht_fouls_home", "ht_fouls_away",
                        "ht_yellow_cards_home", "ht_yellow_cards_away"]


def _build_input(row: pd.Series, numeric_feats: list[str], feature_names: list[str]) -> np.ndarray:
    """
    Monta o vetor de entrada para o modelo ONNX.
    Aplica get_dummies em competition_type e alinha com feature_names do modelo.
    """
    data = {col: row[col] for col in numeric_feats if col in row.index}
    data["competition_type"] = row.get("competition_type", "Other")

    df = pd.DataFrame([data])
    df = pd.get_dummies(df, columns=["competition_type"])

    if feature_names:
        df = df.reindex(columns=feature_names, fill_value=0)

    return df.values.astype(np.float32)


def _run_session(session, X: np.ndarray):
    """Executa sessão ONNX e retorna outputs brutos."""
    input_name = session.get_inputs()[0].name
    return session.run(None, {input_name: X})


def _extract_classifier_probs(outputs) -> list[float]:
    """
    Extrai probabilidades do output ONNX de um classificador.
    Handles ZipMap (list of dicts) ou array direto.
    """
    prob_output = outputs[1]

    # ZipMap: list of dicts {class_id: prob}
    if isinstance(prob_output, list) and isinstance(prob_output[0], dict):
        probs_dict = prob_output[0]
        return [probs_dict[k] for k in sorted(probs_dict.keys())]

    # Array: shape (1, n_classes)
    arr = np.array(prob_output)
    if arr.ndim == 2:
        return arr[0].tolist()
    return arr.tolist()


def _poisson_over_prob(lam: float, threshold: float) -> float:
    """P(X > threshold) usando distribuição de Poisson com média lam."""
    lam = max(lam, 0.01)
    k = int(threshold)
    return float(1.0 - poisson.cdf(k, lam))


def _most_likely_goals_range(expected: float) -> str:
    if expected < 1.5:
        return "0-1"
    elif expected < 3.5:
        return "2-3"
    return "4+"


def predict_match_outcome(
    match_id: int,
    registry: "ModelRegistry",
    store: "FeatureStore",
) -> dict:
    if not registry.is_loaded("match_outcome"):
        raise RuntimeError("Modelo match_outcome não carregado.")

    row = store.get_team_outcome(match_id)
    if row is None:
        raise KeyError(f"match_id={match_id} não encontrado no dataset.")

    X = _build_input(row, _MATCH_OUTCOME_FEATS, registry.get_feature_names("match_outcome"))
    outputs = _run_session(registry.get_session("match_outcome"), X)
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


def predict_total_goals(
    match_id: int,
    registry: "ModelRegistry",
    store: "FeatureStore",
) -> dict:
    if not registry.is_loaded("total_goals"):
        raise RuntimeError("Modelo total_goals não carregado.")

    row = store.get_team_sog(match_id)
    if row is None:
        raise KeyError(f"match_id={match_id} não encontrado no dataset.")

    X = _build_input(row, _TOTAL_GOALS_FEATS, registry.get_feature_names("total_goals"))
    outputs = _run_session(registry.get_session("total_goals"), X)
    expected = float(outputs[0].flatten()[0])

    over_25  = _poisson_over_prob(expected, 2.5)
    under_25 = round(1.0 - over_25, 4)
    over_25  = round(over_25, 4)

    return {
        "expected_goals":      round(expected, 4),
        "over_25_probability": over_25,
        "under_25_probability": under_25,
        "most_likely_range":   _most_likely_goals_range(expected),
        "confidence_score":    round(max(over_25, under_25), 4),
        "model_version":       registry.manifest_version,
        "generated_at":        datetime.now(timezone.utc),
    }


def predict_corners(
    match_id: int,
    registry: "ModelRegistry",
    store: "FeatureStore",
) -> dict:
    if not registry.is_loaded("corners"):
        raise RuntimeError("Modelo corners não carregado.")

    row = store.get_team_outcome(match_id)
    if row is None:
        raise KeyError(f"match_id={match_id} não encontrado no dataset.")

    X = _build_input(row, _CORNERS_FEATS, registry.get_feature_names("corners"))
    outputs = _run_session(registry.get_session("corners"), X)
    expected = float(outputs[0].flatten()[0])

    over_9  = _poisson_over_prob(expected, 9.0)
    under_9 = round(1.0 - over_9, 4)
    over_9  = round(over_9, 4)

    return {
        "expected_corners":  round(expected, 4),
        "over_9_probability":  over_9,
        "under_9_probability": under_9,
        "confidence_score":  round(max(over_9, under_9), 4),
        "model_version":     registry.manifest_version,
        "generated_at":      datetime.now(timezone.utc),
    }


def predict_cards(
    match_id: int,
    registry: "ModelRegistry",
    store: "FeatureStore",
) -> dict:
    if not registry.is_loaded("yellow_cards") or not registry.is_loaded("red_cards"):
        raise RuntimeError("Modelos yellow_cards e/ou red_cards não carregados.")

    row = store.get_team_outcome(match_id)
    if row is None:
        raise KeyError(f"match_id={match_id} não encontrado no dataset.")

    X_yellow = _build_input(row, _CARDS_FEATS, registry.get_feature_names("yellow_cards"))
    X_red    = _build_input(row, _CARDS_FEATS, registry.get_feature_names("red_cards"))

    exp_yellow = float(_run_session(registry.get_session("yellow_cards"), X_yellow)[0].flatten()[0])
    exp_red    = float(_run_session(registry.get_session("red_cards"),    X_red)[0].flatten()[0])

    over_3_y  = _poisson_over_prob(exp_yellow, 3.0)
    under_3_y = round(1.0 - over_3_y, 4)
    over_3_y  = round(over_3_y, 4)

    return {
        "expected_yellow_cards":     round(exp_yellow, 4),
        "expected_red_cards":        round(exp_red, 4),
        "over_3_yellow_probability":  over_3_y,
        "under_3_yellow_probability": under_3_y,
        "confidence_score":          round(max(over_3_y, under_3_y), 4),
        "model_version":             registry.manifest_version,
        "generated_at":              datetime.now(timezone.utc),
    }
