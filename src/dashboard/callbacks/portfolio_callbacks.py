"""
Portfolio callbacks for IRIS-D.

Handles the Portfolio Manager modal (select/manage) and the Portfolio
Creation/Edit Wizard (hierarchical filter builder).  All mutable state is
owned by :data:`app_state`.
"""

from __future__ import annotations

import json
import logging

import polars as pl
from dash import Input, Output, State, callback, callback_context, html, dcc, no_update, ALL

from ..app_state import app_state, AppState
from ..auth import user_management
from ..data.registry import DatasetRegistry
from .. import config

logger = logging.getLogger(__name__)

_MODAL_SHOWN = {
    "position": "fixed", "top": "0", "left": "0", "width": "100%",
    "height": "100%", "backgroundColor": "rgba(0,0,0,0.5)",
    "zIndex": "1000", "display": "block",
}
_MODAL_HIDDEN = {"display": "none"}

_CREATE_NEW = "__create_new__"


def _render_filter_levels(state: list[dict]) -> list:
    """Build the UI rows for each filter level from the current filter state."""
    rows = []
    for i, level in enumerate(state):
        used_cols = {s["column"] for j, s in enumerate(state) if j < i and s.get("column")}
        all_cols = app_state.get_segmentation_columns()
        available_cols = [c for c in all_cols if c not in used_cols]
        col_options = [
            {"label": AppState.get_column_display_name(c), "value": c}
            for c in available_cols
        ]

        val_options = []
        if level.get("column"):
            df = app_state.latest_facilities
            for j in range(i):
                prev = state[j]
                if prev.get("column") and prev.get("values") and prev["column"] in df.columns:
                    str_vals = [str(v) for v in prev["values"]]
                    df = df.filter(pl.col(prev["column"]).cast(pl.Utf8).is_in(str_vals))
            vals = app_state.get_unique_values(level["column"], df)
            val_options = [{"label": str(v), "value": str(v)} for v in vals]

        rows.append(
            html.Div([
                html.Label(f"Filter Level {i + 1}", className="block text-xs font-semibold mb-1 text-brand-400"),
                html.Div([
                    dcc.Dropdown(
                        id={"type": "filter-col-dropdown", "index": i},
                        options=col_options,
                        value=level.get("column"),
                        placeholder="Column...",
                        className="text-xs",
                        style={"flex": "1"},
                    ),
                    dcc.Dropdown(
                        id={"type": "filter-val-dropdown", "index": i},
                        options=val_options,
                        value=level.get("values") or [],
                        placeholder="Values...",
                        className="text-xs",
                        style={"flex": "1"},
                        multi=True,
                    ),
                ], className="flex gap-2"),
            ], className="mb-3")
        )
    return rows


def _build_modal_opts() -> list[dict]:
    """Build the portfolio manager dropdown options."""
    opts = [{"label": "➕ Create New Portfolio", "value": _CREATE_NEW}]
    opts += [{"label": n, "value": n} for n in app_state.portfolios]
    return opts


def _build_portfolio_opts() -> list[dict]:
    """Build the hidden universal-portfolio-dropdown options."""
    return [{"label": p, "value": p} for p in app_state.portfolios]


def register(app) -> None:  # noqa: ARG001
    """Register all portfolio-management callbacks with the Dash app."""

    # ── Modal 1: Portfolio Manager ────────────────────────────────────────

    @callback(
        [Output("portfolio-modal", "style"),
         Output("portfolio-modal-dropdown", "options"),
         Output("portfolio-modal-dropdown", "value"),
         Output("portfolio-delete-error", "children")],
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
            return _MODAL_SHOWN, _build_modal_opts(), None, ""
        return _MODAL_HIDDEN, no_update, no_update, ""

    @callback(
        [Output("portfolio-update-btn", "disabled"),
         Output("portfolio-delete-btn", "disabled")],
        Input("portfolio-modal-dropdown", "value"),
        prevent_initial_call=True,
    )
    def toggle_update_delete_buttons(selected):
        """Enable Update/Delete only for custom (non-default) portfolios."""
        if not selected or selected == _CREATE_NEW or selected in config.DEFAULT_PORTFOLIOS:
            return True, True
        return False, False

    # ── Select button ─────────────────────────────────────────────────────

    @callback(
        [Output("portfolio-selector-btn", "children"),
         Output("universal-portfolio-dropdown", "value", allow_duplicate=True),
         Output("universal-portfolio-dropdown", "options", allow_duplicate=True),
         Output("portfolio-modal", "style", allow_duplicate=True),
         Output("portfolio-create-modal", "style"),
         Output("portfolio-filter-state", "data"),
         Output("filter-levels-container", "children"),
         Output("portfolio-edit-name", "data"),
         Output("portfolio-wizard-title", "children"),
         Output("create-portfolio-name-input", "value"),
         Output("create-portfolio-name-input", "disabled")],
        Input("portfolio-select-confirm", "n_clicks"),
        State("portfolio-modal-dropdown", "value"),
        prevent_initial_call=True,
    )
    def confirm_portfolio_selection(confirm_clicks, selected):
        n_out = 11
        if not confirm_clicks or not selected:
            return (no_update,) * n_out
        if selected == _CREATE_NEW:
            initial_state = [{"column": None, "values": []}]
            return (no_update, no_update, no_update, _MODAL_HIDDEN, _MODAL_SHOWN,
                    initial_state, _render_filter_levels(initial_state),
                    None, "Create New Portfolio", "", False)
        # Normal portfolio selection — record as last active
        user_management.set_last_active_portfolio(
            user_management.get_current_user(), selected,
        )
        return (selected, selected, _build_portfolio_opts(), _MODAL_HIDDEN,
                no_update, no_update, no_update,
                no_update, no_update, no_update, no_update)

    # ── Update button ─────────────────────────────────────────────────────

    @callback(
        [Output("portfolio-modal", "style", allow_duplicate=True),
         Output("portfolio-create-modal", "style", allow_duplicate=True),
         Output("portfolio-filter-state", "data", allow_duplicate=True),
         Output("filter-levels-container", "children", allow_duplicate=True),
         Output("portfolio-edit-name", "data", allow_duplicate=True),
         Output("portfolio-wizard-title", "children", allow_duplicate=True),
         Output("create-portfolio-name-input", "value", allow_duplicate=True),
         Output("create-portfolio-name-input", "disabled", allow_duplicate=True)],
        Input("portfolio-update-btn", "n_clicks"),
        State("portfolio-modal-dropdown", "value"),
        prevent_initial_call=True,
    )
    def open_update_wizard(n_clicks, selected):
        if not n_clicks or not selected or selected == _CREATE_NEW:
            return (no_update,) * 8
        if selected not in app_state.portfolios:
            return (no_update,) * 8

        criteria = app_state.portfolios[selected]
        criteria = AppState._migrate_criteria(criteria)
        existing_filters = criteria.get("filters", [])
        state = existing_filters if existing_filters else [{"column": None, "values": []}]

        return (_MODAL_HIDDEN, _MODAL_SHOWN,
                state, _render_filter_levels(state),
                selected, f"Update Portfolio: {selected}",
                selected, False)

    # ── Delete button ─────────────────────────────────────────────────────

    @callback(
        [Output("portfolio-modal-dropdown", "options", allow_duplicate=True),
         Output("portfolio-modal-dropdown", "value", allow_duplicate=True),
         Output("portfolio-delete-error", "children", allow_duplicate=True),
         Output("universal-portfolio-dropdown", "options", allow_duplicate=True),
         Output("portfolio-selector-btn", "children", allow_duplicate=True),
         Output("universal-portfolio-dropdown", "value", allow_duplicate=True)],
        Input("portfolio-delete-btn", "n_clicks"),
        State("portfolio-modal-dropdown", "value"),
        prevent_initial_call=True,
    )
    def delete_portfolio(n_clicks, selected):
        if not n_clicks or not selected:
            return (no_update,) * 6
        if selected in config.DEFAULT_PORTFOLIOS:
            return no_update, no_update, "Cannot delete default portfolios.", no_update, no_update, no_update
        if selected == _CREATE_NEW:
            return (no_update,) * 6

        user = user_management.get_current_user()
        app_state.portfolios.pop(selected, None)
        app_state.available_portfolios = list(app_state.portfolios.keys())
        app_state.save_user_data(user)
        DatasetRegistry.invalidate_all_caches()
        default = app_state.default_portfolio
        user_management.set_last_active_portfolio(user, default)
        logger.info("Deleted portfolio '%s'. Remaining: %s", selected, list(app_state.portfolios.keys()))
        return (_build_modal_opts(), None, "",
                _build_portfolio_opts(), default, default)

    # ── Modal 2: Creation/Edit Wizard ─────────────────────────────────────

    @callback(
        Output("portfolio-create-modal", "style", allow_duplicate=True),
        Input("portfolio-create-cancel", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_create_modal(n_clicks):
        if n_clicks:
            return _MODAL_HIDDEN
        return no_update

    @callback(
        [Output("portfolio-filter-state", "data", allow_duplicate=True),
         Output("filter-levels-container", "children", allow_duplicate=True)],
        Input("add-filter-level-btn", "n_clicks"),
        State("portfolio-filter-state", "data"),
        prevent_initial_call=True,
    )
    def add_filter_level(add_clicks, current_state):
        if not add_clicks:
            return no_update, no_update
        state = current_state or []
        state.append({"column": None, "values": []})
        return state, _render_filter_levels(state)

    @callback(
        [Output("portfolio-filter-state", "data", allow_duplicate=True),
         Output("filter-levels-container", "children", allow_duplicate=True)],
        [Input({"type": "filter-col-dropdown", "index": ALL}, "value"),
         Input({"type": "filter-val-dropdown", "index": ALL}, "value")],
        State("portfolio-filter-state", "data"),
        prevent_initial_call=True,
    )
    def update_filter_state(col_values, val_values, current_state):
        """Sync dropdown selections back into the filter state store."""
        ctx = callback_context
        if not ctx.triggered or not current_state:
            return no_update, no_update

        state = [dict(s) for s in current_state]

        trigger = ctx.triggered[0]["prop_id"]
        try:
            prop_id_str = trigger.rsplit(".", 1)[0]
            prop_id = json.loads(prop_id_str)
            idx = prop_id["index"]
            is_column = prop_id["type"] == "filter-col-dropdown"
        except (json.JSONDecodeError, KeyError):
            return no_update, no_update

        if idx >= len(state):
            return no_update, no_update

        if is_column:
            new_col = col_values[idx] if idx < len(col_values) else None
            if new_col == state[idx].get("column"):
                return no_update, no_update
            state[idx] = {"column": new_col, "values": []}
            state = state[:idx + 1]
        else:
            new_vals = val_values[idx] if idx < len(val_values) else []
            if not isinstance(new_vals, list):
                new_vals = [new_vals] if new_vals else []
            if new_vals == state[idx].get("values", []):
                return no_update, no_update
            state[idx] = {"column": state[idx].get("column"), "values": new_vals}

        return state, _render_filter_levels(state)

    # ── Save (create or update) ───────────────────────────────────────────

    @callback(
        [Output("portfolio-create-modal", "style", allow_duplicate=True),
         Output("portfolio-modal-dropdown", "options", allow_duplicate=True),
         Output("portfolio-modal-dropdown", "value", allow_duplicate=True),
         Output("create-portfolio-name-input", "value", allow_duplicate=True),
         Output("create-portfolio-error", "children"),
         Output("portfolio-selector-btn", "children", allow_duplicate=True),
         Output("universal-portfolio-dropdown", "value", allow_duplicate=True),
         Output("universal-portfolio-dropdown", "options", allow_duplicate=True)],
        Input("save-new-portfolio-btn", "n_clicks"),
        [State("create-portfolio-name-input", "value"),
         State("portfolio-filter-state", "data"),
         State("portfolio-edit-name", "data")],
        prevent_initial_call=True,
    )
    def save_portfolio(n_clicks, name, filter_state, edit_name):
        if not n_clicks:
            return (no_update,) * 8

        valid_filters = [
            f for f in (filter_state or [])
            if f.get("column") and f.get("values")
        ]
        if not valid_filters:
            return (no_update,) * 4 + ("Please define at least one filter level.",) + (no_update,) * 3

        if edit_name:
            if not name or not name.strip():
                return (no_update,) * 4 + ("Please enter a portfolio name.",) + (no_update,) * 3
            name = name.strip()
            if name != edit_name and name in config.DEFAULT_PORTFOLIOS:
                return (no_update,) * 4 + ("Cannot overwrite a default portfolio.",) + (no_update,) * 3
            if name != edit_name:
                app_state.portfolios.pop(edit_name, None)
        else:
            if not name or not name.strip():
                return (no_update,) * 4 + ("Please enter a portfolio name.",) + (no_update,) * 3
            name = name.strip()
            if name in config.DEFAULT_PORTFOLIOS:
                return (no_update,) * 4 + ("Cannot overwrite a default portfolio.",) + (no_update,) * 3

        user = user_management.get_current_user()
        app_state.portfolios[name] = {"filters": valid_filters}
        app_state.available_portfolios = list(app_state.portfolios.keys())
        user_management.set_last_active_portfolio(user, name)
        app_state.save_user_data(user)
        DatasetRegistry.invalidate_all_caches()
        action = "Updated" if edit_name else "Created"
        logger.info("%s portfolio '%s' with %d filters.", action, name, len(valid_filters))

        return (_MODAL_HIDDEN, _build_modal_opts(), name, "", "",
                name, name, _build_portfolio_opts())
