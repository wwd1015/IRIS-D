"""
Time Window callbacks — modal open/close, apply, and global state update.
"""

from dash import Input, Output, State, callback, html, no_update, callback_context

from ..utils.helpers import MODAL_SHOWN, MODAL_HIDDEN


def _pill_children(label: str):
    """Pill content matching TimeWindowButton.render (dot + label + caret)."""
    return [
        html.Span(className="dot"),
        html.Span(label),
        html.Span("▾", className="portfolio-pill-caret", style={"marginLeft": "4px"}),
    ]


def register(app):
    """Wire all time-window callbacks."""

    # Toggle modal visibility
    @callback(
        Output("time-window-modal", "style"),
        [Input("time-window-btn", "n_clicks"),
         Input("time-window-backdrop", "n_clicks"),
         Input("time-window-cancel", "n_clicks"),
         Input("time-window-cancel-x", "n_clicks"),
         Input("time-window-apply", "n_clicks"),
         Input("time-window-reset", "n_clicks"),
         Input("perf-warning-confirm", "n_clicks")],
        State("time-window-modal", "style"),
        prevent_initial_call=True,
    )
    def toggle_modal(open_clicks, backdrop_clicks, cancel_clicks, cancel_x_clicks,
                     apply_clicks, reset_clicks, confirm_clicks, current_style):
        # Anchored dropdown popover: time-window-btn opens it; everything else
        # (backdrop click, close, apply, reset, perf-confirm) closes it.
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        style = dict(current_style) if current_style else {}
        style["display"] = "block" if trigger == "time-window-btn" else "none"
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
            return None, _pill_children(label), no_update

        if trigger == "perf-warning-confirm":
            # User confirmed — apply Show All
            app_state.set_time_window(None, None)
            if all_dates:
                label = _format_time_label(all_dates[0][:10], all_dates[-1][:10])
            else:
                label = _format_time_label(None, None)
            return None, _pill_children(label), MODAL_HIDDEN

        # Apply button
        if not start_val or not end_val:
            return no_update, no_update, no_update

        app_state.set_time_window(start_val, end_val)
        label = _format_time_label(start_val, end_val)
        return {"start": start_val, "end": end_val}, _pill_children(label), no_update

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

    # Preset chips (3M/6M/1Y/2Y/ALL) → set the start/end dropdowns.
    # Pure draft state — Apply still commits, so behavior is unchanged.
    _PRESET_MONTHS = {"tw-preset-3m": 3, "tw-preset-6m": 6,
                      "tw-preset-1y": 12, "tw-preset-2y": 24}

    @callback(
        [Output("time-window-start-dropdown", "value"),
         Output("time-window-end-dropdown", "value")],
        [Input("tw-preset-3m", "n_clicks"), Input("tw-preset-6m", "n_clicks"),
         Input("tw-preset-1y", "n_clicks"), Input("tw-preset-2y", "n_clicks"),
         Input("tw-preset-all", "n_clicks")],
        State("time-window-dates", "data"),
        prevent_initial_call=True,
    )
    def apply_preset(n3, n6, n1y, n2y, nall, all_dates):
        ctx = callback_context
        if not ctx.triggered or not all_dates:
            return no_update, no_update
        trigger = ctx.triggered[0]["prop_id"].split(".")[0]
        end = all_dates[-1][:10]
        if trigger == "tw-preset-all":
            return all_dates[0][:10], end
        months = _PRESET_MONTHS.get(trigger)
        if not months:
            return no_update, no_update
        start_ix = max(0, len(all_dates) - 1 - months)
        return all_dates[start_ix][:10], end
