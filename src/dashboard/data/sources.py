"""
DataSource — pluggable data-source abstraction for IRIS-D.

Defines the :class:`DataSource` protocol so callers never depend on a
concrete SQLite implementation.  Swap in CSV, REST API, or in-memory
fixtures without touching anything outside this module.

Usage::

    source = SqliteDataSource("data/bank_risk.db")
    df = source.load_facilities()        # pd.DataFrame
    source.save_user_profiles(profiles)  # persists to JSON
"""

from __future__ import annotations

import logging
import os
import time
from typing import Protocol, runtime_checkable

import pandas as pd
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

# Cache TTL: 24 hours
_CACHE_TTL = 86_400


@runtime_checkable
class DataSource(Protocol):
    """Minimal interface every data source must satisfy."""

    def load_facilities(self) -> pd.DataFrame:
        """Return all facility records as a DataFrame."""
        ...

    def clear_cache(self) -> None:
        """Invalidate any cached data so the next load_facilities() is fresh."""
        ...


class SqliteDataSource:
    """Concrete DataSource backed by a SQLite database.

    Parameters
    ----------
    db_path:
        Path to the SQLite ``.db`` file.  Defaults to ``data/bank_risk.db``.
    cache_ttl:
        Seconds before the in-memory cache is considered stale.
    """

    def __init__(self, db_path: str | None = None, cache_ttl: int = _CACHE_TTL) -> None:
        from .. import config
        self._db_path = db_path or config.DATABASE_PATH
        self._cache_ttl = cache_ttl
        self._cache: pd.DataFrame | None = None
        self._cache_ts: float = 0.0

    # ── DataSource interface ─────────────────────────────────────────────────

    def load_facilities(self) -> pd.DataFrame:
        """Load (and cache) facilities from SQLite, with Pydantic validation."""
        now = time.time()
        if self._cache is not None and (now - self._cache_ts) < self._cache_ttl:
            logger.debug("Using cached facilities data")
            return self._cache

        if not os.path.exists(self._db_path):
            raise FileNotFoundError(
                f"Database not found: {self._db_path}. "
                "Please run db_data_generator.py first."
            )

        df = self._load_with_validation()
        self._cache = df
        self._cache_ts = now
        return df

    def clear_cache(self) -> None:
        self._cache = None
        self._cache_ts = 0.0

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _load_with_validation(self) -> pd.DataFrame:
        """Attempt Pydantic-validated load; fall back to raw load on error."""
        try:
            return self._load_pydantic()
        except Exception as exc:
            logger.warning(
                "Pydantic validation failed (%s). Falling back to raw load.", exc
            )
            return self._load_raw()

    def _load_pydantic(self) -> pd.DataFrame:
        from .models import FacilityDataset

        logger.info("Loading facilities with Pydantic validation from %s", self._db_path)
        engine = create_engine(f"sqlite:///{self._db_path}")
        raw_df = pd.read_sql(
            "SELECT * FROM raw_facilities ORDER BY facility_id, reporting_date", engine
        )
        logger.info("Loaded %d raw records; validating…", len(raw_df))
        dataset = FacilityDataset.from_dataframe(raw_df)
        df = dataset.to_dataframe()
        stats = dataset.get_summary_stats()
        logger.info(
            "Validated %d records — %d facilities, $%.1fM total balance",
            len(df), stats["total_facilities"], stats["total_balance_millions"],
        )
        return df

    def _load_raw(self) -> pd.DataFrame:
        """Direct SQL load without Pydantic — last resort fallback."""
        logger.info("Raw fallback load from %s", self._db_path)
        engine = create_engine(f"sqlite:///{self._db_path}")
        df = pd.read_sql(
            "SELECT * FROM raw_facilities ORDER BY facility_id, reporting_date", engine
        )
        df["balance_millions"] = df["balance"] / 1_000_000
        df["risk_category"] = df["obligor_rating"].apply(
            lambda x: (
                "Pass Rated" if x <= 13
                else "Watch" if x == 14
                else "Criticized" if x <= 16
                else "Defaulted"
            )
        )
        logger.info("Raw load complete — %d records", len(df))
        return df


class InMemoryDataSource:
    """Lightweight in-memory DataSource — primarily for testing.

    Pass a pre-built DataFrame; ``load_facilities()`` returns it immediately.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def load_facilities(self) -> pd.DataFrame:
        return self._df.copy()

    def clear_cache(self) -> None:
        pass  # nothing to clear


# Module-level default instance used by loader.py
_default_source: DataSource | None = None


def get_default_source() -> DataSource:
    """Return (creating on first call) the module-level SqliteDataSource."""
    global _default_source
    if _default_source is None:
        _default_source = SqliteDataSource()
    return _default_source


def set_default_source(source: DataSource) -> None:
    """Override the default source — useful in tests."""
    global _default_source
    _default_source = source
