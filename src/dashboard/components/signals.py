"""
Signal definitions for cross-layer communication.

Signals are well-known ``dcc.Store`` IDs that act as an event bus between
layers.  Layer 1 controls *write* to a signal store, and Layer 2/3 components
*read* from the same store by adding it to their callback ``inputs``.

The framework auto-creates a ``dcc.Store`` for every signal ID returned by
``all_signal_ids()``.
"""

from __future__ import annotations

from ..tabs.registry import get_all_tabs


class Signal:
    """Well-known signal store IDs for cross-layer communication.

    Usage::

        # Layer 1 writes:
        CallbackSpec(outputs=[(Signal.PORTFOLIO, "data")], ...)

        # Layer 3 reads:
        CallbackSpec(inputs=[(Signal.PORTFOLIO, "data")], ...)
    """

    # ── Layer 1 → all layers ───────────────────────────────────────────────
    PORTFOLIO = "signal-portfolio"  # value: str (selected portfolio name)
    USER = "signal-current-user"    # value: str (current username)

    # ── Layer 2 → Layer 3 (tab-scoped) ─────────────────────────────────────
    @staticmethod
    def tab_filter(tab_id: str) -> str:
        """Per-tab filter store.  Value is a dict of the tab's toolbar state."""
        return f"signal-{tab_id}-filters"


def all_signal_ids() -> list[str]:
    """Return every signal ID that needs a ``dcc.Store`` in the layout.

    Includes static signals **and** one per registered tab.
    """
    ids = [Signal.PORTFOLIO, Signal.USER]
    for tab in get_all_tabs():
        ids.append(Signal.tab_filter(tab.id))
    return ids
