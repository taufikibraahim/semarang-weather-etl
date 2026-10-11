"""Konfigurasi logging: terminal + file berputar."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


def setup_logging(log_file="logs/pipeline.log"):
    """Configure logging to both console and a rotating file.

    :param log_file: path of the log file
    """
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    console_handler = logging.StreamHandler()

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[file_handler, console_handler],
    )
