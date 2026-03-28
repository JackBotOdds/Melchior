"""
app.py — Aplicação FastAPI do Delfos v1.0

Inicialização:
  uvicorn delfos.api.app:app --reload --port 8000

Variáveis de ambiente:
  CORS_ALLOWED_ORIGIN  — origem autorizada (default: http://predictive-service:8080)
  DELFOS_PORT          — porta (usado pelo run_api.sh, default: 8000)
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from delfos.api.routers import betsapi, health, predictions
from delfos.api.services.feature_store import FeatureStore
from delfos.api.services.model_registry import ModelRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = ModelRegistry()
    registry.load_all()
    app.state.registry = registry

    store = FeatureStore()
    store.load()
    app.state.feature_store = store

    yield


app = FastAPI(
    title="Delfos — JackBot ML Service",
    version="1.0.0",
    description="API de inferência preditiva para partidas de futebol.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ALLOWED_ORIGIN", "http://predictive-service:8080")],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(predictions.router, prefix="/v1/predict")
app.include_router(betsapi.router,     prefix="/v1/predict/betsapi")
