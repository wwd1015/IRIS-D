"""Unit tests for src/dashboard/app_state.py"""

import pytest
import polars as pl


class TestAppStateInitialisation:
    def test_initialize_loads_data(self, app_state):
        assert len(app_state.facilities_df) > 0

    def test_default_portfolios_present(self, app_state):
        assert "Entire Commercial" in app_state.portfolios

    def test_default_portfolio_is_first(self, app_state):
        assert app_state.default_portfolio == app_state.available_portfolios[0]

    def test_latest_facilities_subset(self, app_state):
        assert app_state.latest_facilities["facility_id"].n_unique() == len(app_state.latest_facilities)

    def test_default_portfolios_use_filter_format(self, app_state):
        for name, criteria in app_state.portfolios.items():
            assert "filters" in criteria, f"Portfolio '{name}' missing 'filters' key"
            assert isinstance(criteria["filters"], list)


class TestGetFilteredData:
    def test_entire_commercial_returns_all(self, app_state):
        df = app_state.get_filtered_data("Entire Commercial")
        assert not df.is_empty()
        assert len(df) == len(app_state.latest_facilities)

    def test_missing_portfolio_returns_empty(self, app_state):
        df = app_state.get_filtered_data("Nonexistent Portfolio")
        assert df.is_empty()

    def test_custom_portfolio_multi_level_filter(self, app_state):
        app_state.portfolios["CRE Office"] = {
            "filters": [
                {"column": "lob", "values": ["CRE"]},
                {"column": "cre_property_type", "values": ["Office"]},
            ]
        }
        from src.dashboard.data.registry import DatasetRegistry
        DatasetRegistry.invalidate_all_caches()
        df = app_state.get_filtered_data("CRE Office")
        assert all(v == "CRE" for v in df["lob"].to_list())
        assert all(v == "Office" for v in df["cre_property_type"].to_list())

    def test_custom_portfolio_single_level_filter(self, app_state):
        app_state.portfolios["Tech Only"] = {
            "filters": [
                {"column": "lob", "values": ["Corporate Banking"]},
                {"column": "industry", "values": ["Technology"]},
            ]
        }
        from src.dashboard.data.registry import DatasetRegistry
        DatasetRegistry.invalidate_all_caches()
        df = app_state.get_filtered_data("Tech Only")
        assert all(v == "Technology" for v in df["industry"].to_list())

    def test_legacy_format_backward_compat(self, app_state):
        """Old flat-format portfolios should still work via migration shim."""
        app_state.portfolios["Legacy CB"] = {
            "lob": "Corporate Banking",
            "industry": "Technology",
            "property_type": None,
        }
        from src.dashboard.data.registry import DatasetRegistry
        DatasetRegistry.invalidate_all_caches()
        df = app_state.get_filtered_data("Legacy CB")
        assert all(v == "Corporate Banking" for v in df["lob"].to_list())
        assert all(v == "Technology" for v in df["industry"].to_list())


class TestSegmentationColumns:
    def test_returns_categorical_columns(self, app_state):
        cols = app_state.get_segmentation_columns()
        assert "lob" in cols
        assert "industry" in cols
        assert "cre_property_type" in cols
        assert "risk_category" in cols

    def test_excludes_numeric_and_date_columns(self, app_state):
        cols = app_state.get_segmentation_columns()
        assert "balance" not in cols
        assert "reporting_date" not in cols
        assert "facility_id" not in cols

    def test_get_column_display_name(self, app_state):
        assert app_state.get_column_display_name("lob") == "Line of Business"
        assert app_state.get_column_display_name("cre_property_type") == "Property Type"
        assert app_state.get_column_display_name("some_col") == "Some Col"

    def test_get_unique_values(self, app_state):
        vals = app_state.get_unique_values("lob")
        assert "Corporate Banking" in vals
        assert "CRE" in vals


class TestMigratePortfolioCriteria:
    def test_new_format_passthrough(self):
        from src.dashboard.app_state import AppState
        criteria = {"filters": [{"column": "lob", "values": ["CRE"]}]}
        assert AppState._migrate_criteria(criteria) is criteria

    def test_old_format_converted(self):
        from src.dashboard.app_state import AppState
        old = {"lob": "CRE", "industry": None, "property_type": "Office"}
        result = AppState._migrate_criteria(old)
        assert "filters" in result
        cols = [f["column"] for f in result["filters"]]
        assert "lob" in cols
        assert "cre_property_type" in cols


class TestMakeTabContext:
    def test_returns_tab_context(self, app_state):
        from src.dashboard.tabs.registry import TabContext
        ctx = app_state.make_tab_context()
        assert isinstance(ctx, TabContext)

    def test_selected_portfolio_default(self, app_state):
        ctx = app_state.make_tab_context()
        assert ctx.selected_portfolio == app_state.default_portfolio

    def test_selected_portfolio_override(self, app_state):
        ctx = app_state.make_tab_context("CRE")
        assert ctx.selected_portfolio == "CRE"

    def test_get_filtered_data_callable(self, app_state):
        ctx = app_state.make_tab_context()
        df = ctx.get_filtered_data("Entire Commercial")
        assert isinstance(df, pl.DataFrame)
        assert not df.is_empty()


class TestLoadUserPortfolios:
    def test_guest_loads_only_defaults(self, app_state):
        app_state.load_user_portfolios("Guest")
        assert set(app_state.portfolios.keys()) == {"Entire Commercial"}

    def test_custom_metrics_cleared_on_switch(self, app_state):
        app_state.custom_metrics["test_metric"] = "value"
        app_state.load_user_portfolios("Guest")
        assert app_state.custom_metrics == {}
