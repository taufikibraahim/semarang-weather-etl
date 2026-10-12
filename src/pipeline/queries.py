"""Query analitik: membaca tabel ``hourly_weather`` menjadi DataFrame.

Modul ini hanya MEMBACA data. Penulisan ke database ada di ``load.py``.

Kolom ``date`` disimpan sebagai teks ``YYYY-MM-DD HH:MM:SS`` (WIB), sehingga:
    - ``substr(date, 1, 10)``  -> tanggal  (``YYYY-MM-DD``)
    - ``substr(date, 12, 2)``  -> jam      (``00`` sampai ``23``)

Catatan penting tentang data:
    - Data berisi 7 hari lalu dan 7 hari ke depan; hari pertama dan terakhir
      biasanya tidak lengkap 24 jam, dan nilai prakiraan bisa berubah antar
      run.
    - ``rain_mm`` boleh dijumlahkan; ``precip_probability_pct`` (persen) tidak
      boleh dijumlahkan, hanya dirata-ratakan atau diambil maksimumnya.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

HOURS_PER_DAY = 24


def open_readonly(db_path):
    """Open a read-only SQLite connection.

    Mode read-only mencegah query analitik mengubah data secara tidak sengaja.

    :param db_path: path to the SQLite file
    :return: sqlite3 connection (caller must close it)
    :raises FileNotFoundError: if the database file does not exist
    """
    path = Path(db_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    return sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)


def _complete_days_clause(complete_only):
    """Return a HAVING clause that keeps only days with all 24 hours."""
    if complete_only:
        return f"HAVING COUNT(*) = {HOURS_PER_DAY}"
    return ""


def data_overview(conn):
    """Summarize row count and date range.

    :param conn: SQLite connection
    :return: one-row DataFrame (row_count, first_date, last_date)
    """
    sql = """
        SELECT COUNT(*)  AS row_count,
               MIN(date) AS first_date,
               MAX(date) AS last_date
        FROM hourly_weather
    """
    return pd.read_sql_query(sql, conn)


def daily_temperature(conn, complete_only=True):
    """Average, minimum, and maximum temperature per day.

    :param conn: SQLite connection
    :param complete_only: keep only days that have all 24 hourly rows
    :return: DataFrame (day, hours, avg_temp_c, min_temp_c, max_temp_c)
    """
    sql = f"""
        SELECT substr(date, 1, 10)            AS day,
               COUNT(*)                       AS hours,
               ROUND(AVG(temperature_c), 1)   AS avg_temp_c,
               MIN(temperature_c)             AS min_temp_c,
               MAX(temperature_c)             AS max_temp_c
        FROM hourly_weather
        GROUP BY day
        {_complete_days_clause(complete_only)}
        ORDER BY day
    """
    return pd.read_sql_query(sql, conn)


def hottest_days(conn, limit=5, complete_only=True):
    """Days ranked by highest temperature reached.

    :param conn: SQLite connection
    :param limit: number of days to return
    :param complete_only: keep only days that have all 24 hourly rows
    :return: DataFrame (day, max_temp_c, avg_temp_c), hottest first
    """
    sql = f"""
        SELECT substr(date, 1, 10)            AS day,
               MAX(temperature_c)             AS max_temp_c,
               ROUND(AVG(temperature_c), 1)   AS avg_temp_c
        FROM hourly_weather
        GROUP BY day
        {_complete_days_clause(complete_only)}
        ORDER BY max_temp_c DESC, day
        LIMIT ?
    """
    return pd.read_sql_query(sql, conn, params=(limit,))


def most_humid_days(conn, limit=5, complete_only=True):
    """Days ranked by average relative humidity.

    :param conn: SQLite connection
    :param limit: number of days to return
    :param complete_only: keep only days that have all 24 hourly rows
    :return: DataFrame (day, avg_humidity_pct), most humid first
    """
    sql = f"""
        SELECT substr(date, 1, 10)            AS day,
               ROUND(AVG(humidity_pct), 1)    AS avg_humidity_pct
        FROM hourly_weather
        GROUP BY day
        {_complete_days_clause(complete_only)}
        ORDER BY avg_humidity_pct DESC, day
        LIMIT ?
    """
    return pd.read_sql_query(sql, conn, params=(limit,))


def daily_rain(conn, complete_only=True):
    """Total rain (mm) and peak precipitation probability per day.

    ``rain_mm`` is summed (an amount); ``precip_probability_pct`` uses MAX
    because percentages must not be added together.

    :param conn: SQLite connection
    :param complete_only: keep only days that have all 24 hourly rows
    :return: DataFrame (day, total_rain_mm, rainy_hours, max_precip_prob_pct)
    """
    sql = f"""
        SELECT substr(date, 1, 10)                 AS day,
               ROUND(SUM(rain_mm), 1)              AS total_rain_mm,
               SUM(CASE WHEN rain_mm > 0 THEN 1 ELSE 0 END) AS rainy_hours,
               MAX(precip_probability_pct)         AS max_precip_prob_pct
        FROM hourly_weather
        GROUP BY day
        {_complete_days_clause(complete_only)}
        ORDER BY day
    """
    return pd.read_sql_query(sql, conn)


def rain_by_hour(conn):
    """Average rain per hour of day (which hours are rainiest).

    Uses every row (days with fewer than 24 hours still contribute), because
    each row belongs to exactly one hour of the day.

    :param conn: SQLite connection
    :return: DataFrame (hour, avg_rain_mm, avg_precip_prob_pct), rainiest first
    """
    sql = """
        SELECT CAST(substr(date, 12, 2) AS INTEGER)  AS hour,
               ROUND(AVG(rain_mm), 3)                AS avg_rain_mm,
               ROUND(AVG(precip_probability_pct), 1) AS avg_precip_prob_pct
        FROM hourly_weather
        GROUP BY hour
        ORDER BY avg_rain_mm DESC, hour
    """
    return pd.read_sql_query(sql, conn)


def temperature_vs_daily_average(conn):
    """Difference between each hour's temperature and that day's average.

    Demonstrates a CTE plus a window function:
    ``AVG(...) OVER (PARTITION BY day)`` computes the daily average without
    collapsing rows, so every hourly row is kept.

    :param conn: SQLite connection
    :return: DataFrame (date, day, temperature_c, day_avg_c, diff_from_avg_c)
    """
    sql = """
        WITH hourly AS (
            SELECT date,
                   substr(date, 1, 10) AS day,
                   temperature_c
            FROM hourly_weather
        )
        SELECT date,
               day,
               temperature_c,
               ROUND(
                   AVG(temperature_c) OVER (PARTITION BY day),
                   2
               ) AS day_avg_c,
               ROUND(temperature_c
                     - AVG(temperature_c) OVER (PARTITION BY day), 2)
                   AS diff_from_avg_c
        FROM hourly
        ORDER BY date
    """
    return pd.read_sql_query(sql, conn)


def run_all(db_path):
    """Run every query and return the results in a dict.

    :param db_path: path to the SQLite file
    :return: dict mapping query name to DataFrame
    """
    with closing(open_readonly(db_path)) as conn:
        return {
            "overview": data_overview(conn),
            "daily_temperature": daily_temperature(conn),
            "hottest_days": hottest_days(conn),
            "most_humid_days": most_humid_days(conn),
            "daily_rain": daily_rain(conn),
            "rain_by_hour": rain_by_hour(conn),
            "temperature_vs_daily_average": temperature_vs_daily_average(conn),
        }
