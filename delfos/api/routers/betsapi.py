"""
betsapi.py — Endpoints de predição via BetsAPI (dados ao vivo).

O Java envia apenas o fixture ID (fi) da BetsAPI. O Delfos:
  1. Busca as estatísticas ao vivo na BetsAPI
  2. Valida que o jogo está no 1º tempo ou intervalo
  3. Mapeia os campos para LiveMatchRequest
  4. Normaliza via scaler e executa os modelos HT

Endpoints:
  POST /v1/predict/betsapi/match-outcome
  POST /v1/predict/betsapi/total-goals
  POST /v1/predict/betsapi/corners
  POST /v1/predict/betsapi/cards

Body: {"fi": "12345", "competition_type": "Domestic League"}
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from delfos.api.schemas.response import (
    CardsResponse,
    CornersResponse,
    MatchOutcomeResponse,
    TotalGoalsResponse,
)
from delfos.api.services import inference
from delfos.api.services.betsapi_client import (
    BetsAPIMatchNotFoundError,
    BetsAPIUnavailableError,
    fetch_inplay_stats,
)
from delfos.api.services.betsapi_mapper import (
    assert_halftime_window,
    map_inplay_stats_to_request,
)

router = APIRouter()


class BetsAPIRequest(BaseModel):
    fi: str
    competition_type: str = "Domestic League"


async def _fetch_and_map(req: BetsAPIRequest):
    """Busca stats da BetsAPI, valida o período e retorna LiveMatchRequest."""
    try:
        results = await fetch_inplay_stats(req.fi)
    except BetsAPIUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except BetsAPIMatchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        assert_halftime_window(results)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return map_inplay_stats_to_request(results, req.competition_type)


def _handle_inference(fn, *args):
    try:
        return fn(*args)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/match-outcome", response_model=MatchOutcomeResponse)
async def predict_betsapi_match_outcome(req: BetsAPIRequest, request: Request):
    live_req = await _fetch_and_map(req)
    return MatchOutcomeResponse(**_handle_inference(
        inference.predict_match_outcome_live, live_req,
        request.app.state.registry, request.app.state.feature_store,
    ))


@router.post("/total-goals", response_model=TotalGoalsResponse)
async def predict_betsapi_total_goals(req: BetsAPIRequest, request: Request):
    live_req = await _fetch_and_map(req)
    return TotalGoalsResponse(**_handle_inference(
        inference.predict_total_goals_live, live_req,
        request.app.state.registry, request.app.state.feature_store,
    ))


@router.post("/corners", response_model=CornersResponse)
async def predict_betsapi_corners(req: BetsAPIRequest, request: Request):
    live_req = await _fetch_and_map(req)
    return CornersResponse(**_handle_inference(
        inference.predict_corners_live, live_req,
        request.app.state.registry, request.app.state.feature_store,
    ))


@router.post("/cards", response_model=CardsResponse)
async def predict_betsapi_cards(req: BetsAPIRequest, request: Request):
    live_req = await _fetch_and_map(req)
    return CardsResponse(**_handle_inference(
        inference.predict_cards_live, live_req,
        request.app.state.registry, request.app.state.feature_store,
    ))
