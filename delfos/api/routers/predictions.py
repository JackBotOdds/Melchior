from fastapi import APIRouter, HTTPException, Request

from delfos.api.schemas.request import LiveMatchRequest, PredictionRequest
from delfos.api.schemas.response import (
    CardsResponse,
    CornersResponse,
    MatchOutcomeResponse,
    TotalGoalsResponse,
)
from delfos.api.services import inference

router = APIRouter()


def _parse_match_id(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"match_id deve ser numérico, recebido: '{raw}'")


def _handle(fn, *args):
    try:
        return fn(*args)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ── Endpoints históricos (match_id) ──────────────────────────────────────────

@router.post("/match-outcome", response_model=MatchOutcomeResponse)
async def predict_match_outcome(req: PredictionRequest, request: Request):
    mid = _parse_match_id(req.match_id)
    return MatchOutcomeResponse(**_handle(
        inference.predict_match_outcome, mid,
        request.app.state.registry, request.app.state.feature_store,
    ))


@router.post("/total-goals", response_model=TotalGoalsResponse)
async def predict_total_goals(req: PredictionRequest, request: Request):
    mid = _parse_match_id(req.match_id)
    return TotalGoalsResponse(**_handle(
        inference.predict_total_goals, mid,
        request.app.state.registry, request.app.state.feature_store,
    ))


@router.post("/corners", response_model=CornersResponse)
async def predict_corners(req: PredictionRequest, request: Request):
    mid = _parse_match_id(req.match_id)
    return CornersResponse(**_handle(
        inference.predict_corners, mid,
        request.app.state.registry, request.app.state.feature_store,
    ))


@router.post("/cards", response_model=CardsResponse)
async def predict_cards(req: PredictionRequest, request: Request):
    mid = _parse_match_id(req.match_id)
    return CardsResponse(**_handle(
        inference.predict_cards, mid,
        request.app.state.registry, request.app.state.feature_store,
    ))


# ── Endpoints ao vivo / HT (features brutas via BetsAPI — chamar no intervalo) ─

@router.post("/live/match-outcome", response_model=MatchOutcomeResponse)
async def predict_match_outcome_live(req: LiveMatchRequest, request: Request):
    return MatchOutcomeResponse(**_handle(
        inference.predict_match_outcome_live, req,
        request.app.state.registry, request.app.state.feature_store,
    ))


@router.post("/live/total-goals", response_model=TotalGoalsResponse)
async def predict_total_goals_live(req: LiveMatchRequest, request: Request):
    return TotalGoalsResponse(**_handle(
        inference.predict_total_goals_live, req,
        request.app.state.registry, request.app.state.feature_store,
    ))


@router.post("/live/corners", response_model=CornersResponse)
async def predict_corners_live(req: LiveMatchRequest, request: Request):
    return CornersResponse(**_handle(
        inference.predict_corners_live, req,
        request.app.state.registry, request.app.state.feature_store,
    ))


@router.post("/live/cards", response_model=CardsResponse)
async def predict_cards_live(req: LiveMatchRequest, request: Request):
    return CardsResponse(**_handle(
        inference.predict_cards_live, req,
        request.app.state.registry, request.app.state.feature_store,
    ))
