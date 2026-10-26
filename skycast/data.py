"""Download daily weather history from Open-Meteo (ERA5 reanalysis) and cache it as CSV.

Run directly to refresh the cache:  python -m skycast.data
"""
import datetime as dt
import time
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from .config import DAILY_VARS, HISTORY_START, LOCATIONS, RAW_DIR, TIMEZONE, UNITS

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _get(url, params, retries=4):
    for attempt in range(retries):
        resp = requests.get(url, params=params, timeout=120)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429 and attempt < retries - 1:
            time.sleep(30 * (attempt + 1))  # rate limited: back off and retry
            continue
        resp.raise_for_status()
    raise RuntimeError(f"request to {url} failed")


def _to_frame(payload):
    df = pd.DataFrame(payload["daily"])
    df["time"] = pd.to_datetime(df["time"])
    return df.set_index("time")


def fetch_archive(key, start=HISTORY_START, end=None):
    """Daily history for one location. The archive lags real time by about 5 days."""
    loc = LOCATIONS[key]
    end = end or (dt.date.today() - dt.timedelta(days=6)).isoformat()
    params = {
        "latitude": loc["lat"],
        "longitude": loc["lon"],
        "start_date": start,
        "end_date": end,
        "daily": ",".join(DAILY_VARS),
        "timezone": TIMEZONE,
        **UNITS,
    }
    return _to_frame(_get(ARCHIVE_URL, params))


def fetch_recent(key, past_days=14):
    """The last couple of weeks from the forecast API, to bridge the archive's lag."""
    loc = LOCATIONS[key]
    params = {
        "latitude": loc["lat"],
        "longitude": loc["lon"],
        "past_days": past_days,
        "forecast_days": 1,
        "daily": ",".join(DAILY_VARS),
        "timezone": TIMEZONE,
        **UNITS,
    }
    return _to_frame(_get(FORECAST_URL, params))


def load_history(refresh=False):
    """All locations side by side, columns named like 'urb_temperature_2m_max'."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for key in LOCATIONS:
        path = RAW_DIR / f"{key}.csv"
        if refresh or not path.exists():
            print(f"downloading {LOCATIONS[key]['name']} ...")
            fetch_archive(key).to_csv(path)
        df = pd.read_csv(path, index_col="time", parse_dates=True)
        frames.append(df.add_prefix(f"{key}_"))
    return pd.concat(frames, axis=1).sort_index()


def load_latest():
    """History plus the most recent days, ending at the last fully observed day (yesterday)."""
    hist = load_history()
    recent = pd.concat(
        [fetch_recent(key).add_prefix(f"{key}_") for key in LOCATIONS], axis=1
    )
    combined = hist.combine_first(recent)  # archive wins where both exist
    today = dt.datetime.now(ZoneInfo(TIMEZONE)).date()
    yesterday = pd.Timestamp(today) - pd.Timedelta(days=1)
    return combined.loc[:yesterday]


if __name__ == "__main__":
    df = load_history(refresh=True)
    print(f"{len(df):,} days, {df.index.min().date()} to {df.index.max().date()}")
