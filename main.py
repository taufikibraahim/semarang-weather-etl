import logging

from src.pipeline.config import DB_PATH
from src.pipeline.extract import fetch_weather
from src.pipeline.load import save_to_sqlite
from src.pipeline.transform import response_to_dataframe, clean_weather

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def run():
    logger.info("Extract: Fetching weather data from Open-Meteo API")
    response = fetch_weather()
    
    logger.info("Transform: creating and cleaning DataFrame")
    df = clean_weather(response_to_dataframe(response))
    
    logger.info("Load: saving DataFrame to SQLite database")
    rows_written = save_to_sqlite(df, DB_PATH)

    logger.info("Finish: %d rows written to %s", rows_written, DB_PATH)


if __name__ == "__main__":
    run()