import openmeteo_requests
import requests_cache
from retry_requests import retry

from .config import (
    API_URL,
    CACHE_PATH,
    HOURLY_VARIABLES,
    LATITUDE,
    LONGITUDE,
    PAST_DAYS,
    TIMEZONE,
)


def fetch_weather():
    """Call Open-Meteo and return the first location's response."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    cache_session = requests_cache.CachedSession(
        str(CACHE_PATH),
        expire_after=3600,
    )
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    client = openmeteo_requests.Client(session=retry_session)

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": HOURLY_VARIABLES,
        "timezone": TIMEZONE,
        "past_days": PAST_DAYS,
    }
    return client.weather_api(API_URL, params=params)[0]
