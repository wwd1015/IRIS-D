"""
Signal definitions for cross-layer communication in IRIS-D.

Signals are well-known ``dcc.Store`` IDs that act as a lightweight event bus
between the three UI layers.  Layer 1 controls *write* to a signal store;
Layer 2/3 components *read* from the same store by listing it in their
callback ``inputs``.

The framework auto-creates a ``dcc.Store`` for every ID returned by
:func:`all_signal_ids`.

Signal flow
-----------
::

    Layer 1 (GlobalControl)  →  writes  →  Signal.PORTFOLIO / Signal.USER / …
    Layer 2 (ToolbarControl) →  reads   →  Signal.PORTFOLIO (filters by portfolio)
    Layer 3 (DisplayCard)    →  reads   →  Signal.tab_filter(tab_id)

Adding a signal
---------------
1. Add a class attribute to :class:`Signal` with a unique store-ID string.
2. If the signal is per-tab, add a static factory method (see
   :meth:`Signal.tab_filter` as the pattern).
3. Register it in :func:`all_signal_ids` so a ``dcc.Store`` is
   created automatically.

Contributing tab-specific signals
----------------------------------
Tabs that need their own custom signal stores can call
:func:`SignalRegistry.register` at module level inside their tab file::

    from ..components.signals import SignalRegistry
    SignalRegistry.register("my-tab-custom-signal")
"""

from __future__ import annotations

from ..tabs.registry import get_all_tabs


class Signal:
    """Well-known signal store IDs.

    Usage::

        # Layer 1 writes:
        CallbackSpec(outputs=[(Signal.PORTFOLIO, "data")], ...)

        # Layer 3 reads:
        CallbackSpec(inputs=[(Signal.PORTFOLIO, "data")], ...)
    """

    # ── Layer 1 → all layers ───────────────────────────────────────────────
    PORTFOLIO = "signal-portfolio"      # str  — selected portfolio name
    USER = "signal-current-user"        # str  — current username

    # ── Global UI state ────────────────────────────────────────────────────
    THEME = "signal-theme"              # str  — "light" | "dark"
    DATE_RANGE = "signal-date-range"    # dict — {"start": iso, "end": iso}
    NOTIFICATION = "signal-notification"  # dict — {"message": str, "level": str}
    CUSTOM_METRICS = "custom-metric-store"  # int — counter bumped on save/delete

    # ── Layer 2 → Layer 3 (tab-scoped) ─────────────────────────────────────
    @staticmethod
    def tab_filter(tab_id: str) -> str:
        """Per-tab filter store.  Value is a dict of the tab's toolbar state."""
        return f"signal-{tab_id}-filters"


class SignalRegistry:
    """Registry for tab-contributed custom signals.

    Tabs that need extra ``dcc.Store`` nodes beyond the standard set can
    register them here so the framework automatically creates the stores in
    the layout.

    Usage (inside a tab file)::

        from ..components.signals import SignalRegistry
        SignalRegistry.register("my-tab-drilldown")
    """

    _extra: list[str] = []

    @classmethod
    def register(cls, signal_id: str) -> None:
        """Register a custom signal ID."""
        if signal_id not in cls._extra:
            cls._extra.append(signal_id)

    @classmethod
    def extra_ids(cls) -> list[str]:
        """Return all tab-contributed signal IDs."""
        return list(cls._extra)


def all_signal_ids() -> list[str]:
    """Return every signal ID that needs a ``dcc.Store`` in the layout.

    Includes static signals, one per registered tab, and any extras
    contributed via :class:`SignalRegistry`.
    """
    ids = [
        Signal.PORTFOLIO,
        Signal.USER,
        Signal.THEME,
        Signal.DATE_RANGE,
        Signal.NOTIFICATION,
        Signal.CUSTOM_METRICS,
    ]
    for tab in get_all_tabs():
        ids.append(Signal.tab_filter(tab.id))
    ids.extend(SignalRegistry.extra_ids())
    return ids
