"""
train_player_sog.py — Baseline EDA: Chutes a gol por jogador.

Dataset  : player_sog_train.parquet (90%)
Holdout  : player_sog_holdout.parquet (10%)
Modelo   : GradientBoostingRegressor + GridSearchCV
MLflow   : experimento "player-sog"
Baseline : R²=0.26, MAE=0.24 (CA-US-4.2.1)
"""

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV, cross_val_score

from training.common import load_train, load_holdout, cv_and_log
from training.evaluate import evaluate_regressor

FEATURES = [
    "ht_passes",
    "ht_touches",
    "ht_dribbles",
    "player_id_x_world_cup",
    "competition_type",
]
TARGET       = "total_sog"
BASELINE_R2  = 0.26
BASELINE_MAE = 0.24

PARAM_GRID = {
    "n_estimators":  [100, 200],
    "max_depth":     [3, 5],
    "learning_rate": [0.05, 0.1],
}


def train():
    print("=" * 60)
    print("Treinando: player-sog (baseline EDA validado)")
    print("=" * 60)

    df   = load_train("player_sog")
    df_h = load_holdout("player_sog")

    X   = pd.get_dummies(df[FEATURES],   columns=["competition_type"])
    X_h = pd.get_dummies(df_h[FEATURES], columns=["competition_type"])
    X_h = X_h.reindex(columns=X.columns, fill_value=0)
    y   = df[TARGET]
    y_h = df_h[TARGET]

    print(f"  Média {TARGET}: {y.mean():.4f}/partida (esperado ~0.16 — evento raro)")

    gs = GridSearchCV(GradientBoostingRegressor(random_state=42),
                      PARAM_GRID, cv=5, scoring="r2", n_jobs=-1)
    gs.fit(X, y)
    print(f"  Melhores parâmetros: {gs.best_params_}")

    scores_r2, final_model = cv_and_log(
        model=gs.best_estimator_, X=X, y=y,
        scoring="r2",
        experiment_name="player-sog", params=gs.best_params_, run_name="gbr-v1",
    )
    mae_cv = -cross_val_score(final_model, X, y, cv=5,
                               scoring="neg_mean_absolute_error", n_jobs=-1).mean()

    print(f"  player_sog R²  CV: {scores_r2.mean():.3f}  (baseline: {BASELINE_R2})")
    print(f"  player_sog MAE CV: {mae_cv:.3f}  (baseline: {BASELINE_MAE})")

    if scores_r2.mean() >= BASELINE_R2 and mae_cv <= BASELINE_MAE:
        print("  [OK] CA-US-4.2.1 APROVADO — modelo >= baseline EDA.")
    else:
        print(f"  [AVISO] CA-US-4.2.1 — abaixo do baseline. "
              f"R²={scores_r2.mean():.3f} MAE={mae_cv:.3f}")

    evaluate_regressor(final_model, X_h, y_h, X.columns.tolist(), "player-sog")
    return final_model


if __name__ == "__main__":
    train()
