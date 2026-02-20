"""
Portfolio CRUD callbacks for IRIS-D.

Handles portfolio modal open/close, portfolio creation, selection,
and deletion.  All mutable state is owned by :data:`app_state`.
"""

from __future__ import annotations

import logging

from dash import Input, Output, State, callback, callback_context, no_update

from ..app_state import app_state
from ..auth import user_management
from .. import config

logger = logging.getLogger(__name__)

_MODAL_SHOWN = {
    "position": "fixed", "top": "0", "left": "0", "width": "100%",
    "height": "100%", "backgroundColor": "rgba(0,0,0,0.5)",
    "zIndex": "1000", "display": "block",
}
_MODAL_HIDDEN = {"display": "none"}


def register(app) -> None:  # noqa: ARG001
    """Register all portfolio-management callbacks with the Dash app."""

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
            opts = [{"label": n, "value": n} for n in app_state.portfolios]
            del_opts = [
                {"label": n, "value": n}
                for n in app_state.portfolios
                if n not in ("Corporate Banking", "CRE")
            ]
            return _MODAL_SHOWN, opts, None, del_opts
        return _MODAL_HIDDEN, no_update, no_update, no_update

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
            return selected_portfolio, selected_portfolio, _MODAL_HIDDEN
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
        obligor_opts = [
            {"label": n, "value": n}
            for n in sorted(app_state.latest_facilities["obligor_name"].unique())
        ]
        if lob_value == "Corporate Banking":
            cb_df = app_state.latest_facilities[
                app_state.latest_facilities["lob"] == "Corporate Banking"
            ]
            ind_opts = [
                {"label": i, "value": i}
                for i in sorted(cb_df["industry"].dropna().unique())
            ]
            return {"display": "block"}, {"display": "none"}, ind_opts, [], obligor_opts
        if lob_value == "CRE":
            cre_df = app_state.latest_facilities[
                app_state.latest_facilities["lob"] == "CRE"
            ]
            prop_opts = [
                {"label": p, "value": p}
                for p in sorted(cre_df["cre_property_type"].dropna().unique())
            ]
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
        if n_clicks and name and (lob or obligors):
            app_state.portfolios[name] = {
                "lob": lob, "industry": industry,
                "property_type": prop_type, "obligors": obligors,
            }
            app_state.available_portfolios = list(app_state.portfolios.keys())
            opts = [{"label": p, "value": p} for p in app_state.available_portfolios]
            del_opts = [
                {"label": p, "value": p}
                for p in app_state.available_portfolios
                if p not in ("Corporate Banking", "CRE")
            ]
            app_state.save_user_data(user_management.get_current_user())
            return opts, name, del_opts, "", None, None, None, None
        return (no_update,) * 8

    @callback(
        [Output("portfolio-modal-dropdown", "options", allow_duplicate=True),
         Output("portfolio-modal-dropdown", "value", allow_duplicate=True),
         Output("modal-delete-portfolio-dropdown", "options", allow_duplicate=True)],
        Input("modal-delete-confirm-btn", "n_clicks"),
        State("modal-delete-portfolio-dropdown", "value"),
        prevent_initial_call=True,
    )
    def delete_portfolio_from_modal(n_clicks, portfolio_to_delete):
        if (
            n_clicks
            and portfolio_to_delete
            and portfolio_to_delete not in ("Corporate Banking", "CRE")
        ):
            app_state.portfolios.pop(portfolio_to_delete, None)
            app_state.available_portfolios = list(app_state.portfolios.keys())
            opts = [{"label": p, "value": p} for p in app_state.available_portfolios]
            del_opts = [
                {"label": p, "value": p}
                for p in app_state.available_portfolios
                if p not in ("Corporate Banking", "CRE")
            ]
            app_state.save_user_data(user_management.get_current_user())
            return opts, None, del_opts
        return no_update, no_update, no_update
