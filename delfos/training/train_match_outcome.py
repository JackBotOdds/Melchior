"""
train_match_outcome.py — Métrica 3.1: Resultado da partida (HOME / DRAW / AWAY).

Dataset  : team_outcome_train.parquet  (90%)
Holdout  : team_outcome_holdout.parquet (10%)
Modelo   : XGBoostClassifier + GridSearchCV
MLflow   : experimento "match-outcome"  (SQLite local)
"""

import pandas as pd
import xgboost as xgb
from sklearn.model_selection import GridSearchCV

from training.common import load_train, load_holdout, cv_and_log
from training.evaluate import evaluate_classifier

FEATURES = [
    "ht_goals_diff",
    "ht_shots_diff",
    "ht_sog_diff",
    "ht_fouls_diff",
    "competition_type",
]
# ht_corners_diff EXCLUÍDO (std=0 na EDA — CA-US-4.2.3)

TARGET      = "outcome"   # HOME=0, DRAW=1, AWAY=2
PARAM_GRID  = {"n_estimators": [100, 200], "max_depth": [3, 5]}


def train():
    print("=" * 60)
    print("Treinando: match-outcome (Métrica 3.1)")
    print("=" * 60)

    df = load_train("team_outcome")
    X  = pd.get_dummies(df[FEATURES], columns=["competition_type"])
    y  = df[TARGET]

    gs = GridSearchCV(
        xgb.XGBClassifier(
            learning_rate=0.05, eval_metric="mlogloss",
            random_state=42, n_jobs=-1,
        ),
        PARAM_GRID, cv=5, scoring="accuracy", n_jobs=-1,
    )
    gs.fit(X, y)
    print(f"  Melhores parâmetros: {gs.best_params_}")

    scores, final_model = cv_and_log(
        model=gs.best_estimator_, X=X, y=y,
        scoring="accuracy", experiment_name="match-outcome",
        params=gs.best_params_, run_name="xgboost-v1",
    )
    print(f"  CV accuracy: {scores.mean():.3f} ± {scores.std():.3f}")

    # ── Avaliação no holdout ──────────────────────────────────────
    df_h  = load_holdout("team_outcome")
    X_h   = pd.get_dummies(df_h[FEATURES], columns=["competition_type"])
    X_h   = X_h.reindex(columns=X.columns, fill_value=0)
    y_h   = df_h[TARGET]

    evaluate_classifier(
        model=final_model, X_test=X_h, y_test=y_h,
        feature_names=X.columns.tolist(),
        model_name="match-outcome",
        class_labels=["HOME", "DRAW", "AWAY"],
    )
    return final_model


if __name__ == "__main__":
    train()
