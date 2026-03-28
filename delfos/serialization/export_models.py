"""
export_models.py — Serialização dos modelos Delfos v1.0 para formato ONNX.

Responsabilidades:
  - Carregar cada modelo do MLflow Model Registry (stage "None" → mais recente)
  - Converter para ONNX via skl2onnx usando n_features_in_ do modelo
  - Incluir feature_names no manifest para que a API saiba a ordem esperada das colunas
  - Gerar model_manifest.json como contrato para a API (US-4.4)

Nota sobre o scaler:
  O StandardScaler é aplicado no ETL (preprocessor.py) antes de salvar os parquets.
  Os modelos foram treinados com dados já normalizados. Portanto, os arquivos ONNX
  esperam entrada pré-normalizada. A API carrega os features diretamente dos parquets
  (que já estão normalizados), não sendo necessário incluir o scaler no ONNX.
  Na integração com BetsAPI (sprint futura), o scaler deverá ser incluído no pipeline.

Uso:
  python -m delfos.serialization.export_models
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

ROOT_DIR = Path(__file__).resolve().parents[2]

# MLflow local (SQLite) — consistente com common.py
MLFLOW_URI = f"sqlite:///{ROOT_DIR / 'mlflow.db'}"
mlflow.set_tracking_uri(MLFLOW_URI)

ONNX_DIR = ROOT_DIR / "models" / "onnx"
ONNX_DIR.mkdir(parents=True, exist_ok=True)

# Mapeamento: nome no MLflow Registry → nome do arquivo .onnx
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


def _load_model_from_registry(registry_name: str):
    client = mlflow.tracking.MlflowClient()
    versions = client.get_latest_versions(registry_name, stages=["None"])

    if not versions:
        raise RuntimeError(
            f"Nenhuma versão encontrada para '{registry_name}' no stage 'None'.\n"
            "Execute os scripts de treinamento antes de exportar."
        )

    latest = versions[0]
    model_uri = f"models:/{registry_name}/{latest.version}"
    model = mlflow.sklearn.load_model(model_uri)
    print(f"  [load] {registry_name} v{latest.version}  run_id={latest.run_id[:8]}")
    return model, latest


def _convert_to_onnx(model, registry_name: str) -> bytes:
    if not hasattr(model, "n_features_in_"):
        raise AttributeError(
            f"Modelo '{registry_name}' não tem n_features_in_. "
            "Certifique-se de que o modelo foi ajustado antes de exportar."
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
    client = mlflow.tracking.MlflowClient()
    run = client.get_run(run_id)
    return dict(run.data.metrics)


def _get_feature_names(model) -> list:
    """Extrai os nomes das features na ordem usada durante o treino."""
    if hasattr(model, "feature_names_in_"):
        return model.feature_names_in_.tolist()
    return []


def export_model(registry_name: str, file_prefix: str) -> dict:
    model, version_info = _load_model_from_registry(registry_name)
    onnx_bytes = _convert_to_onnx(model, registry_name)

    onnx_path = ONNX_DIR / f"{file_prefix}_v{VERSION}.onnx"
    onnx_path.write_bytes(onnx_bytes)
    print(f"  [save] {onnx_path.relative_to(ROOT_DIR)}")

    metrics = _collect_metrics(registry_name, version_info.run_id)
    feature_names = _get_feature_names(model)

    return {
        "name":           file_prefix,
        "registry_name":  registry_name,
        "version":        VERSION,
        "onnx_path":      str(onnx_path.relative_to(ROOT_DIR)).replace("\\", "/"),
        "n_features":     model.n_features_in_,
        "feature_names":  feature_names,
        "mlflow_run_id":  version_info.run_id,
        "metrics":        metrics,
        "generated_at":   datetime.now(timezone.utc).isoformat(),
    }


def build_manifest():
    print("=" * 60)
    print("Exportando modelos para ONNX — Delfos v1.0")
    print("=" * 60)

    generated_at = datetime.now(timezone.utc).isoformat()
    entries = []
    errors  = []

    for registry_name, file_prefix in REGISTRY_TO_FILE.items():
        print(f"\n-> {registry_name}")
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
    print(f"\n  [manifest] {manifest_path.relative_to(ROOT_DIR)}")

    if errors:
        print(f"\n  [AVISO] {len(errors)} modelo(s) com erro.")
    else:
        print(f"\n  [OK] {len(entries)} modelos exportados com sucesso.")

    return manifest


if __name__ == "__main__":
    build_manifest()
