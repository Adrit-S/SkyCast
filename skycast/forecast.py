"""Make a live forecast from the latest observations and write docs/data/forecast.json.

    python -m skycast.forecast

Run skycast.train first so the models exist.
"""
import datetime as dt
import json

import joblib
import pandas as pd

from .config import HORIZONS, LOCATIONS, MODEL_DIR, SITE_DATA_DIR, TARGET
from .data import load_latest
from .features import TARGETS, build_features


def main():
    raw = load_latest()
    X = build_features(raw)
    issued = X.dropna().index.max()  # last day with a complete set of features
    row = X.loc[[issued]]
    clim = pd.read_csv(MODEL_DIR / "climatology.csv", index_col=0)

    days = []
    for h in HORIZONS:
        date = issued + pd.Timedelta(days=h)
        day = {"date": date.date().isoformat(), "horizon": h, "normal": {}}
        for target in TARGETS:
            saved = joblib.load(MODEL_DIR / f"{target}_h{h}.joblib")
            model, cols = saved["model"], saved["columns"]
            if target == "rain":
                value = float(model.predict_proba(row[cols])[0, 1])
            else:
                value = float(model.predict(row[cols])[0])
            day[target] = round(value, 3 if target == "rain" else 1)
            day["normal"][target] = round(float(clim.loc[date.dayofyear, target]), 3 if target == "rain" else 1)
        days.append(day)

    out = {
        "location": LOCATIONS[TARGET]["name"],
        "issued_from": issued.date().isoformat(),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "days": days,
    }
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DATA_DIR / "forecast.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
