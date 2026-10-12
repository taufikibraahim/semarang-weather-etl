import pandas as pd
import pytest

from src.pipeline.load import COLUMNS, save_to_sqlite
from src.pipeline.visualize import (
    generate_charts,
    plot_daily_rain,
    plot_daily_temperature,
    plot_rain_by_hour,
)


@pytest.fixture()
def temperature_df():
    """Shaped like the output of queries.daily_temperature."""
    return pd.DataFrame(
        {
            "day": ["2026-10-10", "2026-10-11", "2026-10-12"],
            "avg_temp_c": [28.0, 29.0, 27.5],
            "min_temp_c": [25.0, 26.0, 24.5],
            "max_temp_c": [32.0, 33.0, 31.0],
        }
    )


@pytest.fixture()
def rain_df():
    """Shaped like the output of queries.daily_rain."""
    return pd.DataFrame(
        {
            "day": ["2026-10-10", "2026-10-11"],
            "total_rain_mm": [0.0, 4.2],
        }
    )


@pytest.fixture()
def hourly_rain_df():
    """Shaped like the output of queries.rain_by_hour."""
    return pd.DataFrame(
        {
            "hour": list(range(24)),
            "avg_rain_mm": [0.1] * 24,
        }
    )


@pytest.fixture()
def two_full_days_df():
    """48 hourly rows (two complete days) with every column of COLUMNS."""
    dates = pd.date_range("2026-10-10 00:00", periods=48, freq="h")
    data = {"date": dates.strftime("%Y-%m-%d %H:%M:%S")}
    for i, name in enumerate(COLUMNS[1:], start=1):
        data[name] = [float(i + h % 5) for h in range(48)]
    return pd.DataFrame(data)


def test_temperature_plot_creates_png(tmp_path, temperature_df):
    path = plot_daily_temperature(temperature_df, tmp_path / "t.png")
    assert path.exists()
    assert path.stat().st_size > 0


def test_rain_plot_creates_png(tmp_path, rain_df):
    path = plot_daily_rain(rain_df, tmp_path / "r.png")
    assert path.exists()
    assert path.stat().st_size > 0


def test_rain_by_hour_plot_creates_png(tmp_path, hourly_rain_df):
    path = plot_rain_by_hour(hourly_rain_df, tmp_path / "h.png")
    assert path.exists()
    assert path.stat().st_size > 0


def test_plot_creates_missing_folder(tmp_path, temperature_df):
    target = tmp_path / "belum" / "ada" / "t.png"
    plot_daily_temperature(temperature_df, target)
    assert target.exists()


def test_plot_empty_raises(tmp_path):
    with pytest.raises(ValueError, match="No data"):
        plot_daily_temperature(pd.DataFrame(), tmp_path / "t.png")


def test_generate_charts_creates_three_files(tmp_path, two_full_days_df):
    db_path = tmp_path / "weather.db"
    save_to_sqlite(two_full_days_df, db_path)

    paths = generate_charts(db_path, tmp_path / "charts")

    assert len(paths) == 3
    assert all(p.exists() for p in paths)
