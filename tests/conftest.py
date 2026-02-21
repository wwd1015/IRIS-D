"""
Shared pytest fixtures for IRIS-D tests.

Provides:
- ``minimal_df``  — tiny in-memory facilities DataFrame (no DB required)
- ``app_state``   — initialised AppState backed by in-memory data
- ``tab_context`` — TabContext built from the test AppState
"""

from __future__ import annotations

import sys
import os

# Ensure src/ is on the path when tests are run from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd
import polars as pl
import pytest

from src.dashboard import config
from src.dashboard.app_state import AppState
from src.dashboard.data.sources import InMemoryDataSource, set_default_source
from src.dashboard.data.registry import DatasetRegistry


# ---------------------------------------------------------------------------
# Minimal dataset fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def minimal_df() -> pd.DataFrame:
    """Eight-row facilities DataFrame covering both LOBs (pandas for backward compat)."""
    return pd.DataFrame({
        "facility_id": ["F001", "F002", "F003", "F004", "F005", "F006", "F007", "F008"],
        "obligor_name": [
            "Alpha Corp", "Beta Corp", "Gamma Corp", "Delta Corp",
            "CRE One", "CRE Two", "CRE Three", "CRE Four",
        ],
        "obligor_rating": [3, 7, 13, 14, 5, 10, 15, 17],
        "balance": [
            1_000_000, 2_000_000, 3_000_000, 500_000,
            4_000_000, 1_500_000, 2_500_000, 750_000,
        ],
        "lob": [
            "Corporate Banking", "Corporate Banking", "Corporate Banking", "Corporate Banking",
            "CRE", "CRE", "CRE", "CRE",
        ],
        "industry": ["Technology", "Finance", "Healthcare", "Energy", None, None, None, None],
        "cre_property_type": [None, None, None, None, "Office", "Retail", "Industrial", "Office"],
        "reporting_date": ["2024-01-01"] * 8,
        "origination_date": ["2020-01-01"] * 8,
        "maturity_date": ["2026-01-01"] * 8,
        "balance_millions": [1.0, 2.0, 3.0, 0.5, 4.0, 1.5, 2.5, 0.75],
        "risk_category": [
            "Pass Rated", "Pass Rated", "Pass Rated", "Watch",
            "Pass Rated", "Pass Rated", "Criticized", "Defaulted",
        ],
    })


# ---------------------------------------------------------------------------
# AppState fixture (backed by in-memory data — no DB required)
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_state(minimal_df) -> AppState:
    """Return an AppState initialised with in-memory test data."""
    DatasetRegistry.clear()
    source = InMemoryDataSource(minimal_df)
    set_default_source(source)

    state = AppState()
    state.initialize()
    return state


# ---------------------------------------------------------------------------
# TabContext fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def tab_context(app_state):
    """Return a TabContext for the default portfolio."""
    return app_state.make_tab_context()
