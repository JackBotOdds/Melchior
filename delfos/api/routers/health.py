from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    registry = request.app.state.registry
    store    = request.app.state.feature_store

    loaded_models = list(registry._sessions.keys())
    store_ready   = (
        store._team_outcome is not None and
        store._team_sog     is not None
    )

    return {
        "status":        "ok",
        "model_version": registry.manifest_version,
        "models_loaded": loaded_models,
        "store_ready":   store_ready,
    }
