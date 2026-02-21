"""
Data loading functions for IRIS-D.

Thin facade over the pluggable :class:`~.sources.DataSource` abstraction.
For the vast majority of code, calling :func:`load_facilities_data` is
sufficient.  Swap the underlying source via
:func:`~.sources.set_default_source` (useful in tests).
"""

from __future__ import annotations

import logging

import polars as pl

from .sources import get_default_source
from .dataset import Dataset
from .registry import DatasetRegistry

logger = logging.getLogger(__name__)


def load_dataset(name: str, id_column: str = "facility_id", date_column: str = "reporting_date") -> Dataset:
    """Load a named dataset from the active DataSource and register it.

    Builds both the full DataFrame and the latest-snapshot view, wraps
    them in a :class:`Dataset`, and registers it in the
    :class:`DatasetRegistry`.

    Returns
    -------
    Dataset
        The fully initialised and registered dataset.
    """
    source = get_default_source()
    full_df = source.load_facilities()

    # Derive latest snapshot: last record per entity by date
    latest_df = (
        full_df
        .sort(date_column)
        .group_by(id_column)
        .tail(1)
    )

    dataset = Dataset(
        name=name,
        full_df=full_df,
        latest_df=latest_df,
        id_column=id_column,
        date_column=date_column,
    )
    DatasetRegistry.register(dataset)
    return dataset


def load_facilities_data() -> pl.DataFrame:
    """Load all facility records, delegating to the active DataSource.

    Returns
    -------
    pl.DataFrame
        Processed and validated facility records.

    Raises
    ------
    FileNotFoundError
        If the underlying source cannot locate the database.
    Exception
        If both Pydantic-validated and raw loads fail.
    """
    return get_default_source().load_facilities()
