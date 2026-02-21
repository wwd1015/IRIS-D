"""Unit tests for src/dashboard/data/dataset.py and registry.py"""

import polars as pl
import pytest

from src.dashboard.data.dataset import Dataset
from src.dashboard.data.registry import DatasetRegistry


@pytest.fixture()
def sample_dataset():
    df = pl.DataFrame({
        "facility_id": ["F1", "F2", "F3", "F4"],
        "obligor_name": ["A", "B", "C", "D"],
        "lob": ["Corporate Banking", "Corporate Banking", "CRE", "CRE"],
        "industry": ["Tech", "Finance", None, None],
        "cre_property_type": [None, None, "Office", "Retail"],
        "balance": [1_000_000.0, 2_000_000.0, 3_000_000.0, 500_000.0],
        "reporting_date": ["2024-01-01", "2024-01-01", "2024-01-01", "2024-01-01"],
        "risk_category": ["Pass Rated", "Pass Rated", "Pass Rated", "Watch"],
    })
    return Dataset(name="test", full_df=df, latest_df=df)


@pytest.fixture()
def portfolios():
    return {
        "All": {"filters": []},
        "Corp": {"filters": [{"column": "lob", "values": ["Corporate Banking"]}]},
        "CRE Office": {"filters": [
            {"column": "lob", "values": ["CRE"]},
            {"column": "cre_property_type", "values": ["Office"]},
        ]},
    }


class TestDatasetFiltering:
    def test_no_filters_returns_all(self, sample_dataset, portfolios):
        df = sample_dataset.get_filtered("All", portfolios)
        assert len(df) == 4

    def test_single_filter(self, sample_dataset, portfolios):
        df = sample_dataset.get_filtered("Corp", portfolios)
        assert len(df) == 2
        assert all(v == "Corporate Banking" for v in df["lob"].to_list())

    def test_multi_level_filter(self, sample_dataset, portfolios):
        df = sample_dataset.get_filtered("CRE Office", portfolios)
        assert len(df) == 1
        assert df["facility_id"][0] == "F3"

    def test_missing_portfolio_returns_empty(self, sample_dataset, portfolios):
        df = sample_dataset.get_filtered("Nonexistent", portfolios)
        assert df.is_empty()

    def test_legacy_format(self, sample_dataset):
        portfolios = {"Legacy": {"lob": "CRE", "property_type": "Retail"}}
        df = sample_dataset.get_filtered("Legacy", portfolios)
        assert len(df) == 1
        assert df["facility_id"][0] == "F4"


class TestDatasetCache:
    def test_cache_hit(self, sample_dataset, portfolios):
        df1 = sample_dataset.get_filtered("Corp", portfolios)
        df2 = sample_dataset.get_filtered("Corp", portfolios)
        # Same object from cache
        assert df1 is df2

    def test_invalidate_clears_cache(self, sample_dataset, portfolios):
        df1 = sample_dataset.get_filtered("Corp", portfolios)
        sample_dataset.invalidate_cache()
        df2 = sample_dataset.get_filtered("Corp", portfolios)
        assert df1 is not df2
        assert df1.equals(df2)


class TestDatasetIntrospection:
    def test_segmentation_columns(self, sample_dataset):
        cols = sample_dataset.get_segmentation_columns()
        assert "lob" in cols
        assert "industry" in cols
        assert "cre_property_type" in cols
        assert "risk_category" in cols
        assert "balance" not in cols
        assert "facility_id" not in cols

    def test_unique_values(self, sample_dataset):
        vals = sample_dataset.get_unique_values("lob")
        assert "CRE" in vals
        assert "Corporate Banking" in vals

    def test_unique_values_missing_col(self, sample_dataset):
        assert sample_dataset.get_unique_values("nonexistent") == []


class TestDatasetRegistry:
    def test_register_and_get(self, sample_dataset):
        DatasetRegistry.clear()
        DatasetRegistry.register(sample_dataset)
        assert DatasetRegistry.get("test") is sample_dataset

    def test_get_missing_raises(self):
        DatasetRegistry.clear()
        with pytest.raises(KeyError):
            DatasetRegistry.get("missing")

    def test_has(self, sample_dataset):
        DatasetRegistry.clear()
        assert not DatasetRegistry.has("test")
        DatasetRegistry.register(sample_dataset)
        assert DatasetRegistry.has("test")

    def test_invalidate_all(self, sample_dataset, portfolios):
        DatasetRegistry.clear()
        DatasetRegistry.register(sample_dataset)
        sample_dataset.get_filtered("Corp", portfolios)
        assert len(sample_dataset._filter_cache) > 0
        DatasetRegistry.invalidate_all_caches()
        assert len(sample_dataset._filter_cache) == 0
