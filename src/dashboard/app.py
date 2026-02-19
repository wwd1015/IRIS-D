#!/usr/bin/env python3
"""
IRIS-D – Interactive Reporting & Insight Generation System - Dashboard

A comprehensive portfolio performance dashboard for Corporate Banking and Commercial Real Estate 
portfolios built with Dash and Python.

Architecture:
    - Tab registry system (src/dashboard/tabs/) for extensible analysis views
    - Modular components for layout, auth, and data
    - Plugin-style callbacks registered per tab
"""

import dash
from dash import dcc, html, Input, Output, State, callback, callback_context, no_update
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from . import config
from .auth import user_management
from .data.loader import load_facilities_data
from .tabs.registry import TabContext, get_all_tabs, get_tab

# ── Import tab modules to trigger auto-registration ──────────────────────────
from .tabs import portfolio_summary  # noqa: F401
from .tabs import holdings           # noqa: F401
from .tabs import portfolio_trend    # noqa: F401
from .tabs import financial_trend    # noqa: F401
from .tabs import vintage_analysis   # noqa: F401
from .tabs import role_tabs          # noqa: F401


# =============================================================================
# DATA INITIALIZATION
# =============================================================================

custom_metrics: dict = {}

user_profiles = user_management.load_profiles()

try:
    print("=== IRIS-D - Loading Data ===")
    facilities_df = load_facilities_data()
    latest_facilities = facilities_df.sort_values("reporting_date").groupby("facility_id").tail(1)
    portfolios = config.DEFAULT_PORTFOLIOS.copy()
    available_portfolios = list(portfolios.keys())
    default_portfolio = available_portfolios[0] if available_portfolios else "Corporate Banking"
    print(f"✓ Loaded {len(facilities_df)} facility records")
except Exception as e:
    print(f"✗ Data loading failed: {e}")
    facilities_df = pd.DataFrame({
        "facility_id": ["F001", "F002", "F003"],
        "obligor_name": ["Test Company 1", "Test Company 2", "Test Company 3"],
        "obligor_rating": [5, 8, 12],
        "balance": [1000000, 2000000, 3000000],
        "lob": ["Corporate Banking", "CRE", "Corporate Banking"],
        "industry": ["Technology", None, "Healthcare"],
        "cre_property_type": [None, "Office", None],
        "reporting_date": ["2024-01-01", "2024-01-01", "2024-01-01"],
    })
    latest_facilities = facilities_df
    portfolios = {"Corporate Banking": {"lob": "Corporate Banking", "industry": None, "property_type": None}}
    available_portfolios = list(portfolios.keys())
    default_portfolio = "Corporate Banking"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_filtered_data(portfolio_name, portfolios_dict, latest_fac):
    """Filter facility data based on portfolio criteria."""
    if portfolio_name not in portfolios_dict:
        return pd.DataFrame()

    criteria = portfolios_dict[portfolio_name]
    filtered = latest_fac.copy()

    if criteria.get("lob"):
        filtered = filtered[filtered["lob"] == criteria["lob"]]

    if criteria.get("lob") == "Corporate Banking" and criteria.get("industry"):
        ind = criteria["industry"]
        if isinstance(ind, list):
            filtered = filtered[filtered["industry"].astype(str).isin([str(i) for i in ind])]
        else:
            filtered = filtered[filtered["industry"] == ind]

    if criteria.get("lob") == "CRE" and criteria.get("property_type"):
        pt = criteria["property_type"]
        if isinstance(pt, list):
            filtered = filtered[filtered["cre_property_type"].astype(str).isin([str(i) for i in pt])]
        else:
            filtered = filtered[filtered["cre_property_type"] == pt]

    if criteria.get("obligors"):
        ob = criteria["obligors"]
        if isinstance(ob, list):
            filtered = filtered[filtered["obligor_name"].astype(str).isin([str(i) for i in ob])]
        else:
            filtered = filtered[filtered["obligor_name"] == ob]

    return filtered


def _make_tab_context(selected_portfolio=None):
    """Build a TabContext with current app state."""
    sel = selected_portfolio or default_portfolio
    return TabContext(
        selected_portfolio=sel,
        available_portfolios=list(portfolios.keys()),
        portfolios=portfolios,
        facilities_df=facilities_df,
        latest_facilities=latest_facilities,
        custom_metrics=custom_metrics,
        get_filtered_data=lambda p: get_filtered_data(p, portfolios, latest_facilities),
    )


# =============================================================================
# DASH APP INITIALIZATION
# =============================================================================

app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder="../../assets")
server = app.server

# Apply custom HTML template
from .components.layout import get_app_index_string, create_layout
app.index_string = get_app_index_string()


# =============================================================================
# DYNAMIC TAB NAVIGATION CALLBACK
# =============================================================================

def _build_tab_navigation_callback():
    """
    Dynamically build the tab navigation callback from the registry.
    
    This replaces the old hardcoded callback with massive if/elif chains.
    Adding a new tab no longer requires touching this function.
    """
    all_tabs = get_all_tabs()
    tab_ids = [t.id for t in all_tabs]

    # Build Output list: content + one className output per tab
    outputs = [Output("tab-content-container", "children")]
    outputs += [Output(f"tab-{tid}", "className") for tid in tab_ids]

    # Build Input list: one n_clicks input per tab + universal dropdown
    inputs = [Input(f"tab-{tid}", "n_clicks") for tid in tab_ids]
    inputs.append(Input("universal-portfolio-dropdown", "value"))

    @callback(outputs, inputs, prevent_initial_call=False)
    def route_tabs(*args):
        ctx = callback_context
        active_tab_id = tab_ids[0]  # default to first tab

        if ctx.triggered:
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            candidate = button_id.replace("tab-", "")
            if candidate in tab_ids:
                active_tab_id = candidate

        # Resolve selected portfolio from universal dropdown (last arg)
        universal_portfolio = args[-1]
        sel_portfolio = universal_portfolio or default_portfolio

        # Build tab context
        tab_ctx = _make_tab_context(sel_portfolio)

        # Render the active tab
        active = get_tab(active_tab_id)
        content = active.render(tab_ctx) if active else html.Div("Tab not found")

        # Build class list
        active_class = "px-3 py-1.5 rounded bg-ink-900 text-white"
        inactive_class = "px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700"
        classes = [active_class if tid == active_tab_id else inactive_class for tid in tab_ids]

        return [content] + classes


# =============================================================================
# USER / PROFILE CALLBACKS
# =============================================================================

def _register_user_callbacks():
    """Register all user management and profile-related callbacks."""
    from datetime import datetime

    @callback(
        [Output("login-modal", "style"),
         Output("profile-avatar-btn", "children"),
         Output("delete-profile-dropdown", "options")],
        [Input("login-btn", "n_clicks"),
         Input("login-submit", "n_clicks"),
         Input("register-submit", "n_clicks"),
         Input("delete-profile-btn", "n_clicks"),
         Input("login-cancel", "n_clicks")],
        [State("username-input", "value"),
         State("role-dropdown", "value"),
         State("delete-profile-dropdown", "value")],
        prevent_initial_call=True,
    )
    def handle_login_modal(login_btn, login_clicks, register_clicks, delete_clicks, cancel_clicks,
                           username, role, delete_profile_selection):
        global portfolios, custom_metrics

        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]

        hidden = {"position": "fixed", "top": "0", "left": "0", "width": "100%",
                  "height": "100%", "backgroundColor": "rgba(0,0,0,0.5)",
                  "zIndex": "1000", "display": "none"}
        shown = {**hidden, "display": "block"}

        profiles = user_management.load_profiles()
        delete_opts = [{"label": n, "value": n} for n in profiles if n != "Guest"]

        def initials(u):
            if not u or u == "Guest":
                return "G"
            words = u.split()
            return (words[0][0] + words[1][0]).upper() if len(words) >= 2 else u[0].upper()

        if trigger == "login-btn":
            return shown, initials(user_management.get_current_user()), delete_opts

        if trigger == "login-cancel":
            return hidden, initials(user_management.get_current_user()), delete_opts

        if trigger == "delete-profile-btn" and delete_profile_selection:
            if delete_profile_selection in profiles and delete_profile_selection != "Guest":
                del profiles[delete_profile_selection]
                user_management.save_profiles(profiles)
                if user_management.get_current_user() == delete_profile_selection:
                    user_management.set_current_user("Guest")
                    portfolios.clear()
                    portfolios.update(config.DEFAULT_PORTFOLIOS.copy())
                    custom_metrics.clear()
                updated = [{"label": n, "value": n} for n in profiles if n != "Guest"]
                return hidden, initials(user_management.get_current_user()), updated
            return hidden, initials(user_management.get_current_user()), delete_opts

        if trigger in ("login-submit", "register-submit") and username:
            if trigger == "register-submit" or username not in profiles:
                profiles[username] = {
                    "portfolios": {}, "custom_metrics": {},
                    "role": role or "BA",
                    "created": datetime.now().isoformat(),
                }
                user_management.save_profiles(profiles)
            user_management.set_current_user(username)
            user_data = user_management.get_user_data(username)
            portfolios.clear()
            custom_metrics.clear()
            portfolios.update(config.DEFAULT_PORTFOLIOS.copy())
            user_portfolios = user_data.get("portfolios", {})
            if user_portfolios:
                portfolios.update(user_portfolios)
            custom_metrics.update(user_data.get("custom_metrics", {}))
            updated = [{"label": n, "value": n} for n in profiles if n != "Guest"]
            return hidden, initials(user_management.get_current_user()), updated

        return hidden, initials(user_management.get_current_user()), delete_opts

    @callback(
        [Output("profile-switch-modal", "style"),
         Output("profile-switch-dropdown", "options"),
         Output("profile-switch-dropdown", "value")],
        [Input("profile-avatar-btn", "n_clicks"),
         Input("profile-switch-confirm", "n_clicks"),
         Input("profile-switch-cancel", "n_clicks")],
        [State("profile-switch-dropdown", "value")],
        prevent_initial_call=True,
    )
    def handle_profile_switch_modal(avatar_clicks, confirm_clicks, cancel_clicks, selected_profile):
        global portfolios, custom_metrics
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]

        profiles = user_management.load_profiles()
        opts = [{"label": "Guest", "value": "Guest"}]
        opts.extend([{"label": n, "value": n} for n in profiles])

        hidden = {"position": "fixed", "top": "0", "left": "0", "width": "100%",
                  "height": "100%", "backgroundColor": "rgba(0,0,0,0.5)",
                  "zIndex": "1000", "display": "none"}
        shown = {**hidden, "display": "block"}

        if trigger == "profile-avatar-btn":
            return shown, opts, user_management.get_current_user()
        if trigger == "profile-switch-cancel":
            return hidden, opts, user_management.get_current_user()
        if trigger == "profile-switch-confirm" and selected_profile:
            user_management.set_current_user(selected_profile)
            portfolios.clear()
            custom_metrics.clear()
            portfolios.update(config.DEFAULT_PORTFOLIOS.copy())
            if selected_profile != "Guest":
                ud = user_management.get_user_data(selected_profile)
                up = ud.get("portfolios", {})
                if up:
                    portfolios.update(up)
                custom_metrics.update(ud.get("custom_metrics", {}))
            return hidden, opts, selected_profile

        return hidden, opts, user_management.get_current_user()

    @callback(
        Output("contact-modal", "style"),
        [Input("contact-btn", "n_clicks"), Input("contact-close", "n_clicks")],
        prevent_initial_call=True,
    )
    def handle_contact_modal(contact_clicks, close_clicks):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        hidden = {"position": "fixed", "top": "0", "left": "0", "width": "100%",
                  "height": "100%", "backgroundColor": "rgba(0,0,0,0.5)",
                  "zIndex": "1000", "display": "none"}
        if trigger == "contact-btn":
            return {**hidden, "display": "block"}
        return hidden

    @callback(
        Output("current-user-store", "data"),
        [Input("login-submit", "n_clicks"),
         Input("register-submit", "n_clicks"),
         Input("profile-switch-confirm", "n_clicks")],
        [State("username-input", "value"),
         State("role-dropdown", "value"),
         State("profile-switch-dropdown", "value")],
        prevent_initial_call=True,
    )
    def update_current_user_store(login_clicks, register_clicks, switch_clicks, username, role, selected_profile):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger in ("login-submit", "register-submit") and username:
            return username
        if trigger == "profile-switch-confirm" and selected_profile:
            return selected_profile
        return no_update

    @callback(
        Output("navigation-tabs-container", "children"),
        Input("current-user-store", "data"),
        prevent_initial_call=True,
    )
    def update_navigation_tabs(stored_user):
        """Re-render nav tabs when user role changes (some tabs are role-gated)."""
        from .components.layout import create_navigation_tabs
        return create_navigation_tabs()


# =============================================================================
# PORTFOLIO MANAGEMENT CALLBACKS
# =============================================================================

def _register_portfolio_callbacks():
    """Register portfolio CRUD callbacks."""

    @callback(
        [Output("portfolio-modal", "style"),
         Output("portfolio-modal-dropdown", "options"),
         Output("portfolio-modal-dropdown", "value"),
         Output("modal-delete-portfolio-dropdown", "options")],
        [Input("portfolio-selector-btn", "n_clicks"),
         Input("portfolio-modal-cancel", "n_clicks")],
        prevent_initial_call=True,
    )
    def toggle_portfolio_modal(btn_clicks, cancel_clicks):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger == "portfolio-selector-btn":
            opts = [{"label": n, "value": n} for n in portfolios]
            del_opts = [{"label": n, "value": n} for n in portfolios if n not in ("Corporate Banking", "CRE")]
            return {"position": "fixed", "top": "0", "left": "0", "width": "100%",
                    "height": "100%", "backgroundColor": "rgba(0,0,0,0.5)",
                    "zIndex": "1000", "display": "block"}, opts, None, del_opts
        return {"display": "none"}, no_update, no_update, no_update

    @callback(
        [Output("portfolio-selector-btn", "children"),
         Output("universal-portfolio-dropdown", "value", allow_duplicate=True),
         Output("portfolio-modal", "style", allow_duplicate=True)],
        Input("portfolio-select-confirm", "n_clicks"),
        State("portfolio-modal-dropdown", "value"),
        prevent_initial_call=True,
    )
    def confirm_portfolio_selection(confirm_clicks, selected_portfolio):
        if confirm_clicks and selected_portfolio:
            return selected_portfolio, selected_portfolio, {"display": "none"}
        return no_update, no_update, no_update

    @callback(
        [Output("modal-industry-group", "style"),
         Output("modal-property-type-group", "style"),
         Output("modal-industry-dropdown", "options"),
         Output("modal-property-type-dropdown", "options"),
         Output("modal-obligor-dropdown", "options")],
        Input("modal-lob-dropdown", "value"),
        prevent_initial_call=True,
    )
    def update_modal_dropdown_visibility(lob_value):
        if not lob_value:
            return {"display": "none"}, {"display": "none"}, [], [], []
        obligor_opts = [{"label": n, "value": n} for n in sorted(latest_facilities["obligor_name"].unique())]
        if lob_value == "Corporate Banking":
            ind_opts = [{"label": i, "value": i} for i in sorted(
                latest_facilities[latest_facilities["lob"] == "Corporate Banking"]["industry"].dropna().unique()
            )]
            return {"display": "block"}, {"display": "none"}, ind_opts, [], obligor_opts
        if lob_value == "CRE":
            prop_opts = [{"label": p, "value": p} for p in sorted(
                latest_facilities[latest_facilities["lob"] == "CRE"]["cre_property_type"].dropna().unique()
            )]
            return {"display": "none"}, {"display": "block"}, [], prop_opts, obligor_opts
        return {"display": "none"}, {"display": "none"}, [], [], obligor_opts

    @callback(
        [Output("portfolio-modal-dropdown", "options", allow_duplicate=True),
         Output("portfolio-modal-dropdown", "value", allow_duplicate=True),
         Output("modal-delete-portfolio-dropdown", "options", allow_duplicate=True),
         Output("modal-portfolio-name-input", "value"),
         Output("modal-lob-dropdown", "value"),
         Output("modal-industry-dropdown", "value"),
         Output("modal-property-type-dropdown", "value"),
         Output("modal-obligor-dropdown", "value")],
        Input("modal-save-portfolio-btn", "n_clicks"),
        [State("modal-portfolio-name-input", "value"),
         State("modal-lob-dropdown", "value"),
         State("modal-industry-dropdown", "value"),
         State("modal-property-type-dropdown", "value"),
         State("modal-obligor-dropdown", "value")],
        prevent_initial_call=True,
    )
    def save_portfolio_from_modal(n_clicks, name, lob, industry, prop_type, obligors):
        global portfolios, available_portfolios
        if n_clicks and name and (lob or obligors):
            portfolios[name] = {"lob": lob, "industry": industry, "property_type": prop_type, "obligors": obligors}
            available_portfolios = list(portfolios.keys())
            opts = [{"label": p, "value": p} for p in available_portfolios]
            del_opts = [{"label": p, "value": p} for p in available_portfolios if p not in ("Corporate Banking", "CRE")]
            if user_management.get_current_user() != "Guest":
                custom_p = {k: v for k, v in portfolios.items() if k not in config.DEFAULT_PORTFOLIOS}
                user_management.save_user_data(user_management.get_current_user(), custom_p, custom_metrics)
            return opts, name, del_opts, "", None, None, None, None
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    @callback(
        [Output("portfolio-modal-dropdown", "options", allow_duplicate=True),
         Output("portfolio-modal-dropdown", "value", allow_duplicate=True),
         Output("modal-delete-portfolio-dropdown", "options", allow_duplicate=True)],
        Input("modal-delete-confirm-btn", "n_clicks"),
        State("modal-delete-portfolio-dropdown", "value"),
        prevent_initial_call=True,
    )
    def delete_portfolio_from_modal(n_clicks, portfolio_to_delete):
        global portfolios, available_portfolios
        if n_clicks and portfolio_to_delete and portfolio_to_delete not in ("Corporate Banking", "CRE"):
            portfolios.pop(portfolio_to_delete, None)
            available_portfolios = list(portfolios.keys())
            opts = [{"label": p, "value": p} for p in available_portfolios]
            del_opts = [{"label": p, "value": p} for p in available_portfolios if p not in ("Corporate Banking", "CRE")]
            if user_management.get_current_user() != "Guest":
                custom_p = {k: v for k, v in portfolios.items() if k not in config.DEFAULT_PORTFOLIOS}
                user_management.save_user_data(user_management.get_current_user(), custom_p, custom_metrics)
            return opts, None, del_opts
        return no_update, no_update, no_update


# =============================================================================
# AUTO-SAVE CALLBACKS
# =============================================================================

def _register_autosave_callbacks():
    @callback(
        [Output("auto-save-notification", "style"),
         Output("save-message", "children"),
         Output("hide-notification-interval", "disabled")],
        Input("auto-save-interval", "n_intervals"),
        prevent_initial_call=True,
    )
    def show_auto_save_notification(n_intervals):
        if user_management.get_current_user() != "Guest" and n_intervals > 0:
            custom_p = {k: v for k, v in portfolios.items() if k not in config.DEFAULT_PORTFOLIOS}
            user_management.save_user_data(user_management.get_current_user(), custom_p, custom_metrics)
            return ({"position": "fixed", "bottom": "20px", "right": "20px",
                     "zIndex": "1000", "opacity": "1", "transition": "opacity 0.3s ease",
                     "display": "block"}, "Saved", False)
        return ({"position": "fixed", "bottom": "20px", "right": "20px",
                 "zIndex": "1000", "opacity": "0", "transition": "opacity 0.3s ease",
                 "display": "none"}, "Data auto-saved", True)

    @callback(
        [Output("auto-save-notification", "style", allow_duplicate=True),
         Output("hide-notification-interval", "disabled", allow_duplicate=True)],
        Input("hide-notification-interval", "n_intervals"),
        prevent_initial_call=True,
    )
    def hide_notification_after_delay(n_intervals):
        if n_intervals > 0:
            return ({"position": "fixed", "bottom": "20px", "right": "20px",
                     "zIndex": "1000", "opacity": "0", "transition": "opacity 0.3s ease",
                     "display": "none"}, True)
        return no_update, no_update


# =============================================================================
# REGISTER ALL CALLBACKS & SET LAYOUT
# =============================================================================

_build_tab_navigation_callback()
_register_user_callbacks()
_register_portfolio_callbacks()
_register_autosave_callbacks()

# Register per-tab callbacks
for tab in get_all_tabs():
    tab.register_callbacks(app)

# Dark mode toggle (client-side)
app.clientside_callback(
    """
    function(n_clicks){
      const root = document.documentElement;
      // Remove any leftover inline body styles — CSS variables handle theming
      document.body.style.removeProperty('color');
      document.body.style.removeProperty('background');
      if (!window._themeInit){
        const s = localStorage.getItem('theme');
        if (s === 'light') root.classList.remove('dark');
        window._themeInit = true;
      }
      if (n_clicks && n_clicks > 0){
        const isDark = root.classList.toggle('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        return isDark ? '🌙' : '☀️';
      }
      return root.classList.contains('dark') ? '🌙' : '☀️';
    }
    """,
    Output("theme-toggle", "children"),
    Input("theme-toggle", "n_clicks"),
)

# Set layout
app.layout = create_layout(default_portfolio, app.index_string, available_portfolios)


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("Starting IRIS-D...")
    print("Dashboard available at: http://127.0.0.1:8050/")
    print("Press Ctrl+C to stop the server")
    app.run(debug=config.DEBUG_MODE, host=config.HOST, port=config.PORT)
