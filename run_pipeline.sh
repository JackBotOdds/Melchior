#!/usr/bin/env bash
# =============================================================================
# run_pipeline.sh  --  Pipeline completo Delfos v1.0
#
# Uso:
#   bash run_pipeline.sh               # Pipeline completo (download + ETL + treino)
#   bash run_pipeline.sh --skip-etl   # Pula download/ETL (parquets já existem)
#   bash run_pipeline.sh --force      # Força re-download de todos os CSVs StatsBomb
#
# Saidas:
#   data/raw/          -> CSVs por competicao
#   data/processed/    -> Parquets de treino (90%) e holdout (10%)
#   models/trained/    -> Modelos .joblib
#   reports/plots/     -> Graficos de avaliacao (.png)
#   mlflow.db          -> Historico de experimentos MLflow
#
# Requisitos: Python 3.11+, pip
# Tempo estimado (download completo): 30-90 min (depende da rede)
# =============================================================================

set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python}"
SKIP_ETL=false
FORCE_DOWNLOAD=false

# --- Parse args ---
for arg in "$@"; do
  case $arg in
    --skip-etl)    SKIP_ETL=true ;;
    --force)       FORCE_DOWNLOAD=true ;;
    --help|-h)
      sed -n '2,20p' "$0" | sed 's/^# //'
      exit 0
      ;;
  esac
done

echo "============================================================"
echo "     DELFOS v1.0 -- Pipeline de Treinamento"
echo "============================================================"
echo "Python : $($PYTHON --version)"
echo "Dir    : $(pwd)"
echo ""

# --- Instala dependencias ---
echo "[1/4] Verificando dependencias..."
$PYTHON -m pip install -r requirements-ml.txt --quiet
echo "      OK"

# --- Download e conversao JSON -> CSV ---
if [ "$SKIP_ETL" = false ]; then
  echo ""
  echo "[2/4] StatsBomb JSON -> CSV (todas as competicoes disponiveis)"
  echo "      AVISO: ~75 competicoes / ~5000+ partidas -- pode levar 30-90 min"
  echo "      Use Ctrl+C para interromper. Re-execute com --skip-etl apos cancelar."
  echo ""
  if [ "$FORCE_DOWNLOAD" = true ]; then
    $PYTHON -m etl.statsbomb_loader --force
  else
    $PYTHON -m etl.statsbomb_loader
  fi

  echo ""
  echo "[3/4] ETL: CSV -> Parquet + split 90/10 + StandardScaler"
  $PYTHON -c "
import sys
sys.path.insert(0, '.')
from pathlib import Path
from etl.data_loader import load_all
from etl.cleaner import clean
from etl.feature_engineer import engineer
from etl.preprocessor import fit_and_split
dfs = load_all(Path('data/raw'))
dfs = clean(dfs)
dfs = engineer(dfs)
fit_and_split(dfs, Path('models/preprocessors'), Path('data/processed'))
print('ETL concluido.')
"
else
  echo ""
  echo "[2-3/4] Pulando download e ETL (--skip-etl ativo)"
fi

# --- Treinamento + Avaliacao ---
echo ""
echo "[4/4] Treinamento dos modelos + Avaliacao no holdout..."
$PYTHON run_pipeline.py --skip-etl

echo ""
echo "============================================================"
echo "  CONCLUIDO"
echo "  Graficos  : reports/plots/"
echo "  Modelos   : models/trained/"
echo "  MLflow UI : mlflow ui --backend-store-uri sqlite:///mlflow.db"
echo "============================================================"
