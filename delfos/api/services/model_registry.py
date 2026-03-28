"""
model_registry.py — Carrega modelos ONNX e o manifest na inicialização da API.

Cada sessão ONNX é mantida em memória para garantir latência baixa (eager loading).
Se um modelo não for encontrado, o endpoint retorna 503 em vez de falhar na inicialização.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import onnxruntime as rt

ROOT_DIR   = Path(__file__).resolve().parents[4]
ONNX_DIR   = ROOT_DIR / "models" / "onnx"
MANIFEST   = ONNX_DIR / "model_manifest.json"

logger = logging.getLogger(__name__)

# Modelos utilizados pelos endpoints da API
API_MODELS = {
    "match_outcome",
    "total_goals",
    "corners",
    "yellow_cards",
    "red_cards",
}


class ModelRegistry:
    def __init__(self):
        self._sessions: dict[str, rt.InferenceSession] = {}
        self._feature_names: dict[str, list[str]] = {}
        self.manifest_version = "unknown"

    def load_all(self):
        if not MANIFEST.exists():
            logger.warning(
                "model_manifest.json não encontrado em %s. "
                "Execute export_models.py após o treinamento.", ONNX_DIR
            )
            return

        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.manifest_version = manifest.get("version", "unknown")

        for entry in manifest.get("models", []):
            name = entry["name"]
            if name not in API_MODELS:
                continue

            onnx_path = ROOT_DIR / entry["onnx_path"]
            if not onnx_path.exists():
                logger.warning("ONNX não encontrado: %s — endpoint retornará 503.", onnx_path)
                continue

            try:
                self._sessions[name] = rt.InferenceSession(str(onnx_path))
                self._feature_names[name] = entry.get("feature_names", [])
                logger.info("Modelo carregado: %s (n_features=%s)", name, entry.get("n_features"))
            except Exception as exc:
                logger.error("Falha ao carregar %s: %s", name, exc)

        loaded = len(self._sessions)
        logger.info("ModelRegistry: %d/%d modelos carregados.", loaded, len(API_MODELS))

    def get_session(self, name: str) -> Optional[rt.InferenceSession]:
        return self._sessions.get(name)

    def get_feature_names(self, name: str) -> list[str]:
        return self._feature_names.get(name, [])

    def is_loaded(self, name: str) -> bool:
        return name in self._sessions
