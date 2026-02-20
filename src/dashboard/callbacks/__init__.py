"""
CallbackRegistry — wires ``callback_specs()`` from Layer 1 global controls,
and invokes ``register_callbacks(app)`` on every registered tab.

Callback registration is split by layer:

* **Layer 1 (GlobalControl)** — declares callbacks via ``callback_specs()``,
  which are collected and wired here.  This is the *only* layer that uses the
  declarative ``CallbackSpec`` pattern.

* **Layer 2 (ToolbarControl)** — passive inputs only; no callbacks.

* **Layer 3 (DisplayCard)** — passive outputs only; no callbacks.

* **Tabs** — declare callbacks by overriding ``register_callbacks(app)`` and
  using ``@callback`` decorators inline.  State is accessed via the
  ``app_state`` singleton::

      from ..app_state import app_state

      def register_callbacks(self, app) -> None:
          @callback(Output("my-chart", "figure"),
                    Input("universal-portfolio-dropdown", "value"))
          def update(portfolio):
              df = app_state.get_filtered_data(portfolio)
              ...

Called once at startup by ``app.py``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from dash import Input, Output, State

if TYPE_CHECKING:
    from dash import Dash

from ..components.cards import CallbackSpec
from ..components.controls import get_all_global_controls
from ..tabs.registry import get_all_tabs

logger = logging.getLogger(__name__)


class CallbackRegistry:
    """Collect and register all callbacks from all layers.

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
        """Register a list of :class:`CallbackSpec` instances from a named owner."""
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
        """Discover and register every callback from all layers.

        **Call order:**

        1. Layer 1 — GlobalControl ``callback_specs()`` (declarative, wired here)
        2. Tabs — ``tab.register_callbacks(app)`` (imperative, ``@callback`` inline)
        """
        # Layer 1: GlobalControl.callback_specs() — declarative pattern.
        for ctrl in get_all_global_controls():
            self.register_specs(f"global:{ctrl.id}", ctrl.callback_specs())

        # Tabs: each tab's register_callbacks() uses @callback decorators directly.
        # Layer 2 (ToolbarControl) and Layer 3 (DisplayCard) are passive —
        # they provide Input/Output IDs but declare no callbacks of their own.
        for tab in get_all_tabs():
            tab.register_callbacks(self.app)
            logger.debug("Registered callbacks for tab '%s'", tab.id)

    # ── Introspection ──────────────────────────────────────────────────────

    def summary(self) -> str:
        """Return a human-readable summary of all Layer-1 callbacks registered."""
        lines = [f"CallbackRegistry: {len(self._registered)} Layer-1 callbacks registered"]
        for owner, spec in self._registered:
            kind = "client" if spec.client_side else "server"
            outs = ", ".join(f"{o[0]}.{o[1]}" for o in spec.outputs)
            ins = ", ".join(f"{i[0]}.{i[1]}" for i in spec.inputs)
            lines.append(f"  [{kind}] {owner}: {ins} → {outs}")
        return "\n".join(lines)
