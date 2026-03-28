#!/usr/bin/env bash
# run_api.sh — Inicia a API de inferência Delfos
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python}"
PORT="${DELFOS_PORT:-8000}"
HOST="${DELFOS_HOST:-0.0.0.0}"
RELOAD="${DELFOS_RELOAD:-false}"

echo "=== Delfos API v1.0 ==="

# Verifica dependências
echo "[1/3] Verificando dependências..."
$PYTHON -m pip install -r requirements-ml.txt --quiet

# Verifica artefatos ONNX
echo "[2/3] Verificando artefatos ONNX..."
MANIFEST="models/onnx/model_manifest.json"

if [ ! -f "$MANIFEST" ]; then
    echo ""
    echo "[AVISO] model_manifest.json não encontrado em models/onnx/"
    echo "        Execute antes: python -m delfos.serialization.export_models"
    echo ""
    read -r -p "Continuar mesmo assim? (s/N) " resp
    [[ "${resp,,}" == "s" ]] || { echo "Abortado."; exit 1; }
else
    MODEL_COUNT=$(python -c "import json; m=json.load(open('$MANIFEST')); print(len(m.get('models', {})))" 2>/dev/null || echo "?")
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
