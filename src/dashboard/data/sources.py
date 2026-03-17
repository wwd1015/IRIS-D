"""
DataSource — pluggable data-source abstraction for IRIS-D.

Defines the :class:`DataSource` protocol so callers never depend on a
concrete SQLite implementation.  Swap in CSV, REST API, or in-memory
fixtures without touching anything outside this module.

Usage::

    source = SqliteDataSource("data/bank_risk.db")
    df = source.load_facilities()        # pl.DataFrame
    source.save_user_profiles(profiles)  # persists to JSON
"""

from __future__ import annotations

import logging
import os
import time
from typing import Protocol, runtime_checkable

import pandas as pd
import polars as pl
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# Cache TTL: 24 hours
_CACHE_TTL = 86_400


@runtime_checkable
class DataSource(Protocol):
    """Minimal interface every data source must satisfy."""

    def load_facilities(self) -> pl.DataFrame:
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
        self._cache: pl.DataFrame | None = None
        self._cache_ts: float = 0.0

    # ── DataSource interface ─────────────────────────────────────────────────

    def load_facilities(self) -> pl.DataFrame:
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

    _PYDANTIC_ROW_LIMIT = 50_000  # skip row-by-row validation above this

    def _load_with_validation(self) -> pl.DataFrame:
        """Attempt Pydantic-validated load; fall back to raw load on error.

        For large datasets (>50K rows), skip Pydantic to avoid slow
        row-by-row validation and use the raw load path directly.
        """
        # Quick row count check to avoid slow Pydantic on large datasets
        try:
            engine = create_engine(f"sqlite:///{self._db_path}")
            with engine.connect() as conn:
                count = conn.execute(text("SELECT COUNT(*) FROM raw_facilities")).scalar()
            if count > self._PYDANTIC_ROW_LIMIT:
                logger.info(
                    "Dataset has %d rows (>%d); skipping Pydantic validation.",
                    count, self._PYDANTIC_ROW_LIMIT,
                )
                return self._load_raw()
        except Exception:
            pass

        try:
            return self._load_pydantic()
        except Exception as exc:
            logger.warning(
                "Pydantic validation failed (%s). Falling back to raw load.", exc
            )
            return self._load_raw()

    def _load_pydantic(self) -> pl.DataFrame:
        from .models import FacilityDataset

        logger.info("Loading facilities with Pydantic validation from %s", self._db_path)
        engine = create_engine(f"sqlite:///{self._db_path}")
        raw_pdf = pd.read_sql(
            "SELECT * FROM raw_facilities ORDER BY facility_id, reporting_date", engine
        )
        logger.info("Loaded %d raw records; validating…", len(raw_pdf))
        dataset = FacilityDataset.from_dataframe(raw_pdf)
        df = dataset.to_dataframe()
        stats = dataset.get_summary_stats()
        logger.info(
            "Validated %d records — %d facilities, $%.1fM total balance",
            len(df), stats["total_facilities"], stats["total_balance_millions"],
        )
        return df

    def _load_raw(self) -> pl.DataFrame:
        """Direct SQL load without Pydantic — last resort fallback."""
        logger.info("Raw fallback load from %s", self._db_path)
        engine = create_engine(f"sqlite:///{self._db_path}")
        pdf = pd.read_sql(
            "SELECT * FROM raw_facilities ORDER BY facility_id, reporting_date", engine
        )
        pdf["balance_millions"] = pdf["balance"] / 1_000_000
        pdf["risk_category"] = pdf["obligor_rating"].apply(
            lambda x: (
                "Pass Rated" if x <= 13
                else "Watch" if x == 14
                else "Criticized" if x <= 16
                else "Defaulted"
            )
        )
        logger.info("Raw load complete — %d records", len(pdf))
        return pl.from_pandas(pdf)


class SnowflakeDataSource:
    """DataSource backed by a Snowflake connection.

    Requires ``snowflake-connector-python`` (install separately).
    Connection settings are read from :class:`config.SnowflakeSettings`,
    which reads from environment variables.  Authentication defaults to
    SSO (``externalbrowser``).

    Usage::

        # Set env vars, then:
        from ..data.sources import SnowflakeDataSource, set_default_source
        set_default_source(SnowflakeDataSource())
    """

    def __init__(self, sf_settings: object | None = None) -> None:
        from .. import config
        self._settings = sf_settings or config.settings.snowflake
        self._cache: pl.DataFrame | None = None
        self._cache_ts: float = 0.0
        self._cache_ttl = _CACHE_TTL

    def load_facilities(self) -> pl.DataFrame:
        now = time.time()
        if self._cache is not None and (now - self._cache_ts) < self._cache_ttl:
            logger.debug("Using cached Snowflake data")
            return self._cache

        try:
            import snowflake.connector  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "snowflake-connector-python is required for Snowflake data source. "
                "Install with:  pip install 'iris-d[snowflake]'"
            ) from None

        s = self._settings
        logger.info(
            "Connecting to Snowflake account=%s warehouse=%s db=%s schema=%s",
            s.account, s.warehouse, s.database, s.schema,
        )
        conn = snowflake.connector.connect(
            account=s.account,
            warehouse=s.warehouse,
            database=s.database,
            schema=s.schema,
            role=s.role or None,
            authenticator=s.authenticator,
        )

        try:
            cursor = conn.cursor()
            cursor.execute(s.query)
            pdf = cursor.fetch_pandas_all()
        finally:
            conn.close()

        # Same derived columns as SqliteDataSource._load_raw
        pdf["balance_millions"] = pdf["balance"] / 1_000_000
        pdf["risk_category"] = pdf["obligor_rating"].apply(
            lambda x: (
                "Pass Rated" if x <= 13
                else "Watch" if x == 14
                else "Criticized" if x <= 16
                else "Defaulted"
            )
        )

        df = pl.from_pandas(pdf)
        logger.info("Snowflake load complete — %d records", len(df))
        self._cache = df
        self._cache_ts = now
        return df

    def clear_cache(self) -> None:
        self._cache = None
        self._cache_ts = 0.0


class InMemoryDataSource:
    """Lightweight in-memory DataSource — primarily for testing.

    Pass a pre-built DataFrame (pandas or polars); ``load_facilities()``
    returns it as a polars DataFrame.
    """

    def __init__(self, df: pd.DataFrame | pl.DataFrame) -> None:
        if isinstance(df, pd.DataFrame):
            self._df = pl.from_pandas(df)
        else:
            self._df = df

    def load_facilities(self) -> pl.DataFrame:
        return self._df

    def clear_cache(self) -> None:
        pass  # nothing to clear


# Module-level default instance used by loader.py
_default_source: DataSource | None = None


def get_default_source() -> DataSource:
    """Return (creating on first call) the appropriate DataSource.

    Reads ``DATA_SOURCE_TYPE`` from config to choose between SQLite
    (default / demo) and Snowflake (production).
    """
    global _default_source
    if _default_source is None:
        from .. import config
        if config.DATA_SOURCE_TYPE == "snowflake":
            _default_source = SnowflakeDataSource()
        else:
            _default_source = SqliteDataSource()
    return _default_source


def set_default_source(source: DataSource) -> None:
    """Override the default source — useful in tests."""
    global _default_source
    _default_source = source
