"""
User / Profile callbacks for IRIS-D.

Handles profile-switch and contact-modal interactions.  All mutable state is owned by :data:`app_state`.
"""

from __future__ import annotations

import logging

from dash import Input, Output, State, callback, callback_context, no_update

from ..app_state import app_state
from ..auth import user_management

logger = logging.getLogger(__name__)

_HIDDEN = {
    "position": "fixed", "top": "0", "left": "0", "width": "100%",
    "height": "100%", "backgroundColor": "rgba(0,0,0,0.5)",
    "zIndex": "1000", "display": "none",
}
_SHOWN = {**_HIDDEN, "display": "block"}


def _initials(username: str) -> str:
    if not username:
        return "?"
    words = username.split()
    return (words[0][0] + words[-1][0]).upper() if len(words) >= 2 else username[0].upper()


def register(app) -> None:  # noqa: ARG001  (app kept for signature consistency)
    """Register all user-management callbacks with the Dash app."""

    @callback(
        [Output("profile-switch-modal", "style"),
         Output("profile-switch-dropdown", "options"),
         Output("profile-switch-dropdown", "value")],
        [Input("profile-avatar-btn", "n_clicks"),
         Input("profile-switch-confirm", "n_clicks"),
         Input("profile-switch-cancel", "n_clicks"),
         Input("profile-switch-cancel-x", "n_clicks")],
        [State("profile-switch-dropdown", "value")],
        prevent_initial_call=True,
    )
    def handle_profile_switch_modal(avatar_clicks, confirm_clicks, cancel_clicks, cancel_x_clicks, selected_profile):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]

        roster = user_management.load_roster()
        opts = [{"label": f"{u['name']} ({u['role']})", "value": u["name"]} for u in roster]

        if trigger == "profile-avatar-btn":
            return _SHOWN, opts, user_management.get_current_user()
        if trigger in ("profile-switch-cancel", "profile-switch-cancel-x"):
            return _HIDDEN, opts, user_management.get_current_user()
        if trigger == "profile-switch-confirm" and selected_profile:
            return _HIDDEN, opts, selected_profile

        return _HIDDEN, opts, user_management.get_current_user()

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
        if trigger == "contact-btn":
            return _SHOWN
        return _HIDDEN

    @callback(
        [Output("current-user-store", "data"),
         Output("profile-avatar-btn", "children"),
         Output("portfolio-selector-btn", "children", allow_duplicate=True),
         Output("universal-portfolio-dropdown", "value", allow_duplicate=True),
         Output("universal-portfolio-dropdown", "options", allow_duplicate=True)],
        Input("profile-switch-confirm", "n_clicks"),
        State("profile-switch-dropdown", "value"),
        prevent_initial_call=True,
    )
    def update_current_user_store(switch_clicks, selected_profile):
        if selected_profile:
            # Load user state first (must happen before checking portfolios)
            user_management.set_current_user(selected_profile)
            app_state.load_user_portfolios(selected_profile)
            # Restore last-used portfolio, fall back to default
            last_active = user_management.get_last_active_portfolio(selected_profile)
            if last_active and last_active in app_state.portfolios:
                active = last_active
            else:
                active = app_state.default_portfolio
            portfolio_opts = [{"label": p, "value": p} for p in app_state.portfolios]
            return selected_profile, _initials(selected_profile), active, active, portfolio_opts
        return no_update, no_update, no_update, no_update, no_update

    @callback(
        Output("navigation-tabs-container", "children"),
        Input("current-user-store", "data"),
        prevent_initial_call=True,
    )
    def update_navigation_tabs(stored_user):
        """Re-render nav tabs when user role changes (some tabs are role-gated)."""
        from ..components.layout import create_navigation_tabs
        return create_navigation_tabs()
