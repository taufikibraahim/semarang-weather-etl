import pandas as pd
import pytest

from src.pipeline.config import HOURLY_VARIABLES


@pytest.fixture()
def raw_weather_df():
    """Small DataFrame shaped like the output of ``response_to_dataframe``."""
    dates = pd.date_range(
        "2026-10-10 00:00",
        periods=3,
        freq="h",
        tz="Asia/Jakarta",
    )
    data = {"date": dates}
    for i, name in enumerate(HOURLY_VARIABLES):
        data[name] = [float(i + 1)] * 3
    return pd.DataFrame(data)
