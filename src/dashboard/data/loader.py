"""
Data loading functions for IRIS-D.

Thin façade over the pluggable :class:`~.sources.DataSource` abstraction.
For the vast majority of code, calling :func:`load_facilities_data` is
sufficient.  Swap the underlying source via
:func:`~.sources.set_default_source` (useful in tests).
"""

from __future__ import annotations

import logging

import pandas as pd

from .sources import get_default_source

logger = logging.getLogger(__name__)


def load_facilities_data() -> pd.DataFrame:
    """Load all facility records, delegating to the active DataSource.

    Returns
    -------
    pd.DataFrame
        Processed and validated facility records.

    Raises
    ------
    FileNotFoundError
        If the underlying source cannot locate the database.
    Exception
        If both Pydantic-validated and raw loads fail.
    """
    return get_default_source().load_facilities()
