import sqlite3

import pytest

from src.pipeline.load import save_to_sqlite
from src.pipeline.transform import clean_weather


@pytest.fixture()
def clean_df(raw_weather_df):
    return clean_weather(raw_weather_df)


def count_rows(db_path):
    with sqlite3.connect(db_path) as conn:
        query = "SELECT COUNT(*) FROM hourly_weather"
        return conn.execute(query).fetchone()[0]


def test_save_creates_database_and_rows(tmp_path, clean_df):
    db_path = tmp_path / "sub" / "weather.db"
    save_to_sqlite(clean_df, db_path)
    assert db_path.exists()
    assert count_rows(db_path) == len(clean_df)


def test_save_is_idempotent(tmp_path, clean_df):
    db_path = tmp_path / "weather.db"
    save_to_sqlite(clean_df, db_path)
    save_to_sqlite(clean_df, db_path)
    assert count_rows(db_path) == len(clean_df)


def test_upsert_overwrites_with_latest_value(tmp_path, clean_df):
    db_path = tmp_path / "weather.db"
    save_to_sqlite(clean_df, db_path)

    updated = clean_df.copy()
    updated["temperature_c"] = 99.0
    save_to_sqlite(updated, db_path)

    with sqlite3.connect(db_path) as conn:
        query = "SELECT temperature_c FROM hourly_weather"
        temps = {r[0] for r in conn.execute(query)}
    assert temps == {99.0}
    assert count_rows(db_path) == len(clean_df)


def test_values_stored_as_real(tmp_path, clean_df):
    db_path = tmp_path / "weather.db"
    save_to_sqlite(clean_df, db_path)
    with sqlite3.connect(db_path) as conn:
        kind = conn.execute(
            "SELECT typeof(temperature_c) FROM hourly_weather LIMIT 1"
        ).fetchone()[0]
    assert kind == "real"
