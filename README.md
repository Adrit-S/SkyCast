# SkyCast

Machine-learning weather forecasts for Urbana, IL: next-day to 3-day high and low temperature and chance of rain, learned from 30+ years of local history.

Names: Adrit, Alex, Nikhil, Linh, Peter

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m skycast.data       # download daily history (1990 to now) into data/raw/
python -m skycast.train      # train, score vs baselines, save models/ and docs/data/
python -m skycast.forecast   # live forecast -> docs/data/forecast.json

python -m http.server -d docs   # view the site at http://localhost:8000
```

## Layout

| Path | What it does |
|---|---|
| `skycast/config.py` | Locations, variables, date splits, forecast horizons |
| `skycast/data.py` | Downloads Open-Meteo (ERA5) daily data for Urbana and 4 upstream points |
| `skycast/features.py` | Lagged/rolling features, season encoding, targets, climatology |
| `skycast/train.py` | Trains linear and gradient-boosting models per target and horizon; compares to persistence and climatology on 2021+ |
| `skycast/forecast.py` | Builds today's features and writes the forecast for the website |
| `docs/` | Static website (GitHub Pages ready); reads `docs/data/*.json` |
| `.github/workflows/forecast.yml` | Retrains and refreshes the forecast daily |

## Current results (test set: 2021 onward)

| Target | 1 day | 2 days | 3 days |
|---|---|---|---|
| High temp MAE (persistence → SkyCast) | 5.5° → 4.0° | 7.9° → 6.0° | 8.8° → 6.8° |
| Low temp MAE | 5.1° → 3.2° | 7.3° → 5.1° | 8.2° → 6.0° |
| Rain Brier skill vs climatology | +0.25 | +0.03 | 0.00 |

## Ideas for next steps

- Swap in real station observations (NOAA GHCN Urbana, Illinois Climate Network Champaign) instead of gridded reanalysis
- Predict rain amount, snow, wind
- Sequence models (LSTM/GRU, temporal CNN) over the last N days
- Hourly data and more upstream points
- Compare against official NWS forecasts
