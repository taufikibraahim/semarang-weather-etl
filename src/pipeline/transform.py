import pandas as pd

from .config import COLUMN_RENAMES, HOURLY_VARIABLES


def response_to_dataframe(response):
    """Convert an Open-Meteo response into an hourly DataFrame.

    :param response: response object from ``fetch_weather``
    :return: DataFrame with a ``date`` column and one column per variable
    """
    hourly = response.Hourly()
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        ).tz_convert(response.Timezone().decode())
    }

    for index, name in enumerate(HOURLY_VARIABLES):
        hourly_data[name] = hourly.Variables(index).ValuesAsNumpy()
    df = pd.DataFrame(data=hourly_data)
    return df


def clean_weather(df):
    """Clean the weather DataFrame.

    Dates are stored as local time (WIB, UTC+7) text without timezone info.
    Columns are renamed so that names carry their units.

    :param df: DataFrame with a ``date`` column and one column per variable
    :return: cleaned DataFrame
    :raises ValueError: if values are outside plausible ranges
    """
    df = df.copy()

    # Drop timezone label; values stay in local time (WIB, UTC+7)
    df["date"] = df["date"].dt.tz_localize(None)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d %H:%M:%S")

    df = df.rename(columns=COLUMN_RENAMES)

    if not df["rain_mm"].dropna().ge(0).all():
        raise ValueError("rain_mm contains negative values")

    if not df["precip_probability_pct"].dropna().between(0, 100).all():
        raise ValueError("precip_probability_pct outside 0-100")

    if not df["date"].is_unique:
        raise ValueError("duplicate timestamps in date")

    return df
