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
import pandas as pd

from . import config
from .auth import user_management
from .data.loader import load_facilities_data
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
        self.facilities_df: pd.DataFrame = pd.DataFrame()
        self.latest_facilities: pd.DataFrame = pd.DataFrame()
        self.default_portfolio: str = "Corporate Banking"
        self.available_portfolios: list[str] = []

    # ── Initialisation ───────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Load data from the database and set up default portfolios."""
        logger.info("=== IRIS-D - Loading Data ===")
        try:
            self.facilities_df = load_facilities_data()
            self.latest_facilities = (
                self.facilities_df
                .sort_values("reporting_date")
                .groupby("facility_id")
                .tail(1)
            )
            self.portfolios = config.DEFAULT_PORTFOLIOS.copy()
            self.available_portfolios = list(self.portfolios.keys())
            self.default_portfolio = (
                self.available_portfolios[0] if self.available_portfolios else "Corporate Banking"
            )
            logger.info("Loaded %d facility records", len(self.facilities_df))
        except Exception as exc:
            logger.error("Data loading failed: %s", exc)
            self._load_fallback_data()

    def _load_fallback_data(self) -> None:
        """Populate minimal stub data when the database is unavailable."""
        self.facilities_df = pd.DataFrame({
            "facility_id": ["F001", "F002", "F003"],
            "obligor_name": ["Test Company 1", "Test Company 2", "Test Company 3"],
            "obligor_rating": [5, 8, 12],
            "balance": [1_000_000, 2_000_000, 3_000_000],
            "lob": ["Corporate Banking", "CRE", "Corporate Banking"],
            "industry": ["Technology", None, "Healthcare"],
            "cre_property_type": [None, "Office", None],
            "reporting_date": ["2024-01-01", "2024-01-01", "2024-01-01"],
        })
        self.latest_facilities = self.facilities_df.copy()
        self.portfolios = {
            "Corporate Banking": {
                "lob": "Corporate Banking", "industry": None, "property_type": None,
            }
        }
        self.available_portfolios = list(self.portfolios.keys())
        self.default_portfolio = "Corporate Banking"

    # ── Core filtering ────────────────────────────────────────────────────────

    def _apply_portfolio_filter(self, portfolio_name: str, df: pd.DataFrame) -> pd.DataFrame:
        """Apply portfolio criteria to any arbitrary DataFrame.

        This is the single place where portfolio filter logic lives.
        Both :meth:`get_filtered_data` and :meth:`get_filtered_data_windowed`
        delegate here so the logic is never duplicated.

        Parameters
        ----------
        portfolio_name:
            Key into ``self.portfolios``.
        df:
            Input DataFrame — typically ``latest_facilities`` or a time-windowed
            version of it produced by :meth:`get_filtered_data_windowed`.

        Returns
        -------
        pd.DataFrame
            Filtered copy, or an empty DataFrame if the portfolio is unknown.
        """
        if portfolio_name not in self.portfolios:
            return pd.DataFrame()

        criteria = self.portfolios[portfolio_name]
        filtered = df.copy()

        if criteria.get("lob"):
            filtered = filtered[filtered["lob"] == criteria["lob"]]

        if criteria.get("lob") == "Corporate Banking" and criteria.get("industry"):
            ind = criteria["industry"]
            if isinstance(ind, list):
                filtered = filtered[filtered["industry"].astype(str).isin([str(i) for i in ind])]
            else:
                filtered = filtered[filtered["industry"] == ind]

        if criteria.get("lob") == "CRE" and criteria.get("property_type"):
            pt = criteria["property_type"]
            if isinstance(pt, list):
                filtered = filtered[
                    filtered["cre_property_type"].astype(str).isin([str(i) for i in pt])
                ]
            else:
                filtered = filtered[filtered["cre_property_type"] == pt]

        if criteria.get("obligors"):
            ob = criteria["obligors"]
            if isinstance(ob, list):
                filtered = filtered[
                    filtered["obligor_name"].astype(str).isin([str(i) for i in ob])
                ]
            else:
                filtered = filtered[filtered["obligor_name"] == ob]

        return filtered

    def get_filtered_data(self, portfolio_name: str) -> pd.DataFrame:
        """Return ``latest_facilities`` filtered by the named portfolio's criteria.

        This is the standard, single-snapshot filter.  Use it in callbacks and
        in ``render()`` methods via ``ctx.get_filtered_data``.
        """
        return self._apply_portfolio_filter(portfolio_name, self.latest_facilities.copy())

    def get_filtered_data_windowed(
        self, portfolio_name: str, n_quarters: int | None = None
    ) -> pd.DataFrame:
        """Return portfolio-filtered data restricted to the most-recent N quarters.

        Used by tabs with a time-window slider (e.g. Portfolio Summary).
        When *n_quarters* is ``None`` or exceeds the available history, the
        full history is returned — matching the behaviour of
        :meth:`get_filtered_data`.

        Parameters
        ----------
        portfolio_name:
            Key into ``self.portfolios``.
        n_quarters:
            How many of the most-recent reporting periods to include.
            ``None`` means all periods.

        Returns
        -------
        pd.DataFrame
            Portfolio-filtered snapshot using the last quarter visible in the
            time window.
        """
        fdf = self.facilities_df
        if n_quarters is not None:
            dates = sorted(fdf["reporting_date"].unique())
            if n_quarters < len(dates):
                cutoff_dates = dates[-n_quarters:]
                fdf = fdf[fdf["reporting_date"].isin(cutoff_dates)]

        # Derive "latest" snapshot within the window
        if fdf.empty:
            return pd.DataFrame()
        max_date = fdf["reporting_date"].max()
        latest_in_window = fdf[fdf["reporting_date"] == max_date]

        return self._apply_portfolio_filter(portfolio_name, latest_in_window)

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

    def save_user_data(self, username: str) -> None:
        """Persist custom portfolios and metrics for the given user."""
        custom_p = {k: v for k, v in self.portfolios.items() if k not in config.DEFAULT_PORTFOLIOS}
        user_management.save_user_data(username, custom_p, self.custom_metrics)


# Module-level singleton — imported by app.py and all callback modules.
app_state = AppState()
