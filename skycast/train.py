"""Train SkyCast models, score them against baselines on held-out years, and save everything.

    python -m skycast.train

Writes models/*.joblib (refit on all data, for live forecasts), docs/data/metrics.json and
docs/data/backtest.json (for the website).
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss, mean_absolute_error, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import HORIZONS, MODEL_DIR, SITE_DATA_DIR, TEST_START
from .data import load_history
from .features import TARGETS, build_features, build_targets, climatology, target_values

MODEL_LABELS = {
    "persistence": "Persistence",
    "climatology": "Climatology",
    "linear": "Linear",
    "gbm": "Gradient boosting",
}


def make_model(kind, target):
    if target == "rain":
        if kind == "linear":
            return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))
        return HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=1.0)
    if kind == "linear":
        return make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    return HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=1.0)


def predict(model, target, X):
    return model.predict_proba(X)[:, 1] if target == "rain" else model.predict(X)


def score(target, y, pred):
    if target == "rain":
        return {"brier": brier_score_loss(y, pred), "auc": roc_auc_score(y, pred)}
    return {"mae": mean_absolute_error(y, pred)}


def main():
    raw = load_history()
    X = build_features(raw)
    Y = build_targets(raw)
    today_vals = target_values(raw)
    train_end = pd.Timestamp(TEST_START) - pd.Timedelta(days=1)
    clim = climatology(raw, train_end)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    metrics = {"test_start": TEST_START, "models": MODEL_LABELS, "targets": {}}
    backtest = {}

    for target in TARGETS:
        metrics["targets"][target] = {}
        for h in HORIZONS:
            col = f"{target}_h{h}"
            ok = Y[col].notna() & X.notna().all(axis=1)
            Xo, yo = X[ok], Y[col][ok]
            train = Xo.index <= train_end
            test = ~train
            target_dates = Xo.index[test] + pd.Timedelta(days=h)

            preds = {
                "persistence": today_vals[target].loc[Xo.index[test]].to_numpy(),
                "climatology": clim[target].loc[target_dates.dayofyear].to_numpy(),
            }
            for kind in ("linear", "gbm"):
                model = make_model(kind, target).fit(Xo[train], yo[train])
                preds[kind] = predict(model, target, Xo[test])

            y_test = yo[test].to_numpy()
            scores = {k: score(target, y_test, p) for k, p in preds.items()}
            if target == "rain":
                ref = scores["climatology"]["brier"]
                for s in scores.values():
                    s["brier_skill"] = 1 - s["brier"] / ref
            metrics["targets"][target][f"h{h}"] = scores
            key = "brier" if target == "rain" else "mae"
            best = min(("linear", "gbm"), key=lambda k: scores[k][key])
            metrics["targets"][target][f"h{h}"]["best"] = best
            print(f"{col:8s} " + "  ".join(f"{k}={v[key]:.3f}" for k, v in scores.items() if k != "best") + f"  -> {best}")

            if h == 1:
                last = slice(-120, None)
                backtest[target] = {
                    "dates": [d.date().isoformat() for d in target_dates[last]],
                    "actual": np.round(y_test[last], 2).tolist(),
                    "skycast": np.round(preds[best][last], 2).tolist(),
                    "persistence": np.round(preds["persistence"][last], 2).tolist(),
                }

            # Refit the winning model on every available day for live use.
            final = make_model(best, target).fit(Xo, yo)
            joblib.dump({"model": final, "kind": best, "columns": list(X.columns)}, MODEL_DIR / f"{col}.joblib")

    clim.to_csv(MODEL_DIR / "climatology.csv")
    (SITE_DATA_DIR / "metrics.json").write_text(json.dumps(metrics, indent=1))
    (SITE_DATA_DIR / "backtest.json").write_text(json.dumps(backtest))
    print(f"saved models to {MODEL_DIR} and site data to {SITE_DATA_DIR}")


if __name__ == "__main__":
    main()
