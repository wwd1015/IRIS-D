"""Unit tests for src/dashboard/app_state.py"""

import pytest
import pandas as pd


class TestAppStateInitialisation:
    def test_initialize_loads_data(self, app_state):
        assert len(app_state.facilities_df) > 0

    def test_default_portfolios_present(self, app_state):
        assert "Corporate Banking" in app_state.portfolios
        assert "CRE" in app_state.portfolios

    def test_default_portfolio_is_first(self, app_state):
        assert app_state.default_portfolio == app_state.available_portfolios[0]

    def test_latest_facilities_subset(self, app_state):
        # latest_facilities should have at most one row per facility_id
        assert app_state.latest_facilities["facility_id"].is_unique


class TestGetFilteredData:
    def test_corporate_banking_filter(self, app_state):
        df = app_state.get_filtered_data("Corporate Banking")
        assert set(df["lob"].unique()) == {"Corporate Banking"}

    def test_cre_filter(self, app_state):
        df = app_state.get_filtered_data("CRE")
        assert set(df["lob"].unique()) == {"CRE"}

    def test_missing_portfolio_returns_empty(self, app_state):
        df = app_state.get_filtered_data("Nonexistent Portfolio")
        assert df.empty

    def test_custom_portfolio_industry_filter(self, app_state):
        app_state.portfolios["Tech Only"] = {
            "lob": "Corporate Banking",
            "industry": "Technology",
            "property_type": None,
            "obligors": None,
        }
        df = app_state.get_filtered_data("Tech Only")
        assert all(df["industry"] == "Technology")

    def test_custom_portfolio_property_type_filter(self, app_state):
        app_state.portfolios["Office CRE"] = {
            "lob": "CRE",
            "industry": None,
            "property_type": "Office",
            "obligors": None,
        }
        df = app_state.get_filtered_data("Office CRE")
        assert all(df["cre_property_type"] == "Office")


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
        df = ctx.get_filtered_data("Corporate Banking")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty


class TestLoadUserPortfolios:
    def test_guest_loads_only_defaults(self, app_state):
        app_state.load_user_portfolios("Guest")
        assert set(app_state.portfolios.keys()) == {"Corporate Banking", "CRE"}

    def test_custom_metrics_cleared_on_switch(self, app_state):
        app_state.custom_metrics["test_metric"] = "value"
        app_state.load_user_portfolios("Guest")
        assert app_state.custom_metrics == {}
