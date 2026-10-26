"""Turn the raw daily table into model features (known on day t) and targets (day t + h)."""
import numpy as np
import pandas as pd

from .config import HORIZONS, LOCATIONS, RAIN_THRESHOLD_IN, TARGET

TMAX, TMIN, PRCP = "temperature_2m_max", "temperature_2m_min", "precipitation_sum"
TARGETS = ["tmax", "tmin", "rain"]

_LOCAL_VARS = [
    TMAX, TMIN, PRCP, "snowfall_sum", "wind_speed_10m_max", "shortwave_radiation_sum",
    "relative_humidity_2m_mean", "dew_point_2m_mean", "pressure_msl_mean", "cloud_cover_mean",
]
_UPSTREAM_VARS = [TMAX, TMIN, PRCP, "dew_point_2m_mean", "pressure_msl_mean", "cloud_cover_mean"]


def build_features(raw):
    t = f"{TARGET}_"
    feats = {}

    # Target location: today and a few days back.
    for var in _LOCAL_VARS:
        for lag in (0, 1, 2, 3, 6):
            feats[f"{t}{var}_lag{lag}"] = raw[t + var].shift(lag)
    for var in (TMAX, TMIN):
        feats[f"{t}{var}_mean7"] = raw[t + var].rolling(7).mean()
    feats[f"{t}{PRCP}_sum7"] = raw[t + PRCP].rolling(7).sum()
    feats[f"{t}pressure_change1"] = raw[t + "pressure_msl_mean"].diff(1)
    feats[f"{t}pressure_change3"] = raw[t + "pressure_msl_mean"].diff(3)
    wdir = np.deg2rad(raw[t + "wind_direction_10m_dominant"])
    feats[f"{t}wind_dir_sin"] = np.sin(wdir)
    feats[f"{t}wind_dir_cos"] = np.cos(wdir)

    # Upstream points: what is heading our way.
    for key in LOCATIONS:
        if key == TARGET:
            continue
        for var in _UPSTREAM_VARS:
            for lag in (0, 1):
                feats[f"{key}_{var}_lag{lag}"] = raw[f"{key}_{var}"].shift(lag)
        feats[f"{key}_pressure_change1"] = raw[f"{key}_pressure_msl_mean"].diff(1)

    # Season.
    doy = raw.index.dayofyear
    feats["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    feats["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)

    return pd.DataFrame(feats, index=raw.index)


def target_values(raw):
    """Same-day values of each target variable (not yet shifted)."""
    t = f"{TARGET}_"
    return pd.DataFrame(
        {
            "tmax": raw[t + TMAX],
            "tmin": raw[t + TMIN],
            "rain": (raw[t + PRCP] >= RAIN_THRESHOLD_IN).astype(float).where(raw[t + PRCP].notna()),
        },
        index=raw.index,
    )


def build_targets(raw):
    """Columns like 'tmax_h1': the value h days after the row's date."""
    vals = target_values(raw)
    return pd.DataFrame(
        {f"{name}_h{h}": vals[name].shift(-h) for name in TARGETS for h in HORIZONS},
        index=raw.index,
    )


def climatology(raw, train_end):
    """Smoothed day-of-year average of each target, from training years only."""
    vals = target_values(raw).loc[:train_end]
    by_doy = vals.groupby(vals.index.dayofyear).mean().reindex(range(1, 367)).interpolate()
    # Circular 15-day smoothing so Dec 31 and Jan 1 blend together.
    padded = pd.concat([by_doy.iloc[-15:], by_doy, by_doy.iloc[:15]])
    smooth = padded.rolling(15, center=True).mean().iloc[15:-15]
    smooth.index = range(1, 367)
    return smooth
