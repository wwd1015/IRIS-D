"""
AppState — encapsulates all mutable application state for IRIS-D.

Replaces the scattered module-level globals in app.py with a single
object that owns portfolios, custom_metrics, and the loaded data.
Provides filtering helpers and make_tab_context() as methods so
callbacks never need the ``global`` keyword.

Callback authoring pattern
--------------------------
* In ``render()`` / ``render_content()`` methods — use the :class:`TabContext`
  passed in (``ctx.get_filtered_data``, ``ctx.facilities_df``, etc.).

* In ``register_callbacks(app)`` — import the module-level singleton at the
  top of the method body::

      def register_callbacks(self, app) -> None:
          from ..app_state import app_state

          @callback(Output("my-chart", "figure"),
                    Input("universal-portfolio-dropdown", "value"))
          def update(portfolio):
              df = app_state.get_filtered_data(portfolio or app_state.default_portfolio)
              ...
"""

from __future__ import annotations

import logging

import polars as pl

from . import config
from .auth import user_management
from .data.loader import load_dataset, load_facilities_data
from .data.dataset import Dataset
from .data.registry import DatasetRegistry
from .tabs.registry import TabContext

logger = logging.getLogger(__name__)


class AppState:
    """Singleton-style container for all mutable application state.

    Typical usage::

        state = AppState()
        state.initialize()            # load data & set defaults
        ctx = state.make_tab_context("Corporate Banking")
    """

    def __init__(self) -> None:
        self.portfolios: dict = {}
        self.custom_metrics: dict = {}
        self._dataset: Dataset | None = None
        self.default_portfolio: str = "Entire Commercial"
        self.available_portfolios: list[str] = []

    # ── Properties delegating to Dataset ──────────────────────────────────

    @property
    def facilities_df(self) -> pl.DataFrame:
        if self._dataset is not None:
            return self._dataset.full_df
        return pl.DataFrame()

    @facilities_df.setter
    def facilities_df(self, value: pl.DataFrame) -> None:
        # Support direct assignment for fallback / tests
        if self._dataset is not None:
            self._dataset.full_df = value
        else:
            self._dataset = Dataset(
                name="facilities", full_df=value,
                latest_df=value,
            )

    @property
    def latest_facilities(self) -> pl.DataFrame:
        if self._dataset is not None:
            return self._dataset.latest_df
        return pl.DataFrame()

    @latest_facilities.setter
    def latest_facilities(self, value: pl.DataFrame) -> None:
        if self._dataset is not None:
            self._dataset.latest_df = value

    # ── Initialisation ───────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Load data from the database and set up default portfolios."""
        logger.info("=== IRIS-D - Loading Data ===")
        try:
            self._dataset = load_dataset("facilities")
            self.portfolios = config.DEFAULT_PORTFOLIOS.copy()
            self.available_portfolios = list(self.portfolios.keys())
            self.default_portfolio = (
                self.available_portfolios[0] if self.available_portfolios else "Entire Commercial"
            )
            logger.info("Loaded %d facility records", len(self.facilities_df))
            # Load current user's saved portfolios
            current_user = user_management.get_current_user()
            if current_user:
                self.load_user_portfolios(current_user)
        except Exception as exc:
            logger.error("Data loading failed: %s", exc)
            self._load_fallback_data()

    def _load_fallback_data(self) -> None:
        """Populate minimal stub data when the database is unavailable."""
        fallback = pl.DataFrame({
            "facility_id": ["F001", "F002", "F003"],
            "obligor_name": ["Test Company 1", "Test Company 2", "Test Company 3"],
            "obligor_rating": [5, 8, 12],
            "balance": [1_000_000.0, 2_000_000.0, 3_000_000.0],
            "lob": ["Corporate Banking", "CRE", "Corporate Banking"],
            "industry": ["Technology", None, "Healthcare"],
            "cre_property_type": [None, "Office", None],
            "reporting_date": ["2024-01-01", "2024-01-01", "2024-01-01"],
        })
        self._dataset = Dataset(
            name="facilities",
            full_df=fallback,
            latest_df=fallback,
        )
        DatasetRegistry.register(self._dataset)
        self.portfolios = {
            "Entire Commercial": {"filters": []},
        }
        self.available_portfolios = list(self.portfolios.keys())
        self.default_portfolio = "Entire Commercial"

    # ── Core filtering ────────────────────────────────────────────────────────

    # ── Column display names ────────────────────────────────────────────────

    _COLUMN_DISPLAY_NAMES: dict[str, str] = {
        "lob": "Line of Business",
        "industry": "Industry",
        "cre_property_type": "Property Type",
        "obligor_name": "Obligor",
        "risk_category": "Risk Category",
        "obligor_rating": "Obligor Rating",
    }

    def get_segmentation_columns(self) -> list[str]:
        """Return categorical column names suitable for portfolio segmentation."""
        if self._dataset is None:
            return []
        return self._dataset.get_segmentation_columns()

    @staticmethod
    def get_column_display_name(col: str) -> str:
        """Return a user-friendly label for a raw column name."""
        if col in AppState._COLUMN_DISPLAY_NAMES:
            return AppState._COLUMN_DISPLAY_NAMES[col]
        return col.replace("_", " ").title()

    def get_unique_values(self, column: str, df: pl.DataFrame | None = None) -> list[str]:
        """Return sorted unique non-null values for a column."""
        if self._dataset is None:
            return []
        return self._dataset.get_unique_values(column, df)

    # ── Core filtering ────────────────────────────────────────────────────────

    @staticmethod
    def _migrate_criteria(criteria: dict) -> dict:
        """Convert old flat-format criteria to new filter-list format."""
        return Dataset._migrate_criteria(criteria)

    def _apply_portfolio_filter(self, portfolio_name: str, df: pl.DataFrame) -> pl.DataFrame:
        """Apply portfolio criteria to any arbitrary DataFrame.

        Supports both the new ``{"filters": [...]}`` format and the legacy
        flat format (auto-migrated on the fly).
        """
        if self._dataset is None:
            return pl.DataFrame()
        return self._dataset._apply_filter(portfolio_name, self.portfolios, df)

    def get_filtered_data(self, portfolio_name: str) -> pl.DataFrame:
        """Return ``latest_facilities`` filtered by the named portfolio's criteria."""
        if self._dataset is None:
            return pl.DataFrame()
        return self._dataset.get_filtered(portfolio_name, self.portfolios)

    def get_filtered_data_windowed(
        self, portfolio_name: str, n_periods: int | None = None
    ) -> pl.DataFrame:
        """Return portfolio-filtered data restricted to the most-recent N periods."""
        if self._dataset is None:
            return pl.DataFrame()
        return self._dataset.get_filtered_windowed(portfolio_name, self.portfolios, n_periods)

    # ── Tab context ──────────────────────────────────────────────────────────

    def make_tab_context(self, selected_portfolio: str | None = None) -> TabContext:
        """Build a :class:`TabContext` reflecting the current state."""
        sel = selected_portfolio or self.default_portfolio
        return TabContext(
            selected_portfolio=sel,
            available_portfolios=list(self.portfolios.keys()),
            portfolios=self.portfolios,
            facilities_df=self.facilities_df,
            latest_facilities=self.latest_facilities,
            custom_metrics=self.custom_metrics,
            get_filtered_data=self.get_filtered_data,
        )

    # ── User data helpers ────────────────────────────────────────────────────

    def load_user_portfolios(self, username: str) -> None:
        """Reload portfolios and custom_metrics for the given user."""
        self.portfolios.clear()
        self.custom_metrics.clear()
        self.portfolios.update(config.DEFAULT_PORTFOLIOS.copy())
        user_data = user_management.get_user_data(username)
        user_portfolios = user_data.get("portfolios", {})
        if user_portfolios:
            self.portfolios.update(user_portfolios)
        self.custom_metrics.update(user_data.get("custom_metrics", {}))
        self.available_portfolios = list(self.portfolios.keys())
        # Invalidate caches when portfolios change
        DatasetRegistry.invalidate_all_caches()

    def save_user_data(self, username: str) -> None:
        """Persist custom portfolios and metrics for the given user."""
        custom_p = {k: v for k, v in self.portfolios.items() if k not in config.DEFAULT_PORTFOLIOS}
        user_management.save_user_data(username, custom_p, self.custom_metrics)
        # Invalidate caches after portfolio changes
        DatasetRegistry.invalidate_all_caches()


# Module-level singleton — imported by app.py and all callback modules.
app_state = AppState()
