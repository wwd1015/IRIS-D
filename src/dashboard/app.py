#!/usr/bin/env python3
"""
IRIS-D – Interactive Reporting & Insight Generation System - Dashboard

A comprehensive portfolio performance dashboard for Corporate Banking and Commercial Real Estate
portfolios built with Dash and Python.

Architecture:
    - AppState (app_state.py) owns all mutable data & portfolio state
    - Tab registry system (tabs/) for extensible analysis views
    - Modular callback modules (callbacks/) grouped by concern
    - Plugin-style callbacks registered per tab
"""

import warnings
warnings.filterwarnings("ignore")

import dash
from dash import Input, Output, callback, callback_context, html

from . import config
from .app_state import app_state

# ── Tab auto-discovery (imports all tab modules, triggering registration) ─────
from . import tabs  # noqa: F401


# =============================================================================
# DATA INITIALISATION
# =============================================================================

app_state.initialize()


# =============================================================================
# DASH APP
# =============================================================================

app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder="../../assets")
server = app.server

from .components.layout import get_app_index_string, create_layout
app.index_string = get_app_index_string()


# =============================================================================
# DYNAMIC TAB NAVIGATION CALLBACK
# =============================================================================

def _build_tab_navigation_callback() -> None:
    """Dynamically build the tab navigation callback from the registry.

    Adding a new tab no longer requires touching this function — the registry
    is queried at startup.
    """
    from .tabs.registry import get_all_tabs, get_tab

    all_tabs = get_all_tabs()
    tab_ids = [t.id for t in all_tabs]

    outputs = [Output("tab-content-container", "children")]
    outputs += [Output(f"tab-{tid}", "className") for tid in tab_ids]

    inputs = [Input(f"tab-{tid}", "n_clicks") for tid in tab_ids]
    inputs.append(Input("universal-portfolio-dropdown", "value"))

    @callback(outputs, inputs, prevent_initial_call=False)
    def route_tabs(*args):
        from .auth import user_management

        ctx = callback_context
        active_tab_id = tab_ids[0]

        if ctx.triggered:
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            candidate = button_id.replace("tab-", "")
            if candidate in tab_ids:
                active_tab_id = candidate

        universal_portfolio = args[-1]
        sel_portfolio = universal_portfolio or app_state.default_portfolio

        # Server-side role gating: fall back to first accessible tab
        user_role = user_management.get_current_user_role()
        active_tab = get_tab(active_tab_id)
        if active_tab and active_tab.required_roles and user_role not in active_tab.required_roles:
            # Find first tab the user can access
            accessible = [t for t in all_tabs if not t.required_roles or user_role in t.required_roles]
            active_tab_id = accessible[0].id if accessible else tab_ids[0]

        tab_ctx = app_state.make_tab_context(sel_portfolio)

        active = get_tab(active_tab_id)
        content = active.render(tab_ctx) if active else html.Div("Tab not found")

        active_class = "px-3 py-1.5 rounded bg-ink-900 text-white"
        inactive_class = "px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700"
        classes = [active_class if tid == active_tab_id else inactive_class for tid in tab_ids]

        return [content] + classes


# =============================================================================
# REGISTER CALLBACKS
# =============================================================================

_build_tab_navigation_callback()

from .callbacks import user_callbacks, portfolio_callbacks
user_callbacks.register(app)
portfolio_callbacks.register(app)

# Auto-wire callbacks from all 3 layers (GlobalControl, ToolbarControl, DisplayCard)
from .callbacks import CallbackRegistry
_cb_registry = CallbackRegistry(app)
_cb_registry.register_all()

# Set layout
app.layout = create_layout(
    app_state.default_portfolio,
    app.index_string,
    app_state.available_portfolios,
)


# =============================================================================
# BACKWARD-COMPAT SHIM
# =============================================================================

def _make_tab_context(selected_portfolio=None):
    """Thin shim kept for CallbackRegistry's internal introspection call."""
    return app_state.make_tab_context(selected_portfolio)


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("Starting IRIS-D...")
    print("Dashboard available at: http://127.0.0.1:8050/")
    print("Press Ctrl+C to stop the server")
    app.run(debug=config.DEBUG_MODE, host=config.HOST, port=config.PORT)
