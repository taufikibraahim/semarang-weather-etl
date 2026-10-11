from datetime import UTC, datetime
from pathlib import Path


def save_raw(df, raw_dir):
    """Save the unmodified DataFrame as a timestamped Parquet file.

    :param df: DataFrame straight from ``response_to_dataframe``
    :param raw_dir: directory for raw files
    :return: path of the saved file
    """

    # 1. Make sure directory available
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 2. Make file parquet with now datetime
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    file_path = raw_dir / f"weather_raw_{timestamp}.parquet"

    # 3. Save DataFrame to parquet
    df.to_parquet(file_path, index=False)

    # 4. Return the saved file path
    return file_path
