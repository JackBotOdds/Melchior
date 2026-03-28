#!/usr/bin/env bash
# run_api.sh — Inicia a API de inferência Delfos
set -euo pipefail

cd "$(dirname "$0")"

# Carrega variáveis do .env se existir
if [ -f ".env" ]; then
    set -a && source .env && set +a
fi

PYTHON="${PYTHON:-python}"
PORT="${DELFOS_PORT:-8000}"
HOST="${DELFOS_HOST:-0.0.0.0}"
RELOAD="${DELFOS_RELOAD:-false}"

echo "=== Delfos API v1.0 ==="

# Verifica dependências
echo "[1/3] Verificando dependências..."
$PYTHON -m pip install -r requirements-ml.txt --quiet

# Verifica artefatos ONNX — exporta automaticamente se modelos já foram treinados
echo "[2/3] Verificando artefatos ONNX..."
MANIFEST="models/onnx/model_manifest.json"

_models_trained() {
    $PYTHON -c "
import sys
try:
    import mlflow
    mlflow.set_tracking_uri('sqlite:///mlflow.db')
    client = mlflow.tracking.MlflowClient()
    names = [m.name for m in client.search_registered_models()]
    needed = {'match-outcome', 'total-goals', 'corners', 'yellow-cards', 'red-cards'}
    found  = needed & set(names)
    print(len(found))
except Exception:
    print(0)
" 2>/dev/null || echo 0
}

if [ ! -f "$MANIFEST" ]; then
    TRAINED=$(_models_trained)
    if [ "$TRAINED" -gt 0 ] 2>/dev/null; then
        echo "        Manifest ausente — $TRAINED modelo(s) encontrado(s) no MLflow. Exportando..."
        $PYTHON -m delfos.serialization.export_models
    else
        echo ""
        echo "[AVISO] Nenhum modelo treinado encontrado."
        echo "        Execute primeiro: python run_pipeline.py"
        echo ""
        read -r -p "Continuar sem modelos? (s/N) " resp
        [[ "${resp,,}" == "s" ]] || { echo "Abortado."; exit 1; }
    fi
else
    MODEL_COUNT=$($PYTHON -c "import json; m=json.load(open('$MANIFEST')); print(len(m.get('models', [])))" 2>/dev/null || echo "?")
    echo "        Manifest OK — $MODEL_COUNT modelo(s) registrado(s)"
fi

# Inicia servidor
echo "[3/3] Iniciando uvicorn em $HOST:$PORT ..."
echo ""

RELOAD_FLAG=""
[[ "$RELOAD" == "true" ]] && RELOAD_FLAG="--reload"

$PYTHON -m uvicorn delfos.api.app:app \
    --host "$HOST" \
    --port "$PORT" \
    $RELOAD_FLAG
