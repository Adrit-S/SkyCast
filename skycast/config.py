"""Shared settings: where we forecast, which upstream points we use, and which variables we pull."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
MODEL_DIR = ROOT / "models"
SITE_DATA_DIR = ROOT / "docs" / "data"

TIMEZONE = "America/Chicago"

# The target location plus points upstream (weather here mostly moves west -> east).
LOCATIONS = {
    "urb": {"name": "Urbana, IL", "lat": 40.11, "lon": -88.21},
    "peo": {"name": "Peoria, IL", "lat": 40.69, "lon": -89.59},
    "spi": {"name": "Springfield, IL", "lat": 39.80, "lon": -89.64},
    "dav": {"name": "Davenport, IA", "lat": 41.52, "lon": -90.58},
    "stl": {"name": "St. Louis, MO", "lat": 38.63, "lon": -90.20},
}
TARGET = "urb"

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "snowfall_sum",
    "wind_speed_10m_max",
    "wind_direction_10m_dominant",
    "shortwave_radiation_sum",
    "relative_humidity_2m_mean",
    "dew_point_2m_mean",
    "pressure_msl_mean",
    "cloud_cover_mean",
]
UNITS = {"temperature_unit": "fahrenheit", "precipitation_unit": "inch", "wind_speed_unit": "mph"}

HISTORY_START = "1990-01-01"
TEST_START = "2021-01-01"  # everything before trains, everything from here on is held out
HORIZONS = [1, 2, 3]  # days ahead
RAIN_THRESHOLD_IN = 0.01  # a "rain day" is >= 0.01 inch of precipitation
