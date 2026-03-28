"""
promote_to_staging.py — Promove os modelos do MLflow Model Registry para stage "Staging".

Executar após validar a paridade ONNX (validate_onnx.py).
Pré-requisito para US-4.4: a API carrega modelos com stage "Staging" ou "Production".

Uso:
  python -m serialization.promote_to_staging
"""

import mlflow
from export_models import REGISTRY_TO_FILE, MLFLOW_URI

mlflow.set_tracking_uri(MLFLOW_URI)


def promote_all():
    client = mlflow.tracking.MlflowClient()
    print("Promovendo modelos para stage 'Staging'...\n")

    for registry_name in REGISTRY_TO_FILE:
        versions = client.get_latest_versions(registry_name, stages=["None"])
        if not versions:
            print(f"  {registry_name:<25} ⚠️  sem versões em stage 'None' — pulando.")
            continue

        for v in versions:
            client.transition_model_version_stage(
                name=registry_name,
                version=v.version,
                stage="Staging",
            )
            print(f"  {registry_name:<25} v{v.version} → Staging  ✅")

    print("\nConcluído. Verifique no MLflow UI → Models.")


if __name__ == "__main__":
    promote_all()
