"""
User / Profile callbacks for IRIS-D.

Handles login, register, delete-profile, profile-switch, and contact-modal
interactions.  All mutable state is owned by :data:`app_state`.
"""

from __future__ import annotations

import logging
from datetime import datetime

from dash import Input, Output, State, callback, callback_context, no_update

from ..app_state import app_state
from ..auth import user_management
from .. import config

logger = logging.getLogger(__name__)

_HIDDEN = {
    "position": "fixed", "top": "0", "left": "0", "width": "100%",
    "height": "100%", "backgroundColor": "rgba(0,0,0,0.5)",
    "zIndex": "1000", "display": "none",
}
_SHOWN = {**_HIDDEN, "display": "block"}


def _initials(username: str) -> str:
    if not username or username == "Guest":
        return "G"
    words = username.split()
    return (words[0][0] + words[1][0]).upper() if len(words) >= 2 else username[0].upper()


def register(app) -> None:  # noqa: ARG001  (app kept for signature consistency)
    """Register all user-management callbacks with the Dash app."""

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
    def handle_login_modal(
        login_btn, login_clicks, register_clicks, delete_clicks, cancel_clicks,
        username, role, delete_profile_selection,
    ):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]

        profiles = user_management.load_profiles()
        delete_opts = [{"label": n, "value": n} for n in profiles if n != "Guest"]

        if trigger == "login-btn":
            return _SHOWN, _initials(user_management.get_current_user()), delete_opts

        if trigger == "login-cancel":
            return _HIDDEN, _initials(user_management.get_current_user()), delete_opts

        if trigger == "delete-profile-btn" and delete_profile_selection:
            if delete_profile_selection in profiles and delete_profile_selection != "Guest":
                del profiles[delete_profile_selection]
                user_management.save_profiles(profiles)
                if user_management.get_current_user() == delete_profile_selection:
                    user_management.set_current_user("Guest")
                    app_state.load_user_portfolios("Guest")
                updated = [{"label": n, "value": n} for n in profiles if n != "Guest"]
                return _HIDDEN, _initials(user_management.get_current_user()), updated
            return _HIDDEN, _initials(user_management.get_current_user()), delete_opts

        if trigger in ("login-submit", "register-submit") and username:
            if trigger == "register-submit" or username not in profiles:
                profiles[username] = {
                    "portfolios": {}, "custom_metrics": {},
                    "role": role or "BA",
                    "created": datetime.now().isoformat(),
                }
                user_management.save_profiles(profiles)
            user_management.set_current_user(username)
            app_state.load_user_portfolios(username)
            updated = [{"label": n, "value": n} for n in profiles if n != "Guest"]
            return _HIDDEN, _initials(user_management.get_current_user()), updated

        return _HIDDEN, _initials(user_management.get_current_user()), delete_opts

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
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]

        profiles = user_management.load_profiles()
        opts = [{"label": "Guest", "value": "Guest"}]
        opts.extend([{"label": n, "value": n} for n in profiles])

        if trigger == "profile-avatar-btn":
            return _SHOWN, opts, user_management.get_current_user()
        if trigger == "profile-switch-cancel":
            return _HIDDEN, opts, user_management.get_current_user()
        if trigger == "profile-switch-confirm" and selected_profile:
            user_management.set_current_user(selected_profile)
            app_state.load_user_portfolios(selected_profile)
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
        Output("current-user-store", "data"),
        [Input("login-submit", "n_clicks"),
         Input("register-submit", "n_clicks"),
         Input("profile-switch-confirm", "n_clicks")],
        [State("username-input", "value"),
         State("role-dropdown", "value"),
         State("profile-switch-dropdown", "value")],
        prevent_initial_call=True,
    )
    def update_current_user_store(
        login_clicks, register_clicks, switch_clicks, username, role, selected_profile,
    ):
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
        from ..components.layout import create_navigation_tabs
        return create_navigation_tabs()
