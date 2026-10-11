import logging

from src.pipeline.config import DB_PATH, RAW_DIR
from src.pipeline.extract import fetch_weather
from src.pipeline.load import save_to_sqlite
from src.pipeline.logging_config import setup_logging
from src.pipeline.raw import save_raw
from src.pipeline.transform import clean_weather, response_to_dataframe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run():
    logger.info("Extract: fetching weather data from Open-Meteo")
    response = fetch_weather()

    logger.info("Raw: converting response to DataFrame and saving as Parquet")
    raw_df = response_to_dataframe(response)
    raw_path = save_raw(raw_df, RAW_DIR)
    logger.info("Raw: saved %d rows to %s", len(raw_df), raw_path)

    logger.info("Transform: cleaning DataFrame")
    df = clean_weather(raw_df)

    logger.info("Load: saving DataFrame to SQLite")
    rows_written = save_to_sqlite(df, DB_PATH)

    logger.info("Finish: %d rows written to %s", rows_written, DB_PATH)


if __name__ == "__main__":
    setup_logging()
    try:
        run()
    except Exception:
        logger.exception("Pipeline failed")
        raise
