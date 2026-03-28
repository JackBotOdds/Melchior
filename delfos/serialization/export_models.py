"""
export_models.py — Serialização dos modelos Delfos v1.0 para formato ONNX.

Responsabilidades:
  - Carregar cada modelo do MLflow Model Registry (stage "None" → mais recente)
  - Converter para ONNX via skl2onnx usando n_features_in_ do modelo
  - Gerar model_manifest.json como contrato para a API (US-4.4)

Correções aplicadas em relação ao spec US-4.3:
  - Nomes no registry usam hífens (ex: "match-outcome"), igual ao US-4.2
  - n_features inferido de model.n_features_in_ (dinâmico — respeita one-hot encoding)
  - Pacote onnx adicionado ao requirements-ml.txt

Uso:
  python -m serialization.export_models
  ou
  python delfos/serialization/export_models.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
MLFLOW_URI = "http://localhost:5000"
mlflow.set_tracking_uri(MLFLOW_URI)

ONNX_DIR = Path(__file__).resolve().parents[2] / "models" / "onnx"
ONNX_DIR.mkdir(parents=True, exist_ok=True)

# Mapeamento: nome no MLflow Registry → nome do arquivo .onnx
# Chave: nome exato usado em mlflow.register_model() no common.py (com hífens)
# Valor: prefixo do arquivo de saída (com underscores, para compatibilidade de paths)
REGISTRY_TO_FILE = {
    "match-outcome":      "match_outcome",
    "total-goals":        "total_goals",
    "goals-distribution": "goals_distribution",
    "corners":            "corners",
    "red-cards":          "red_cards",
    "yellow-cards":       "yellow_cards",
    "player-sog":         "player_sog",
}

VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def _load_model_from_registry(registry_name: str):
    """
    Carrega o modelo sklearn mais recente do MLflow Model Registry.
    Usa stage='None' (modelos recém-registrados em US-4.2, antes da promoção).
    """
    client = mlflow.tracking.MlflowClient()
    versions = client.get_latest_versions(registry_name, stages=["None"])

    if not versions:
        raise RuntimeError(
            f"Nenhuma versão encontrada para '{registry_name}' no stage 'None'.\n"
            "Execute os scripts de treinamento (US-4.2) antes de exportar."
        )

    latest = versions[0]
    model_uri = f"models:/{registry_name}/{latest.version}"
    model = mlflow.sklearn.load_model(model_uri)
    print(f"  [load] {registry_name} v{latest.version}  run_id={latest.run_id[:8]}")
    return model, latest


def _convert_to_onnx(model, registry_name: str) -> bytes:
    """
    Converte o modelo sklearn para ONNX.
    n_features é inferido de model.n_features_in_ para suportar
    o número real de colunas após pd.get_dummies() em US-4.2.
    """
    if not hasattr(model, "n_features_in_"):
        raise AttributeError(
            f"Modelo '{registry_name}' não tem atributo n_features_in_. "
            "Certifique-se de que o modelo foi ajustado (fit) antes de exportar."
        )

    n_features = model.n_features_in_
    initial_type = [("float_input", FloatTensorType([None, n_features]))]

    onnx_model = convert_sklearn(
        model,
        initial_types=initial_type,
        target_opset={"": 17, "ai.onnx.ml": 3},
    )
    print(f"  [onnx] {registry_name}  n_features={n_features}")
    return onnx_model.SerializeToString()


def _collect_metrics(registry_name: str, run_id: str) -> dict:
    """Lê as métricas do run MLflow para incluir no manifest."""
    client = mlflow.tracking.MlflowClient()
    run = client.get_run(run_id)
    return dict(run.data.metrics)


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def export_model(registry_name: str, file_prefix: str) -> dict:
    """
    Carrega, converte e salva um modelo como .onnx.
    Retorna a entrada para o model_manifest.json.
    """
    model, version_info = _load_model_from_registry(registry_name)
    onnx_bytes = _convert_to_onnx(model, registry_name)

    onnx_path = ONNX_DIR / f"{file_prefix}_v{VERSION}.onnx"
    onnx_path.write_bytes(onnx_bytes)
    print(f"  [save] {onnx_path.relative_to(Path(__file__).parents[2])}")

    metrics = _collect_metrics(registry_name, version_info.run_id)

    return {
        "name":          file_prefix,
        "registry_name": registry_name,
        "version":       VERSION,
        "onnx_path":     str(onnx_path.relative_to(Path(__file__).parents[2])),
        "n_features":    model.n_features_in_,
        "mlflow_run_id": version_info.run_id,
        "metrics":       metrics,
        "generated_at":  datetime.now(timezone.utc).isoformat(),
    }


def build_manifest():
    """Exporta todos os modelos e grava o model_manifest.json."""
    print("=" * 60)
    print("Exportando modelos para ONNX — Delfos v1.0")
    print("=" * 60)

    generated_at = datetime.now(timezone.utc).isoformat()
    entries = []
    errors  = []

    for registry_name, file_prefix in REGISTRY_TO_FILE.items():
        print(f"\n→ {registry_name}")
        try:
            entry = export_model(registry_name, file_prefix)
            entries.append(entry)
        except Exception as exc:
            print(f"  [ERRO] {exc}")
            errors.append({"name": registry_name, "error": str(exc)})

    manifest = {
        "version":      VERSION,
        "generated_at": generated_at,
        "models":       entries,
        "errors":       errors,
    }

    manifest_path = ONNX_DIR / "model_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n  [manifest] {manifest_path.relative_to(Path(__file__).parents[2])}")

    if errors:
        print(f"\n  [AVISO] {len(errors)} modelo(s) com erro — ver campo 'errors' no manifest.")
    else:
        print(f"\n  [OK] {len(entries)} modelos exportados com sucesso.")

    return manifest


if __name__ == "__main__":
    build_manifest()
