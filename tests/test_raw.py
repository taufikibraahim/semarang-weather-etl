import pandas as pd

from src.pipeline.raw import save_raw


def test_save_raw_creates_file(tmp_path, raw_weather_df):
    path = save_raw(raw_weather_df, tmp_path / "raw")
    assert path.exists()
    assert path.suffix == ".parquet"


def test_save_raw_creates_missing_folder(tmp_path, raw_weather_df):
    target = tmp_path / "belum" / "ada"
    save_raw(raw_weather_df, target)
    assert target.is_dir()


def test_save_raw_roundtrip_keeps_data(tmp_path, raw_weather_df):
    path = save_raw(raw_weather_df, tmp_path)
    loaded = pd.read_parquet(path)
    pd.testing.assert_frame_equal(loaded, raw_weather_df)


def test_save_raw_filename_has_timestamp(tmp_path, raw_weather_df):
    path = save_raw(raw_weather_df, tmp_path)
    assert path.name.startswith("weather_")


def test_two_saves_do_not_overwrite(tmp_path, raw_weather_df):
    first = save_raw(raw_weather_df, tmp_path)
    second = save_raw(raw_weather_df, tmp_path)
    assert first != second
