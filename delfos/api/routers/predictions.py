from fastapi import APIRouter, HTTPException, Request

from delfos.api.schemas.request import PredictionRequest
from delfos.api.schemas.response import (
    MatchOutcomeResponse,
    TotalGoalsResponse,
    CornersResponse,
    CardsResponse,
)
from delfos.api.services import inference

router = APIRouter()


def _parse_match_id(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"match_id deve ser numérico, recebido: '{raw}'")


def _handle(fn, match_id: int, registry, store):
    try:
        return fn(match_id, registry, store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/match-outcome", response_model=MatchOutcomeResponse)
async def predict_match_outcome(req: PredictionRequest, request: Request):
    mid      = _parse_match_id(req.match_id)
    registry = request.app.state.registry
    store    = request.app.state.feature_store
    result   = _handle(inference.predict_match_outcome, mid, registry, store)
    return MatchOutcomeResponse(**result)


@router.post("/total-goals", response_model=TotalGoalsResponse)
async def predict_total_goals(req: PredictionRequest, request: Request):
    mid      = _parse_match_id(req.match_id)
    registry = request.app.state.registry
    store    = request.app.state.feature_store
    result   = _handle(inference.predict_total_goals, mid, registry, store)
    return TotalGoalsResponse(**result)


@router.post("/corners", response_model=CornersResponse)
async def predict_corners(req: PredictionRequest, request: Request):
    mid      = _parse_match_id(req.match_id)
    registry = request.app.state.registry
    store    = request.app.state.feature_store
    result   = _handle(inference.predict_corners, mid, registry, store)
    return CornersResponse(**result)


@router.post("/cards", response_model=CardsResponse)
async def predict_cards(req: PredictionRequest, request: Request):
    mid      = _parse_match_id(req.match_id)
    registry = request.app.state.registry
    store    = request.app.state.feature_store
    result   = _handle(inference.predict_cards, mid, registry, store)
    return CardsResponse(**result)
