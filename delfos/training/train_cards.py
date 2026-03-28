"""
train_cards.py — Métricas 3.5 e 3.6: Cartões vermelhos e amarelos.

Dataset  : team_outcome_train.parquet (90%)
Holdout  : team_outcome_holdout.parquet (10%)
Modelos  : GBR vs PoissonRegressor — seleciona menor MAE
MLflow   : experimentos "red-cards" e "yellow-cards"
"""

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import PoissonRegressor
from sklearn.model_selection import GridSearchCV, cross_val_score

from training.common import load_train, load_holdout, cv_and_log
from training.evaluate import evaluate_regressor

FEATURES = [
    "ht_fouls_home",        "ht_fouls_away",
    "ht_yellow_cards_home", "ht_yellow_cards_away",
    "competition_type",
]
TARGET_RED    = "total_red_cards"
TARGET_YELLOW = "total_yellow_cards"
PARAM_GRID    = {"n_estimators": [100, 200], "max_depth": [3, 5], "learning_rate": [0.05, 0.1]}


def _compare_and_log(X, y, X_h, y_h, experiment_name, feature_names):
    gs = GridSearchCV(GradientBoostingRegressor(random_state=42),
                      PARAM_GRID, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1)
    gs.fit(X, y)
    mae_gbr = -gs.best_score_

    poisson = PoissonRegressor(max_iter=500)
    mae_poi = -cross_val_score(poisson, X, y, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1).mean()
    poisson.fit(X, y)

    print(f"  [{experiment_name}] GBR MAE={mae_gbr:.4f}  Poisson MAE={mae_poi:.4f}")

    if mae_gbr <= mae_poi:
        winner, params, run_name = gs.best_estimator_, gs.best_params_, "gbr-v1"
    else:
        winner, params, run_name = poisson, {"model": "PoissonRegressor"}, "poisson-v1"

    scores, model = cv_and_log(
        model=winner, X=X, y=y,
        scoring="neg_mean_absolute_error",
        experiment_name=experiment_name, params=params, run_name=run_name,
    )
    print(f"  [{experiment_name}] CV MAE: {-scores.mean():.3f} ± {scores.std():.3f}")

    if y.mean() < 0.3:
        print(f"  [nota] Evento raro: média={y.mean():.3f}/partida — R² pode ser baixo.")

    evaluate_regressor(model, X_h, y_h, feature_names, experiment_name)
    return model


def train():
    print("=" * 60)
    print("Treinando: red-cards + yellow-cards (Métricas 3.5, 3.6)")
    print("=" * 60)

    df   = load_train("team_outcome")
    df_h = load_holdout("team_outcome")

    X   = pd.get_dummies(df[FEATURES],   columns=["competition_type"])
    X_h = pd.get_dummies(df_h[FEATURES], columns=["competition_type"])
    X_h = X_h.reindex(columns=X.columns, fill_value=0)
    feature_names = X.columns.tolist()

    _compare_and_log(X, df[TARGET_RED],    X_h, df_h[TARGET_RED],    "red-cards",    feature_names)
    _compare_and_log(X, df[TARGET_YELLOW], X_h, df_h[TARGET_YELLOW], "yellow-cards", feature_names)


if __name__ == "__main__":
    train()
