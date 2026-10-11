import openmeteo_requests
import requests_cache
from retry_requests import retry

from .config import (
    API_URL,
    HOURLY_VARIABLES,
    LATITUDE,
    LONGITUDE,
    PAST_DAYS,
    TIMEZONE,
)


def fetch_weather():
    """Call Open-Meteo and return the first location's response.

    :return: Open-Meteo response object (binary, not yet a DataFrame)
    :raises: exception from the client if all retries fail
    """
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    responses = openmeteo.weather_api(
        API_URL,
        params={
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "hourly": HOURLY_VARIABLES,
            "timezone": TIMEZONE,
            "past_days": PAST_DAYS,
        },
    )
    return responses[0]
