"""
validate_onnx.py — Validação de paridade sklearn ↔ ONNX.

Para cada modelo exportado, compara as predições do modelo sklearn
(carregado do MLflow) com as predições do .onnx via onnxruntime.

Critério de aceite CA-US-4.3.3: divergência máxima < 0.001 em 100 amostras.

Uso:
  python -m serialization.validate_onnx
  ou
  python delfos/serialization/validate_onnx.py
"""

import json
import sys
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import onnxruntime as rt

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
MLFLOW_URI      = "http://localhost:5000"
MAX_DIVERGENCE  = 0.001   # CA-US-4.3.3
N_SAMPLES       = 100
MANIFEST_PATH   = Path(__file__).resolve().parents[2] / "models" / "onnx" / "model_manifest.json"

mlflow.set_tracking_uri(MLFLOW_URI)


# ---------------------------------------------------------------------------
# Funções de validação
# ---------------------------------------------------------------------------

def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest não encontrado: {MANIFEST_PATH}\n"
            "Execute export_models.py antes de validar."
        )
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _predict_sklearn(registry_name: str, X: np.ndarray) -> np.ndarray:
    model = mlflow.sklearn.load_model(f"models:/{registry_name}/latest")
    preds = model.predict(X)
    return preds.flatten().astype(np.float64)


def _predict_onnx(onnx_path: str, X: np.ndarray) -> np.ndarray:
    sess     = rt.InferenceSession(onnx_path)
    inp_name = sess.get_inputs()[0].name
    preds    = sess.run(None, {inp_name: X.astype(np.float32)})[0]
    return preds.flatten().astype(np.float64)


def validate_model(entry: dict) -> bool:
    """
    Valida um único modelo. Retorna True se passou, False se falhou.
    n_features é lido do manifest (valor real após one-hot encoding).
    """
    registry_name = entry["registry_name"]
    onnx_path     = str(Path(__file__).parents[2] / entry["onnx_path"])
    n_features    = entry["n_features"]

    if not Path(onnx_path).exists():
        print(f"  {registry_name:<25} ❌ arquivo .onnx não encontrado: {onnx_path}")
        return False

    rng = np.random.default_rng(seed=42)
    X   = rng.random((N_SAMPLES, n_features), dtype=np.float32)

    try:
        pred_sk   = _predict_sklearn(registry_name, X)
        pred_onnx = _predict_onnx(onnx_path, X)

        divergence = float(np.max(np.abs(pred_sk - pred_onnx)))
        passed     = divergence <= MAX_DIVERGENCE
        status     = "✅ OK" if passed else "❌ FALHA"

        print(
            f"  {registry_name:<25} {status}  "
            f"divergência_max={divergence:.6f}  "
            f"(limite={MAX_DIVERGENCE})"
        )
        return passed

    except Exception as exc:
        print(f"  {registry_name:<25} ❌ ERRO — {exc}")
        return False


def run_validation() -> bool:
    """
    Valida todos os modelos listados no manifest.
    Retorna True se todos passaram; False caso contrário.
    """
    print("=" * 65)
    print("Validação de paridade sklearn ↔ ONNX — Delfos v1.0")
    print("=" * 65)

    manifest = _load_manifest()
    models   = manifest.get("models", [])

    if not models:
        print("  [AVISO] Nenhum modelo no manifest. Execute export_models.py primeiro.")
        return False

    results = []
    for entry in models:
        results.append(validate_model(entry))

    passed = sum(results)
    total  = len(results)
    print(f"\n  Resultado: {passed}/{total} modelos validados com sucesso.")

    if passed < total:
        print(
            "  [FALHA] Um ou mais modelos não atendem ao CA-US-4.3.3.\n"
            "  Verifique o log acima e re-execute export_models.py se necessário."
        )
        return False

    print("  [OK] CA-US-4.3.3 APROVADO — todos os modelos dentro da tolerância.")
    return True


if __name__ == "__main__":
    ok = run_validation()
    sys.exit(0 if ok else 1)
