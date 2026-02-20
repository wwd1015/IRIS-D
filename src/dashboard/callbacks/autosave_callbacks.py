"""
Auto-save callbacks for IRIS-D.

Periodically persists the current user's portfolios and custom metrics,
then shows/hides a brief notification banner.
"""

from __future__ import annotations

import logging

from dash import Input, Output, callback, no_update

from ..app_state import app_state
from ..auth import user_management

logger = logging.getLogger(__name__)

_NOTIFICATION_VISIBLE = {
    "position": "fixed", "bottom": "20px", "right": "20px",
    "zIndex": "1000", "opacity": "1", "transition": "opacity 0.3s ease",
    "display": "block",
}
_NOTIFICATION_HIDDEN = {
    "position": "fixed", "bottom": "20px", "right": "20px",
    "zIndex": "1000", "opacity": "0", "transition": "opacity 0.3s ease",
    "display": "none",
}


def register(app) -> None:  # noqa: ARG001
    """Register auto-save and notification-hide callbacks."""

    @callback(
        [Output("auto-save-notification", "style"),
         Output("save-message", "children"),
         Output("hide-notification-interval", "disabled")],
        Input("auto-save-interval", "n_intervals"),
        prevent_initial_call=True,
    )
    def show_auto_save_notification(n_intervals):
        current_user = user_management.get_current_user()
        if current_user != "Guest" and n_intervals and n_intervals > 0:
            try:
                app_state.save_user_data(current_user)
                logger.debug("Auto-saved data for user '%s'", current_user)
            except Exception as exc:
                logger.error("Auto-save failed for user '%s': %s", current_user, exc)
                return _NOTIFICATION_HIDDEN, "Save failed", True
            return _NOTIFICATION_VISIBLE, "Saved", False
        return _NOTIFICATION_HIDDEN, "Data auto-saved", True

    @callback(
        [Output("auto-save-notification", "style", allow_duplicate=True),
         Output("hide-notification-interval", "disabled", allow_duplicate=True)],
        Input("hide-notification-interval", "n_intervals"),
        prevent_initial_call=True,
    )
    def hide_notification_after_delay(n_intervals):
        if n_intervals and n_intervals > 0:
            return _NOTIFICATION_HIDDEN, True
        return no_update, no_update
