"""
DatasetRegistry — central registry for named datasets.

Allows any part of the app to access a dataset by name without
coupling to the loading logic.
"""

from __future__ import annotations

import logging

from .dataset import Dataset

logger = logging.getLogger(__name__)


class DatasetRegistry:
    """Singleton-style registry mapping dataset names to Dataset instances."""

    _datasets: dict[str, Dataset] = {}

    @classmethod
    def register(cls, dataset: Dataset) -> None:
        """Register a dataset. Overwrites any previous with the same name."""
        logger.info("Registered dataset '%s' (%d rows)", dataset.name, len(dataset.full_df))
        cls._datasets[dataset.name] = dataset

    @classmethod
    def get(cls, name: str) -> Dataset:
        """Retrieve a dataset by name.

        Raises
        ------
        KeyError
            If no dataset with that name is registered.
        """
        if name not in cls._datasets:
            raise KeyError(f"Dataset '{name}' not registered. Available: {list(cls._datasets.keys())}")
        return cls._datasets[name]

    @classmethod
    def has(cls, name: str) -> bool:
        """Check whether a dataset is registered."""
        return name in cls._datasets

    @classmethod
    def invalidate_all_caches(cls) -> None:
        """Clear filter caches on every registered dataset."""
        for ds in cls._datasets.values():
            ds.invalidate_cache()

    @classmethod
    def clear(cls) -> None:
        """Remove all registered datasets (useful in tests)."""
        cls._datasets.clear()
