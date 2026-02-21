"""Unit tests for src/dashboard/data/sources.py"""

import pandas as pd
import polars as pl
import pytest

from src.dashboard.data.sources import (
    DataSource, InMemoryDataSource, SqliteDataSource,
    get_default_source, set_default_source,
)


@pytest.fixture()
def sample_df():
    return pd.DataFrame({
        "facility_id": ["A1", "A2"],
        "balance": [100.0, 200.0],
        "lob": ["Corporate Banking", "CRE"],
    })


class TestInMemoryDataSource:
    def test_load_returns_polars(self, sample_df):
        source = InMemoryDataSource(sample_df)
        result = source.load_facilities()
        assert isinstance(result, pl.DataFrame)

    def test_load_data_matches(self, sample_df):
        source = InMemoryDataSource(sample_df)
        result = source.load_facilities()
        assert result["facility_id"].to_list() == ["A1", "A2"]
        assert result["balance"].to_list() == [100.0, 200.0]

    def test_polars_immutability(self, sample_df):
        source = InMemoryDataSource(sample_df)
        result = source.load_facilities()
        # polars DataFrames are immutable — same object returned
        result2 = source.load_facilities()
        assert result.equals(result2)

    def test_accepts_polars_input(self):
        pldf = pl.DataFrame({"facility_id": ["X1"], "balance": [50.0], "lob": ["CRE"]})
        source = InMemoryDataSource(pldf)
        result = source.load_facilities()
        assert result["facility_id"].to_list() == ["X1"]

    def test_implements_protocol(self, sample_df):
        source = InMemoryDataSource(sample_df)
        assert isinstance(source, DataSource)

    def test_clear_cache_no_op(self, sample_df):
        source = InMemoryDataSource(sample_df)
        source.clear_cache()  # should not raise
        result = source.load_facilities()
        assert result["balance"].to_list() == [100.0, 200.0]


class TestDefaultSource:
    def test_set_and_get_default_source(self, sample_df):
        custom = InMemoryDataSource(sample_df)
        set_default_source(custom)
        assert get_default_source() is custom

    def test_default_source_returns_data(self, minimal_df):
        source = InMemoryDataSource(minimal_df)
        set_default_source(source)
        df = get_default_source().load_facilities()
        assert len(df) == len(minimal_df)


class TestSqliteDataSourceMissingFile:
    def test_raises_file_not_found(self, tmp_path):
        source = SqliteDataSource(db_path=str(tmp_path / "nonexistent.db"))
        with pytest.raises(FileNotFoundError):
            source.load_facilities()

    def test_clear_cache_resets_state(self, tmp_path):
        source = SqliteDataSource(db_path=str(tmp_path / "nonexistent.db"))
        source._cache = pl.DataFrame({"x": [1]})
        source._cache_ts = 9_999_999_999.0
        source.clear_cache()
        assert source._cache is None
        assert source._cache_ts == 0.0
