"""
test_api.py — Testes da API Delfos (US-4.4)

Todos os testes usam mocks para model_registry e feature_store,
permitindo execução sem artefatos ONNX ou parquets treinados.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from delfos.api.app import app


# ---------------------------------------------------------------------------
# Helpers de mock
# ---------------------------------------------------------------------------

def _mock_registry(loaded: bool = True, version: str = "1.0.0"):
    registry = MagicMock()
    registry.manifest_version = version

    def is_loaded(name):
        return loaded

    def get_feature_names(name):
        names_map = {
            "match_outcome": [
                "ht_goals_diff", "ht_shots_diff", "ht_sog_diff", "ht_fouls_diff",
                "competition_type_Continental", "competition_type_Domestic League",
                "competition_type_World Cup",
            ],
            "total_goals": [
                "ht_shots_home", "ht_shots_away", "ht_sog_home", "ht_sog_away",
                "ht_goals_home", "ht_goals_away",
                "competition_type_Continental", "competition_type_Domestic League",
                "competition_type_World Cup",
            ],
            "corners": [
                "ht_shots_home", "ht_shots_away", "ht_fouls_home", "ht_fouls_away",
                "ht_corners_home", "ht_corners_away",
                "competition_type_Continental", "competition_type_Domestic League",
                "competition_type_World Cup",
            ],
            "yellow_cards": [
                "ht_fouls_home", "ht_fouls_away",
                "ht_yellow_cards_home", "ht_yellow_cards_away",
                "competition_type_Continental", "competition_type_Domestic League",
                "competition_type_World Cup",
            ],
            "red_cards": [
                "ht_fouls_home", "ht_fouls_away",
                "ht_yellow_cards_home", "ht_yellow_cards_away",
                "competition_type_Continental", "competition_type_Domestic League",
                "competition_type_World Cup",
            ],
        }
        return names_map.get(name, [])

    def get_session(name):
        session = MagicMock()
        if name == "match_outcome":
            # Classificador: [labels, ZipMap probs]
            session.get_inputs.return_value = [MagicMock(name="float_input")]
            session.run.return_value = [
                np.array([0]),
                [{0: 0.55, 1: 0.25, 2: 0.20}],
            ]
        else:
            # Regressor: [predictions]
            session.get_inputs.return_value = [MagicMock(name="float_input")]
            session.run.return_value = [np.array([[2.7]])]
        return session

    registry.is_loaded.side_effect = is_loaded
    registry.get_feature_names.side_effect = get_feature_names
    registry.get_session.side_effect = get_session
    registry._sessions = {k: True for k in ["match_outcome","total_goals","corners","yellow_cards","red_cards"]} if loaded else {}
    return registry


def _mock_store(found: bool = True):
    store = MagicMock()

    row_outcome = pd.Series({
        "competition_type":     "World Cup",
        "ht_goals_diff":        1.2,
        "ht_shots_diff":        0.5,
        "ht_sog_diff":          0.3,
        "ht_fouls_diff":       -0.1,
        "ht_shots_home":        2.0,
        "ht_shots_away":        1.5,
        "ht_fouls_home":        1.0,
        "ht_fouls_away":        0.8,
        "ht_corners_home":      0.5,
        "ht_corners_away":      0.3,
        "ht_yellow_cards_home": 0.2,
        "ht_yellow_cards_away": 0.1,
    })
    row_sog = pd.Series({
        "competition_type": "World Cup",
        "ht_shots_home":    2.0,
        "ht_shots_away":    1.5,
        "ht_sog_home":      1.0,
        "ht_sog_away":      0.7,
        "ht_goals_home":    0.5,
        "ht_goals_away":    0.2,
    })

    store.get_team_outcome.return_value = row_outcome if found else None
    store.get_team_sog.return_value     = row_sog     if found else None
    store._team_outcome = MagicMock() if found else None
    store._team_sog     = MagicMock() if found else None
    return store


# ---------------------------------------------------------------------------
# Fixture: client com mocks injetados
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    with TestClient(app) as c:
        app.state.registry      = _mock_registry()
        app.state.feature_store = _mock_store()
        yield c


@pytest.fixture
def client_not_found():
    with TestClient(app) as c:
        app.state.registry      = _mock_registry()
        app.state.feature_store = _mock_store(found=False)
        yield c


@pytest.fixture
def client_model_down():
    with TestClient(app) as c:
        app.state.registry      = _mock_registry(loaded=False)
        app.state.feature_store = _mock_store()
        yield c


# ---------------------------------------------------------------------------
# CA-US-4.4.1: GET /health
# ---------------------------------------------------------------------------

def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "model_version" in r.json()


# ---------------------------------------------------------------------------
# CA-US-4.4.2: POST /v1/predict/match-outcome
# ---------------------------------------------------------------------------

def test_match_outcome_schema_valid(client):
    r = client.post("/v1/predict/match-outcome", json={"match_id": "3788741"})
    assert r.status_code == 200
    body = r.json()
    for field in ["home_win_probability", "draw_probability", "away_win_probability",
                  "favorite_outcome", "confidence_score", "model_version", "generated_at"]:
        assert field in body, f"Campo ausente: {field}"


def test_probabilities_sum_to_one(client):
    r = client.post("/v1/predict/match-outcome", json={"match_id": "3788741"})
    assert r.status_code == 200
    body  = r.json()
    total = body["home_win_probability"] + body["draw_probability"] + body["away_win_probability"]
    assert abs(total - 1.0) < 0.001, f"Soma = {total}, esperado 1.0"


def test_favorite_outcome_is_valid(client):
    r = client.post("/v1/predict/match-outcome", json={"match_id": "3788741"})
    assert r.json()["favorite_outcome"] in ("HOME", "DRAW", "AWAY")


# ---------------------------------------------------------------------------
# CA-US-4.4.3: POST /v1/predict/total-goals
# ---------------------------------------------------------------------------

def test_total_goals_schema_valid(client):
    r = client.post("/v1/predict/total-goals", json={"match_id": "3788741"})
    assert r.status_code == 200
    body = r.json()
    for field in ["expected_goals", "over_25_probability", "under_25_probability",
                  "most_likely_range", "confidence_score", "model_version", "generated_at"]:
        assert field in body

def test_total_goals_over_under_sum(client):
    r = client.post("/v1/predict/total-goals", json={"match_id": "3788741"})
    body  = r.json()
    total = body["over_25_probability"] + body["under_25_probability"]
    assert abs(total - 1.0) < 0.001


# ---------------------------------------------------------------------------
# CA-US-4.4.4: POST /v1/predict/corners
# ---------------------------------------------------------------------------

def test_corners_schema_valid(client):
    r = client.post("/v1/predict/corners", json={"match_id": "3788741"})
    assert r.status_code == 200
    body = r.json()
    for field in ["expected_corners", "over_9_probability", "under_9_probability",
                  "confidence_score", "model_version"]:
        assert field in body


# ---------------------------------------------------------------------------
# CA-US-4.4.5: POST /v1/predict/cards
# ---------------------------------------------------------------------------

def test_cards_schema_valid(client):
    r = client.post("/v1/predict/cards", json={"match_id": "3788741"})
    assert r.status_code == 200
    body = r.json()
    for field in ["expected_yellow_cards", "expected_red_cards",
                  "over_3_yellow_probability", "under_3_yellow_probability",
                  "confidence_score", "model_version"]:
        assert field in body


# ---------------------------------------------------------------------------
# CA-US-4.4.6: request aceita match_id + season
# ---------------------------------------------------------------------------

def test_request_accepts_match_id_and_season(client):
    r = client.post("/v1/predict/match-outcome",
                    json={"match_id": "3788741", "season": "2022"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# CA-US-4.4.7: tratamento de erros
# ---------------------------------------------------------------------------

def test_invalid_match_id_returns_400(client):
    r = client.post("/v1/predict/match-outcome", json={"match_id": "abc"})
    assert r.status_code == 400


def test_match_not_found_returns_404(client_not_found):
    r = client_not_found.post("/v1/predict/match-outcome", json={"match_id": "9999999"})
    assert r.status_code == 404


def test_model_not_loaded_returns_503(client_model_down):
    r = client_model_down.post("/v1/predict/match-outcome", json={"match_id": "3788741"})
    assert r.status_code == 503


def test_missing_match_id_returns_422(client):
    r = client.post("/v1/predict/match-outcome", json={})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# CA-US-4.4.8: CORS
# ---------------------------------------------------------------------------

def test_cors_blocks_unauthorized_origin(client):
    r = client.options(
        "/v1/predict/match-outcome",
        headers={
            "Origin": "http://evil-attacker.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    allowed = r.headers.get("access-control-allow-origin", "")
    assert "evil-attacker.com" not in allowed
