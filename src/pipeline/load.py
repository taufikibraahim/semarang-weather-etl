import sqlite3
from contextlib import closing
from pathlib import Path

COLUMNS = [
    "date",
    "temperature_c",
    "precip_probability_pct",
    "humidity_pct",
    "apparent_temperature_c",
    "wind_speed_kmh",
    "rain_mm",
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS hourly_weather (
    date TEXT PRIMARY KEY,
    temperature_c REAL,
    precip_probability_pct REAL,
    humidity_pct REAL,
    apparent_temperature_c REAL,
    wind_speed_kmh REAL,
    rain_mm REAL
)
"""

UPSERT_SQL = """
INSERT INTO hourly_weather ({cols})
VALUES ({marks})
ON CONFLICT(date) DO UPDATE SET
    {updates}
""".format(
    cols=", ".join(COLUMNS),
    marks=", ".join("?" for _ in COLUMNS),
    updates=", ".join(f"{col}=excluded.{col}" for col in COLUMNS[1:]),
)


def create_table(conn):
    """Create the hourly_weather table if it doesn't exist.

    :param conn: SQLite connection object
    """
    conn.execute(CREATE_TABLE_SQL)


def upsert_rows(conn, df):
    """Insert rows, overwriting existing rows with the same date.

    :param conn: SQLite connection object
    :param df: cleaned DataFrame containing all columns in ``COLUMNS``
    :return: number of rows written
    """
    data = df[COLUMNS].astype(object).values.tolist()
    conn.executemany(UPSERT_SQL, data)
    return len(data)


def save_to_sqlite(df, db_path):
    """Create the database/table if needed, then upsert the DataFrame.

    :param df: cleaned DataFrame
    :param db_path: path to the SQLite file
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        create_table(conn)
        rows_written = upsert_rows(conn, df)
        conn.commit()
    return rows_written
