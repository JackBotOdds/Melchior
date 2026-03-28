"""
train_corners.py — Métrica 3.3: Escanteios totais.

Dataset  : team_outcome_train.parquet (90%)
Holdout  : team_outcome_holdout.parquet (10%)
Modelos  : GBR vs PoissonRegressor — seleciona menor MAE
MLflow   : experimento "corners"
"""

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import PoissonRegressor
from sklearn.model_selection import GridSearchCV, cross_val_score

from training.common import load_train, load_holdout, cv_and_log
from training.evaluate import evaluate_regressor

FEATURES = [
    "ht_shots_home",  "ht_shots_away",
    "ht_fouls_home",  "ht_fouls_away",
    "ht_corners_home","ht_corners_away",
    "competition_type",
]
TARGET     = "total_corners"
PARAM_GRID = {"n_estimators": [100, 200], "max_depth": [3, 5], "learning_rate": [0.05, 0.1]}


def train():
    print("=" * 60)
    print("Treinando: corners (Métrica 3.3)")
    print("=" * 60)

    df   = load_train("team_outcome")
    df_h = load_holdout("team_outcome")

    X   = pd.get_dummies(df[FEATURES],   columns=["competition_type"])
    X_h = pd.get_dummies(df_h[FEATURES], columns=["competition_type"])
    X_h = X_h.reindex(columns=X.columns, fill_value=0)
    y   = df[TARGET]
    y_h = df_h[TARGET]
    feature_names = X.columns.tolist()

    # GBR
    gs = GridSearchCV(GradientBoostingRegressor(random_state=42),
                      PARAM_GRID, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1)
    gs.fit(X, y)
    mae_gbr = -gs.best_score_

    # Poisson
    poisson = PoissonRegressor(max_iter=500)
    mae_poisson = -cross_val_score(poisson, X, y, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1).mean()
    poisson.fit(X, y)

    print(f"  GBR MAE={mae_gbr:.4f}  |  Poisson MAE={mae_poisson:.4f}")

    if mae_gbr <= mae_poisson:
        winner, params, run_name = gs.best_estimator_, gs.best_params_, "gbr-v1"
        print("  Selecionado: GBR")
    else:
        winner, params, run_name = poisson, {"model": "PoissonRegressor"}, "poisson-v1"
        print("  Selecionado: Poisson")

    scores, final_model = cv_and_log(
        model=winner, X=X, y=y,
        scoring="neg_mean_absolute_error",
        experiment_name="corners", params=params, run_name=run_name,
    )
    print(f"  corners CV MAE: {-scores.mean():.3f} ± {scores.std():.3f}")

    evaluate_regressor(final_model, X_h, y_h, feature_names, "corners")
    return final_model


if __name__ == "__main__":
    train()
