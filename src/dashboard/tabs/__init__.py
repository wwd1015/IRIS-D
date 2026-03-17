"""
Tab registry system for IRIS-D — with auto-discovery.

Every Python file in this directory that is not prefixed with ``_`` is
imported automatically at startup, causing any :func:`register_tab` calls
at module level to fire without requiring manual imports in ``app.py``.

To create a new tab:
  1. Create a new file in ``src/dashboard/tabs/``  (e.g. ``my_tab.py``)
  2. Subclass :class:`BaseTab` and implement the required methods
  3. Call ``register_tab(MyTab())`` at module level

That's it — no other files need to be edited.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil

from .registry import BaseTab, TabContext, register_tab, get_all_tabs, get_tab

__all__ = ["BaseTab", "TabContext", "register_tab", "get_all_tabs", "get_tab"]

logger = logging.getLogger(__name__)


def _autodiscover() -> None:
    """Import every non-private tab module in this package.

    Uses ``pkgutil.iter_modules`` instead of filesystem glob so that
    auto-discovery works inside PyInstaller bundles where ``.py`` files
    are not present on disk.
    """
    package = __name__
    for finder, name, ispkg in pkgutil.iter_modules(__path__):
        if name.startswith("_") or name == "registry":
            continue
        module_name = f"{package}.{name}"
        try:
            importlib.import_module(module_name)
            logger.debug("Auto-discovered tab module: %s", module_name)
        except Exception as exc:
            logger.error("Failed to import tab module '%s': %s", module_name, exc)


_autodiscover()
