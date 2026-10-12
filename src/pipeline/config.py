from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


DB_PATH = BASE_DIR / "data" / "weather.db"
RAW_DIR = BASE_DIR / "data" / "raw"
LOG_FILE = BASE_DIR / "logs" / "pipeline.log"
CACHE_PATH = BASE_DIR / "data" / "cache" / "http_cache"

API_URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE = -6.966667
LONGITUDE = 110.416664
PAST_DAYS = 7
TIMEZONE = "auto"

HOURLY_VARIABLES = [
    "temperature_2m",
    "precipitation_probability",
    "relative_humidity_2m",
    "apparent_temperature",
    "wind_speed_10m",
    "rain",
]

COLUMN_RENAMES = {
    "temperature_2m": "temperature_c",
    "precipitation_probability": "precip_probability_pct",
    "relative_humidity_2m": "humidity_pct",
    "apparent_temperature": "apparent_temperature_c",
    "wind_speed_10m": "wind_speed_kmh",
    "rain": "rain_mm",
}
