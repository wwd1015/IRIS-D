"""
Dataset — generic named dataset with filtering and caching.

A Dataset wraps a polars DataFrame (full history + latest snapshot) and
provides portfolio-based filtering with an internal cache so that repeated
calls with the same portfolio return instantly.
"""

from __future__ import annotations

import logging
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)


class Dataset:
    """One named dataset with full + latest snapshots and a filter cache.

    Parameters
    ----------
    name:
        Human-readable identifier, e.g. ``"facilities"``.
    full_df:
        All periods / snapshots.
    latest_df:
        Most-recent snapshot per entity (derived from *full_df*).
    id_column:
        Column identifying unique entities, e.g. ``"facility_id"``.
    date_column:
        Column identifying the reporting period, e.g. ``"reporting_date"``.
    """

    def __init__(
        self,
        name: str,
        full_df: pl.DataFrame,
        latest_df: pl.DataFrame,
        id_column: str = "facility_id",
        date_column: str = "reporting_date",
    ) -> None:
        self.name = name
        self.full_df = full_df
        self.latest_df = latest_df
        self.id_column = id_column
        self.date_column = date_column
        self._filter_cache: dict[tuple, pl.DataFrame] = {}

    # ── Filtered access ───────────────────────────────────────────────────

    @staticmethod
    def _migrate_criteria(criteria: dict) -> dict:
        """Convert old flat-format criteria to new filter-list format."""
        if "filters" in criteria:
            return criteria
        filters: list[dict[str, Any]] = []
        if criteria.get("lob"):
            filters.append({"column": "lob", "values": [criteria["lob"]]})
        if criteria.get("industry"):
            ind = criteria["industry"]
            filters.append({"column": "industry", "values": ind if isinstance(ind, list) else [ind]})
        if criteria.get("property_type"):
            pt = criteria["property_type"]
            filters.append({"column": "cre_property_type", "values": pt if isinstance(pt, list) else [pt]})
        if criteria.get("obligors"):
            ob = criteria["obligors"]
            filters.append({"column": "obligor_name", "values": ob if isinstance(ob, list) else [ob]})
        return {"filters": filters}

    def _apply_filter(self, portfolio_name: str, portfolios: dict, df: pl.DataFrame) -> pl.DataFrame:
        """Apply portfolio criteria to a DataFrame."""
        if portfolio_name not in portfolios:
            return df.clear()

        criteria = self._migrate_criteria(portfolios[portfolio_name])
        filtered = df

        for level in criteria.get("filters", []):
            col = level.get("column")
            vals = level.get("values", [])
            if col and vals and col in filtered.columns:
                str_vals = [str(v) for v in vals]
                filtered = filtered.filter(pl.col(col).cast(pl.Utf8).is_in(str_vals))

        return filtered

    def get_filtered(self, portfolio_name: str, portfolios: dict) -> pl.DataFrame:
        """Return latest_df filtered by portfolio criteria, with caching."""
        key = ("latest", portfolio_name)
        if key in self._filter_cache:
            return self._filter_cache[key]
        result = self._apply_filter(portfolio_name, portfolios, self.latest_df)
        self._filter_cache[key] = result
        return result

    def get_filtered_windowed(
        self, portfolio_name: str, portfolios: dict, n_periods: int | None = None
    ) -> pl.DataFrame:
        """Return windowed + filtered data, with caching."""
        key = ("windowed", portfolio_name, n_periods)
        if key in self._filter_cache:
            return self._filter_cache[key]

        fdf = self.full_df
        if n_periods is not None:
            dates = fdf[self.date_column].unique().sort()
            if n_periods < len(dates):
                cutoff_dates = dates.tail(n_periods)
                fdf = fdf.filter(pl.col(self.date_column).is_in(cutoff_dates))

        if fdf.is_empty():
            result = fdf.clear()
        else:
            max_date = fdf[self.date_column].max()
            latest_in_window = fdf.filter(pl.col(self.date_column) == max_date)
            result = self._apply_filter(portfolio_name, portfolios, latest_in_window)

        self._filter_cache[key] = result
        return result

    def invalidate_cache(self) -> None:
        """Clear all cached filter results."""
        self._filter_cache.clear()

    # ── Introspection ─────────────────────────────────────────────────────

    _EXCLUDE_ID_DATE = frozenset({
        "facility_id", "reporting_date", "origination_date", "maturity_date",
    })

    def get_segmentation_columns(self) -> list[str]:
        """Auto-detect categorical columns suitable for filtering."""
        if self.latest_df.is_empty():
            return []
        cols: list[str] = []
        for col in self.latest_df.columns:
            if col in self._EXCLUDE_ID_DATE:
                continue
            dtype = self.latest_df[col].dtype
            if dtype == pl.Utf8 or dtype == pl.Categorical or col == "risk_category":
                if col not in cols:
                    cols.append(col)
        return cols

    def get_unique_values(self, column: str, df: pl.DataFrame | None = None) -> list[str]:
        """Sorted unique non-null values for a column."""
        source = df if df is not None else self.latest_df
        if column not in source.columns:
            return []
        return sorted(
            source[column].drop_nulls().unique().cast(pl.Utf8).to_list()
        )
