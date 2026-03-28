"""
common.py — Funções compartilhadas para treinamento dos modelos Delfos v1.0.
"""

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from pathlib import Path
from sklearn.model_selection import cross_val_score

ROOT_DIR = Path(__file__).resolve().parents[2]

# MLflow local (SQLite) — não exige servidor rodando
MLFLOW_URI = f"sqlite:///{ROOT_DIR / 'mlflow.db'}"
mlflow.set_tracking_uri(MLFLOW_URI)

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR    = ROOT_DIR / "models"
TRAINED_DIR   = MODELS_DIR / "trained"
TRAINED_DIR.mkdir(parents=True, exist_ok=True)


def load_train(gran: str, processed_dir: Path = PROCESSED_DIR) -> pd.DataFrame:
    path = Path(processed_dir) / f"{gran}_train.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado: {path}\n"
            "Execute run_pipeline.py para gerar os dados antes de treinar."
        )
    df = pd.read_parquet(path)
    print(f"  [load-train] {gran}: {df.shape[0]} linhas, {df.shape[1]} colunas")
    return df


def load_holdout(gran: str, processed_dir: Path = PROCESSED_DIR) -> pd.DataFrame:
    """Carrega o holdout (10%) — usado apenas para avaliação pós-treino."""
    path = Path(processed_dir) / f"{gran}_holdout.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Holdout não encontrado: {path}")
    df = pd.read_parquet(path)
    print(f"  [load-holdout] {gran}: {df.shape[0]} linhas")
    return df


def save_model_local(model, name: str) -> Path:
    """Salva o modelo treinado em models/trained/<name>.joblib."""
    path = TRAINED_DIR / f"{name}.joblib"
    joblib.dump(model, path)
    print(f"  [save] {path.relative_to(ROOT_DIR)}")
    return path


def cv_and_log(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    scoring: str,
    experiment_name: str,
    params: dict,
    run_name: str,
) -> tuple:
    """
    CV k=5 + log MLflow (local) + salva modelo em disco.
    Retorna (scores, model_fitted).
    """
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=run_name):
        run_id = mlflow.active_run().info.run_id

        scores = cross_val_score(model, X, y, cv=5, scoring=scoring, n_jobs=-1)
        mlflow.log_params(params)
        mlflow.log_metric(f"{scoring}_mean", float(scores.mean()))
        mlflow.log_metric(f"{scoring}_std",  float(scores.std()))

        model.fit(X, y)
        mlflow.sklearn.log_model(model, artifact_path="model")

        try:
            mlflow.register_model(f"runs:/{run_id}/model", name=experiment_name)
        except Exception:
            pass  # registry opcional

        print(
            f"  [mlflow] {experiment_name!r}  run={run_id[:8]}  "
            f"{scoring}: {scores.mean():.4f} ± {scores.std():.4f}"
        )

    save_model_local(model, experiment_name)
    return scores, model
