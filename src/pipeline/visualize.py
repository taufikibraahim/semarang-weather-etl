"""Visualisasi: mengubah hasil query menjadi gambar PNG untuk README.

Memakai API objek ``Figure`` dari matplotlib (bukan ``pyplot``), sehingga:
    - tidak butuh layar/GUI (aman di CI dan Task Scheduler)
    - tidak ada state global yang bocor antar pemanggilan
"""

from contextlib import closing
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

from .queries import (
    daily_rain,
    daily_temperature,
    open_readonly,
    rain_by_hour,
)

FIGURE_SIZE = (9, 4.5)
DPI = 120


def _require_rows(df, name):
    """Raise a clear error when a query returned no rows."""
    if df.empty:
        raise ValueError(f"No data to plot for '{name}'")


def _save(fig, output_path):
    """Save a figure to ``output_path``, creating the folder if needed."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=DPI)
    return output_path


def plot_daily_temperature(df, output_path):
    """Line chart of daily average temperature with a min-max band.

    :param df: result of ``queries.daily_temperature``
    :param output_path: where to save the PNG
    :return: path of the saved image
    :raises ValueError: if ``df`` is empty
    """
    _require_rows(df, "daily_temperature")
    days = pd.to_datetime(df["day"])

    fig = Figure(figsize=FIGURE_SIZE)
    ax = fig.subplots()
    ax.fill_between(
        days,
        df["min_temp_c"],
        df["max_temp_c"],
        alpha=0.25,
        label="Min - Max",
    )
    ax.plot(days, df["avg_temp_c"], marker="o", label="Rata-rata")
    ax.set_title("Suhu harian Semarang")
    ax.set_xlabel("Tanggal")
    ax.set_ylabel("Suhu (°C)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    return _save(fig, output_path)


def plot_daily_rain(df, output_path):
    """Bar chart of total rain per day.

    :param df: result of ``queries.daily_rain``
    :param output_path: where to save the PNG
    :return: path of the saved image
    :raises ValueError: if ``df`` is empty
    """
    _require_rows(df, "daily_rain")
    days = pd.to_datetime(df["day"]).dt.strftime("%d %b")

    fig = Figure(figsize=FIGURE_SIZE)
    ax = fig.subplots()
    ax.bar(days, df["total_rain_mm"])
    ax.set_title("Total hujan harian Semarang")
    ax.set_xlabel("Tanggal")
    ax.set_ylabel("Hujan (mm)")
    ax.grid(axis="y", alpha=0.3)
    fig.autofmt_xdate()
    return _save(fig, output_path)


def plot_rain_by_hour(df, output_path):
    """Bar chart of average rain for each hour of the day.

    :param df: result of ``queries.rain_by_hour``
    :param output_path: where to save the PNG
    :return: path of the saved image
    :raises ValueError: if ``df`` is empty
    """
    _require_rows(df, "rain_by_hour")
    df = df.sort_values("hour")

    fig = Figure(figsize=FIGURE_SIZE)
    ax = fig.subplots()
    ax.bar(df["hour"], df["avg_rain_mm"])
    ax.set_title("Rata-rata hujan per jam (WIB)")
    ax.set_xlabel("Jam")
    ax.set_ylabel("Hujan rata-rata (mm)")
    ax.set_xticks(range(0, 24, 2))
    ax.grid(axis="y", alpha=0.3)
    return _save(fig, output_path)


def generate_charts(db_path, output_dir):
    """Create all charts from the database.

    :param db_path: path to the SQLite file
    :param output_dir: folder for the PNG files (e.g. ``docs/``)
    :return: list of saved image paths
    """
    output_dir = Path(output_dir)
    with closing(open_readonly(db_path)) as conn:
        temperature = daily_temperature(conn)
        rain = daily_rain(conn)
        hourly = rain_by_hour(conn)

    return [
        plot_daily_temperature(temperature, output_dir / "daily_temperature.png"),
        plot_daily_rain(rain, output_dir / "daily_rain.png"),
        plot_rain_by_hour(hourly, output_dir / "rain_by_hour.png"),
    ]
