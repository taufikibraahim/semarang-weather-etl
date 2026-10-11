import pytest

from src.pipeline.config import COLUMN_RENAMES
from src.pipeline.transform import clean_weather


def test_data_has_no_timezone_text(raw_weather_df):
    result = clean_weather(raw_weather_df)
    assert "+07.00" not in result["date"].iloc[0]
    assert result["date"].iloc[0] == "2026-10-10 00:00:00"
    
    
def test_columns_are_renamed(raw_weather_df):
    result = clean_weather(raw_weather_df)
    for new_name in COLUMN_RENAMES.values():
        assert new_name in result.columns
    for old_name in COLUMN_RENAMES:
        assert old_name not in result.columns
        
        
def test_input_is_not_modified(raw_weather_df):
    before = raw_weather_df.copy()
    clean_weather(raw_weather_df)
    assert raw_weather_df.equals(before)
    
    
def test_negative_rain_raises(raw_weather_df):
    raw_weather_df["rain"] = -0.1
    with pytest.raises(ValueError, match="rain"):
        clean_weather(raw_weather_df)
        
        
def test_probability_above_100_raises(raw_weather_df):
    raw_weather_df["precipitation_probability"] = 150.0
    with pytest.raises(ValueError, match="precip"):
        clean_weather(raw_weather_df)
        
        
def test_duplicates_date_raises(raw_weather_df):
    raw_weather_df.loc[1, "date"] = raw_weather_df.loc[0, "date"]
    with pytest.raises(ValueError, match="duplicate"):
        clean_weather(raw_weather_df)