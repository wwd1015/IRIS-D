"""
Time Window callbacks — modal open/close, apply, and global state update.
"""

from dash import Input, Output, State, callback, no_update, callback_context

from ..utils.helpers import MODAL_SHOWN, MODAL_HIDDEN


def register(app):
    """Wire all time-window callbacks."""

    # Toggle modal visibility
    @callback(
        Output("time-window-modal", "style"),
        [Input("time-window-btn", "n_clicks"),
         Input("time-window-cancel", "n_clicks"),
         Input("time-window-cancel-x", "n_clicks"),
         Input("time-window-apply", "n_clicks"),
         Input("time-window-reset", "n_clicks"),
         Input("perf-warning-confirm", "n_clicks")],
        State("time-window-modal", "style"),
        prevent_initial_call=True,
    )
    def toggle_modal(open_clicks, cancel_clicks, cancel_x_clicks,
                     apply_clicks, reset_clicks, confirm_clicks, current_style):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        style = dict(current_style) if current_style else {}
        if trigger == "time-window-btn":
            style["display"] = "block"
        else:
            style["display"] = "none"
        return style

    # Apply button → update store + button label + app_state
    @callback(
        [Output("time-window-store", "data"),
         Output("time-window-btn", "children"),
         Output("perf-warning-modal", "style")],
        [Input("time-window-apply", "n_clicks"),
         Input("time-window-reset", "n_clicks"),
         Input("perf-warning-confirm", "n_clicks")],
        [State("time-window-start-dropdown", "value"),
         State("time-window-end-dropdown", "value"),
         State("time-window-dates", "data"),
         State("universal-portfolio-dropdown", "value")],
        prevent_initial_call=True,
    )
    def apply_time_window(apply_clicks, reset_clicks, confirm_clicks,
                          start_val, end_val, all_dates, current_portfolio):
        from ..app_state import app_state
        from ..components.controls import _format_time_label
        from .. import config

        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger == "time-window-reset":
            # Check if current portfolio is a default (unfiltered) portfolio
            sel = current_portfolio or app_state.default_portfolio
            if sel in config.DEFAULT_PORTFOLIOS:
                # Show warning instead of applying
                return no_update, no_update, MODAL_SHOWN
            # Safe to apply — portfolio has filters
            app_state.set_time_window(None, None)
            if all_dates:
                label = _format_time_label(all_dates[0][:10], all_dates[-1][:10])
            else:
                label = _format_time_label(None, None)
            return None, label, no_update

        if trigger == "perf-warning-confirm":
            # User confirmed — apply Show All
            app_state.set_time_window(None, None)
            if all_dates:
                label = _format_time_label(all_dates[0][:10], all_dates[-1][:10])
            else:
                label = _format_time_label(None, None)
            return None, label, MODAL_HIDDEN

        # Apply button
        if not start_val or not end_val:
            return no_update, no_update, no_update

        app_state.set_time_window(start_val, end_val)
        label = _format_time_label(start_val, end_val)
        return {"start": start_val, "end": end_val}, label, no_update

    # Cancel warning modal
    @callback(
        Output("perf-warning-modal", "style", allow_duplicate=True),
        Input("perf-warning-cancel", "n_clicks"),
        prevent_initial_call=True,
    )
    def cancel_warning(n_clicks):
        if not n_clicks:
            return no_update
        return MODAL_HIDDEN
