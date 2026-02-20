"""
CallbackRegistry — auto-wires ``callback_specs()`` from all layers.

Called once at startup.  Collects every :class:`CallbackSpec` declared by
global controls, toolbar controls, and display cards, then registers them
with the Dash app.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dash import Input, Output, State

if TYPE_CHECKING:
    from dash import Dash

from ..components.cards import CallbackSpec
from ..components.controls import get_all_global_controls
from ..tabs.registry import get_all_tabs


class CallbackRegistry:
    """Collect and register all ``CallbackSpec`` instances from all layers.

    Usage::

        registry = CallbackRegistry(app)
        registry.register_all()      # call once at startup
        print(registry.summary())    # for debugging
    """

    def __init__(self, app: "Dash"):
        self.app = app
        self._registered: list[tuple[str, CallbackSpec]] = []

    # ── Registration ───────────────────────────────────────────────────────

    def register_specs(self, owner_id: str, specs: list[CallbackSpec]) -> None:
        """Register a list of CallbackSpecs from a named owner."""
        for spec in specs:
            outputs = [Output(*o) for o in spec.outputs]
            inputs = [Input(*i) for i in spec.inputs]
            states = [State(*s) for s in spec.states] if spec.states else []

            if spec.client_side:
                self.app.clientside_callback(
                    spec.client_side,
                    outputs[0] if len(outputs) == 1 else outputs,
                    inputs,
                    states,
                )
            elif spec.handler:
                self.app.callback(
                    outputs[0] if len(outputs) == 1 else outputs,
                    inputs,
                    states,
                    prevent_initial_call=spec.prevent_initial_call,
                )(spec.handler)

            self._registered.append((owner_id, spec))

    def register_all(self) -> None:
        """Discover and register every callback from all three layers.

        **Call order:**

        1. Layer 1 — global controls
        2. Layer 2 + 3 — per-tab (toolbar controls + cards + tab.register_callbacks)
        """
        # Layer 1: GlobalControl.callback_specs()
        for ctrl in get_all_global_controls():
            self.register_specs(f"global:{ctrl.id}", ctrl.callback_specs())

        # Layer 2 + 3: per-tab
        for tab in get_all_tabs():
            # Tab-level callbacks (the traditional register_callbacks method)
            tab.register_callbacks(self.app)

            # Note: Toolbar controls and cards callback_specs are registered
            # here for any that declare them.  Most simple controls don't
            # need callbacks — they just provide Input IDs that other
            # callbacks reference.
            # We create a lightweight context for introspection only.
            try:
                from ..app import _make_tab_context
                ctx = _make_tab_context()
                for tc in tab.get_toolbar_controls(ctx):
                    self.register_specs(f"toolbar:{tc.id}", tc.callback_specs())
                for card in tab.get_cards(ctx):
                    self.register_specs(f"card:{card.card_id}", card.callback_specs())
            except Exception:
                # If context building fails (e.g. during import), skip
                # dynamic callback registration — tab.register_callbacks
                # already handles the critical paths.
                pass

    # ── Introspection ──────────────────────────────────────────────────────

    def summary(self) -> str:
        """Return a human-readable summary of all registered callbacks."""
        lines = [f"CallbackRegistry: {len(self._registered)} callbacks registered"]
        for owner, spec in self._registered:
            kind = "client" if spec.client_side else "server"
            outs = ", ".join(f"{o[0]}.{o[1]}" for o in spec.outputs)
            ins = ", ".join(f"{i[0]}.{i[1]}" for i in spec.inputs)
            lines.append(f"  [{kind}] {owner}: {ins} → {outs}")
        return "\n".join(lines)
