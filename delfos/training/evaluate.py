"""
evaluate.py — Avaliação dos modelos no holdout (10%) com relatório CLI e gráficos.

Gráficos salvos em: reports/plots/
"""

import matplotlib
matplotlib.use("Agg")  # backend não-interativo (funciona sem display)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    mean_absolute_error,
    r2_score,
    mean_squared_error,
)

PLOTS_DIR = Path(__file__).resolve().parents[2] / "reports" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="muted")


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _importances(model, feature_names: list) -> dict:
    """Extrai importâncias de features de forma agnóstica ao modelo."""
    if hasattr(model, "feature_importances_"):
        return dict(zip(feature_names, model.feature_importances_))
    if hasattr(model, "coef_"):
        coefs = np.abs(np.array(model.coef_)).flatten()
        return dict(zip(feature_names, coefs[: len(feature_names)]))
    return {}


def _save(fig, name: str):
    path = PLOTS_DIR / name
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  [plot] reports/plots/{name}")


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def _plot_feature_importance(importances: dict, model_name: str, top_n: int = 15):
    if not importances:
        return
    items = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:top_n]
    names, vals = zip(*items)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(range(len(names)), vals, color="steelblue", edgecolor="white")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Importância", fontsize=11)
    ax.set_title(f"Features Utilizadas — {model_name}", fontsize=13, fontweight="bold")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width() + max(vals) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{v:.4f}", va="center", fontsize=9)
    _save(fig, f"{model_name}_feature_importance.png")


def _plot_confusion_matrix(y_true, y_pred, labels: list, model_name: str):
    cm  = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=labels, yticklabels=labels, ax=ax, linewidths=0.5)
    ax.set_xlabel("Predito", fontsize=11)
    ax.set_ylabel("Real", fontsize=11)
    ax.set_title(f"Matriz de Confusão — {model_name}\n(holdout 10%)", fontsize=12, fontweight="bold")
    _save(fig, f"{model_name}_confusion_matrix.png")


def _plot_actual_vs_predicted(y_true: np.ndarray, y_pred: np.ndarray, model_name: str):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Scatter: real vs predito
    ax = axes[0]
    ax.scatter(y_true, y_pred, alpha=0.45, s=18, color="steelblue")
    lo = min(y_true.min(), y_pred.min())
    hi = max(y_true.max(), y_pred.max())
    ax.plot([lo, hi], [lo, hi], "r--", lw=1.5, label="Ideal")
    ax.set_xlabel("Real", fontsize=11)
    ax.set_ylabel("Predito", fontsize=11)
    ax.set_title(f"Real vs Predito — {model_name}", fontsize=12, fontweight="bold")
    ax.legend()

    # Resíduos
    ax = axes[1]
    residuals = y_true - y_pred
    ax.hist(residuals, bins=30, color="steelblue", edgecolor="white", alpha=0.85)
    ax.axvline(0, color="red", linestyle="--", lw=1.5)
    ax.set_xlabel("Resíduo (Real - Predito)", fontsize=11)
    ax.set_ylabel("Frequência", fontsize=11)
    ax.set_title(f"Distribuição de Resíduos — {model_name}", fontsize=12, fontweight="bold")

    fig.suptitle(f"Avaliação no Holdout 10% — {model_name}", fontsize=13, y=1.02)
    _save(fig, f"{model_name}_actual_vs_predicted.png")


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def evaluate_classifier(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    feature_names: list,
    model_name: str,
    class_labels: list = None,
):
    """Avalia classificador no holdout: CLI + confusion matrix + feature importance."""
    y_pred  = model.predict(X_test)
    acc     = accuracy_score(y_test, y_pred)
    report  = classification_report(
        y_test, y_pred,
        target_names=class_labels,
        zero_division=0,
    )
    imps = _importances(model, feature_names)

    bar = "=" * 64
    print(f"\n{bar}")
    print(f"  AVALIAÇÃO — {model_name}  |  Holdout 10%  |  Classificador")
    print(bar)
    print(f"  Accuracy      : {acc:.4f}")
    print(f"  Amostras      : {len(y_test)}")
    print(f"\n{report}")

    if imps:
        print("  Features utilizadas (top-10 por importância):")
        for i, (feat, imp) in enumerate(
            sorted(imps.items(), key=lambda x: x[1], reverse=True)[:10], 1
        ):
            print(f"    {i:>2}. {feat:<38} {imp:.4f}")
    print()

    labels = class_labels or [str(c) for c in sorted(y_test.unique())]
    _plot_confusion_matrix(y_test, y_pred, labels, model_name)
    _plot_feature_importance(imps, model_name)


def evaluate_regressor(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    feature_names: list,
    model_name: str,
):
    """Avalia regressor no holdout: CLI + actual-vs-predicted + feature importance."""
    y_pred = model.predict(X_test)
    mae    = mean_absolute_error(y_test, y_pred)
    r2     = r2_score(y_test, y_pred)
    rmse   = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    imps   = _importances(model, feature_names)

    bar = "=" * 64
    print(f"\n{bar}")
    print(f"  AVALIAÇÃO — {model_name}  |  Holdout 10%  |  Regressor")
    print(bar)
    print(f"  MAE           : {mae:.4f}")
    print(f"  RMSE          : {rmse:.4f}")
    print(f"  R²            : {r2:.4f}")
    print(f"  Amostras      : {len(y_test)}")

    if imps:
        print(f"\n  Features utilizadas (top-10 por importância):")
        for i, (feat, imp) in enumerate(
            sorted(imps.items(), key=lambda x: x[1], reverse=True)[:10], 1
        ):
            print(f"    {i:>2}. {feat:<38} {imp:.4f}")
    print()

    _plot_actual_vs_predicted(
        np.array(y_test, dtype=float),
        np.array(y_pred, dtype=float),
        model_name,
    )
    _plot_feature_importance(imps, model_name)
