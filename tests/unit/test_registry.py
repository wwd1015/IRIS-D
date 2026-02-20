"""Unit tests for src/dashboard/tabs/registry.py"""

import pytest

from src.dashboard.tabs.registry import (
    BaseTab, TabContext, register_tab, get_all_tabs, get_tab, _TABS as _TAB_REGISTRY,
)


# ---------------------------------------------------------------------------
# Minimal concrete tab for testing
# ---------------------------------------------------------------------------

class _PingTab(BaseTab):
    id = "ping-test"
    label = "Ping"
    order = 999  # high order → won't collide with real tabs

    def render(self, ctx: TabContext):
        from dash import html
        return html.Div("ping")


class _PongTab(BaseTab):
    id = "pong-test"
    label = "Pong"
    order = 1000
    required_roles = ["Corp SCO"]

    def render(self, ctx: TabContext):
        from dash import html
        return html.Div("pong")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTabRegistration:
    def setup_method(self):
        """Register test tabs before each test."""
        # Avoid duplicate registration errors
        if "ping-test" not in _TAB_REGISTRY:
            register_tab(_PingTab())
        if "pong-test" not in _TAB_REGISTRY:
            register_tab(_PongTab())

    def test_get_tab_returns_correct_instance(self):
        tab = get_tab("ping-test")
        assert tab is not None
        assert tab.id == "ping-test"

    def test_get_tab_unknown_returns_none(self):
        assert get_tab("does-not-exist") is None

    def test_get_all_tabs_returns_list(self):
        tabs = get_all_tabs()
        assert isinstance(tabs, list)
        assert any(t.id == "ping-test" for t in tabs)

    def test_tabs_ordered_by_order_attribute(self):
        tabs = get_all_tabs()
        orders = [t.order for t in tabs]
        assert orders == sorted(orders)

    def test_duplicate_registration_raises(self):
        with pytest.raises(ValueError, match="already registered"):
            register_tab(_PingTab())
