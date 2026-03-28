"""
train_total_goals.py — Métricas 3.2 e 3.4: Gols totais + Distribuição de gols.

Dataset  : team_sog_train.parquet  (90%)
Holdout  : team_sog_holdout.parquet (10%)
Modelo   : GradientBoostingRegressor + GridSearchCV
MLflow   : experimentos "total-goals" e "goals-distribution"
"""

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV

from training.common import load_train, load_holdout, cv_and_log
from training.evaluate import evaluate_regressor

FEATURES = [
    "ht_shots_home", "ht_shots_away",
    "ht_sog_home",   "ht_sog_away",
    "ht_goals_home", "ht_goals_away",
    "competition_type",
]
TARGET_GOALS = "total_goals"
TARGET_DIST  = "goals_home_frac"

PARAM_GRID = {
    "n_estimators":  [100, 200],
    "max_depth":     [3, 5],
    "learning_rate": [0.05, 0.1],
}


def _train_one(X, y, X_h, y_h, experiment_name, run_name, feature_names):
    gbr = GradientBoostingRegressor(random_state=42)
    gs  = GridSearchCV(gbr, PARAM_GRID, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1)
    gs.fit(X, y)
    print(f"  [{experiment_name}] params={gs.best_params_}  MAE_gs={-gs.best_score_:.4f}")

    scores, model = cv_and_log(
        model=gs.best_estimator_, X=X, y=y,
        scoring="neg_mean_absolute_error",
        experiment_name=experiment_name, params=gs.best_params_, run_name=run_name,
    )
    print(f"  [{experiment_name}] CV MAE: {-scores.mean():.3f} ± {scores.std():.3f}")

    evaluate_regressor(model, X_h, y_h, feature_names, experiment_name)
    return model


def train():
    print("=" * 60)
    print("Treinando: total-goals + goals-distribution (Métricas 3.2, 3.4)")
    print("=" * 60)

    df   = load_train("team_sog")
    df_h = load_holdout("team_sog")

    X   = pd.get_dummies(df[FEATURES],   columns=["competition_type"])
    X_h = pd.get_dummies(df_h[FEATURES], columns=["competition_type"])
    X_h = X_h.reindex(columns=X.columns, fill_value=0)
    feature_names = X.columns.tolist()

    # Métrica 3.2 — Gols totais
    _train_one(X, df[TARGET_GOALS], X_h, df_h[TARGET_GOALS],
               "total-goals", "gbr-v1", feature_names)

    # Métrica 3.4 — Distribuição de gols
    if TARGET_DIST in df.columns:
        _train_one(X, df[TARGET_DIST], X_h, df_h[TARGET_DIST],
                   "goals-distribution", "gbr-v1", feature_names)
    else:
        print(f"  [AVISO] Coluna '{TARGET_DIST}' ausente — Métrica 3.4 pulada.")


if __name__ == "__main__":
    train()
