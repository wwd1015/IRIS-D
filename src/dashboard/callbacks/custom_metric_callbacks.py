"""
Custom Metric callbacks — modal open/close, formula building, save, delete, edit.

The formula builder uses a token-based approach: users click columns and
operators to build a formula visually. Tokens are stored in a dcc.Store
and converted to Polars expressions on save.
"""

from __future__ import annotations

import logging

from dash import Input, Output, State, callback, ctx, no_update, html, ALL
import polars as pl

logger = logging.getLogger(__name__)

_BADGE_COLORS = {"numeric": "#c96442", "categorical": "#d97757", "indicator": "#4d8b6f"}
_BADGE_LABELS = {"numeric": "Num", "categorical": "Cat", "indicator": "Bool"}


def _get_available_columns(dataset_name: str) -> list[dict]:
    """Return dropdown options for all non-custom columns in a dataset."""
    from ..data.registry import DatasetRegistry
    from ..app_state import app_state

    if not dataset_name or not DatasetRegistry.has(dataset_name):
        return []
    ds = DatasetRegistry.get(dataset_name)
    df = ds.latest_df
    custom_names = set(app_state.custom_metrics.keys())
    exclude_ids = {"facility_id", "reporting_date", "origination_date", "maturity_date"}
    cols = [
        col for col in df.columns
        if col not in custom_names and col not in exclude_ids
    ]
    return [{"label": col.replace("_", " ").title(), "value": col} for col in sorted(cols)]


def register(app) -> None:
    """Register all custom-metric callbacks."""

    from ..app_state import app_state
    from ..data.registry import DatasetRegistry
    from ..auth import user_management

    # ── Open / close modal ────────────────────────────────────────────────

    @app.callback(
        [Output("custom-metric-modal", "style"),
         Output("custom-metric-save-status", "children", allow_duplicate=True)],
        [Input("custom-metric-btn", "n_clicks"),
         Input("custom-metric-close-x", "n_clicks")],
        State("custom-metric-modal", "style"),
        prevent_initial_call=True,
    )
    def toggle_modal(open_clicks, close_clicks, current_style):
        trigger = ctx.triggered_id
        if trigger == "custom-metric-btn":
            return {**current_style, "display": "block"}, ""
        return {**current_style, "display": "none"}, no_update

    # ── Populate column dropdown on modal open or dataset change ──────────

    @app.callback(
        Output("custom-metric-column-dropdown", "options"),
        [Input("custom-metric-modal", "style"),
         Input("custom-metric-dataset-dropdown", "value")],
        State("custom-metric-dataset-dropdown", "value"),
    )
    def update_column_options(modal_style, dataset_val, dataset_state):
        dataset_name = dataset_val or dataset_state
        return _get_available_columns(dataset_name)

    # ── Formula token manipulation ────────────────────────────────────────

    _OP_MAP = {
        "custom-metric-op-add": "+",
        "custom-metric-op-sub": "-",
        "custom-metric-op-mul": "*",
        "custom-metric-op-div": "/",
        "custom-metric-op-lparen": "(",
        "custom-metric-op-rparen": ")",
        "custom-metric-op-gte": ">=",
        "custom-metric-op-lte": "<=",
        "custom-metric-op-gt": ">",
        "custom-metric-op-lt": "<",
        "custom-metric-op-eq": "==",
        "custom-metric-op-and": "AND",
        "custom-metric-op-or": "OR",
        "custom-metric-op-if": "IF",
        "custom-metric-op-then": "THEN",
        "custom-metric-op-else": "ELSE",
    }

    @app.callback(
        [Output("custom-metric-token-store", "data"),
         Output("custom-metric-column-dropdown", "value"),
         Output("custom-metric-constant-input", "value"),
         Output("custom-metric-text-input", "value")],
        [Input("custom-metric-add-col-btn", "n_clicks"),
         *[Input(k, "n_clicks") for k in _OP_MAP],
         Input("custom-metric-add-const-btn", "n_clicks"),
         Input("custom-metric-add-text-btn", "n_clicks"),
         Input("custom-metric-bool-true", "n_clicks"),
         Input("custom-metric-bool-false", "n_clicks"),
         Input("custom-metric-undo-btn", "n_clicks")],
        [State("custom-metric-token-store", "data"),
         State("custom-metric-column-dropdown", "value"),
         State("custom-metric-constant-input", "value"),
         State("custom-metric-text-input", "value")],
        prevent_initial_call=True,
    )
    def update_tokens(*args):
        tokens = args[-4] or []
        selected_col = args[-3]
        const_val = args[-2]
        text_val = args[-1]
        trigger = ctx.triggered_id
        clear_col = no_update
        clear_const = no_update
        clear_text = no_update

        if trigger == "custom-metric-undo-btn":
            if tokens:
                tokens = tokens[:-1]
            return tokens, clear_col, clear_const, clear_text

        if trigger == "custom-metric-add-col-btn":
            if selected_col:
                tokens = tokens + [{"type": "column", "value": selected_col}]
                clear_col = None
            return tokens, clear_col, clear_const, clear_text

        if trigger == "custom-metric-add-const-btn":
            if const_val is not None and const_val != "":
                try:
                    float(const_val)
                    tokens = tokens + [{"type": "constant", "value": str(const_val)}]
                    clear_const = ""
                except (ValueError, TypeError):
                    pass
            return tokens, clear_col, clear_const, clear_text

        if trigger == "custom-metric-add-text-btn":
            if text_val is not None and text_val.strip() != "":
                # Store as quoted string constant
                tokens = tokens + [{"type": "constant", "value": f'"{text_val.strip()}"'}]
                clear_text = ""
            return tokens, clear_col, clear_const, clear_text

        if trigger == "custom-metric-bool-true":
            tokens = tokens + [{"type": "boolean", "value": "true"}]
            return tokens, clear_col, clear_const, clear_text

        if trigger == "custom-metric-bool-false":
            tokens = tokens + [{"type": "boolean", "value": "false"}]
            return tokens, clear_col, clear_const, clear_text

        if trigger in _OP_MAP:
            val = _OP_MAP[trigger]
            tok_type = "logic" if val in ("IF", "THEN", "ELSE") else "operator"
            tokens = tokens + [{"type": tok_type, "value": val}]

        return tokens, clear_col, clear_const, clear_text

    # ── Render formula display ────────────────────────────────────────────

    @app.callback(
        Output("custom-metric-formula-display", "children"),
        Input("custom-metric-token-store", "data"),
    )
    def render_formula(tokens):
        if not tokens:
            return html.Span("Click columns and operators to build a formula",
                             style={"color": "var(--text-muted)", "fontStyle": "italic"})
        pills = []
        for tok in tokens:
            if tok["type"] == "column":
                pills.append(html.Span(
                    tok["value"].replace("_", " ").title(),
                    className="inline-block px-2 py-0.5 mx-0.5 rounded text-xs font-medium",
                    style={
                        "background": "var(--primary-600)",
                        "color": "white",
                        "border": "1px solid var(--primary-500)",
                    },
                ))
            elif tok["type"] == "operator":
                pills.append(html.Span(
                    f" {tok['value']} ",
                    className="text-sm font-mono",
                    style={"color": "var(--text-secondary)"},
                ))
            elif tok["type"] == "logic":
                pills.append(html.Span(
                    tok["value"],
                    className="inline-block px-2 py-0.5 mx-0.5 rounded text-xs font-bold",
                    style={
                        "background": "var(--accent-400)",
                        "color": "#0f172a",
                    },
                ))
            elif tok["type"] == "constant":
                val = tok["value"]
                is_string = val.startswith('"') and val.endswith('"')
                pills.append(html.Span(
                    val,
                    className="inline-block px-2 py-0.5 mx-0.5 rounded text-xs font-medium",
                    style={
                        "background": "rgba(201, 100, 66, 0.12)" if is_string else "rgba(77, 139, 111, 0.12)",
                        "color": "#d97757" if is_string else "#6da58b",
                        "border": "1px solid rgba(201, 100, 66, 0.3)" if is_string else "1px solid rgba(77, 139, 111, 0.3)",
                    },
                ))
            elif tok["type"] == "boolean":
                pills.append(html.Span(
                    tok["value"].upper(),
                    className="inline-block px-2 py-0.5 mx-0.5 rounded text-xs font-bold",
                    style={
                        "background": "rgba(77, 139, 111, 0.15)",
                        "color": "#6da58b",
                        "border": "1px solid rgba(77, 139, 111, 0.3)",
                    },
                ))
        return pills

    # ── Render saved metrics list (with Edit button) ──────────────────────

    @app.callback(
        Output("custom-metric-saved-list", "children"),
        [Input("custom-metric-token-store", "data"),
         Input("custom-metric-modal", "style"),
         Input("custom-metric-store", "data")],
    )
    def render_saved_metrics(_, style, __cm):
        if not app_state.custom_metrics:
            return html.Span("No saved metrics yet.",
                             style={"color": "var(--text-muted)", "fontStyle": "italic", "fontSize": "13px"})
        items = []
        for name, meta in app_state.custom_metrics.items():
            if not isinstance(meta, dict):
                continue
            mt = meta.get("metric_type", "numeric")
            items.append(html.Div([
                html.Span(name, className="text-sm", style={"color": "var(--text-primary)", "flex": "1"}),
                html.Span(_BADGE_LABELS.get(mt, "Num"), className="text-xs px-1.5 py-0.5 rounded",
                           style={"color": "#0f172a", "background": _BADGE_COLORS.get(mt, "#a78bfa"),
                                  "fontWeight": "600", "fontSize": "10px"}),
                html.Button(
                    "Edit",
                    id={"type": "custom-metric-edit", "index": name},
                    className="btn btn-ghost text-xs",
                    style={"color": "var(--primary-400)", "padding": "2px 8px", "minWidth": "auto", "minHeight": "auto"},
                ),
                html.Button(
                    "Delete",
                    id={"type": "custom-metric-delete", "index": name},
                    className="btn btn-ghost text-xs",
                    style={"color": "#ef4444", "padding": "2px 8px", "minWidth": "auto", "minHeight": "auto"},
                ),
            ], className="flex items-center gap-1 py-1"))
        return items

    # ── Edit a saved metric (load tokens + name into builder) ─────────────

    @app.callback(
        [Output("custom-metric-token-store", "data", allow_duplicate=True),
         Output("custom-metric-name-input", "value", allow_duplicate=True),
         Output("custom-metric-dataset-dropdown", "value", allow_duplicate=True),
         Output("custom-metric-edit-name", "data")],
        Input({"type": "custom-metric-edit", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def edit_metric(n_clicks_list):
        if not any(n_clicks_list):
            return no_update, no_update, no_update, no_update
        trigger = ctx.triggered_id
        if not trigger:
            return no_update, no_update, no_update, no_update
        name = trigger["index"]
        meta = app_state.custom_metrics.get(name)
        if not isinstance(meta, dict):
            return no_update, no_update, no_update, no_update
        display_name = name
        if display_name.endswith(" (customized)"):
            display_name = display_name[:-len(" (customized)")]
        return (
            meta.get("tokens", []),
            display_name,
            meta.get("dataset", "facilities"),
            name,
        )

    # ── Delete a saved metric ─────────────────────────────────────────────

    @app.callback(
        [Output("custom-metric-save-status", "children", allow_duplicate=True),
         Output("custom-metric-store", "data", allow_duplicate=True)],
        Input({"type": "custom-metric-delete", "index": ALL}, "n_clicks"),
        State("custom-metric-store", "data"),
        prevent_initial_call=True,
    )
    def delete_metric(n_clicks_list, metric_counter):
        if not any(n_clicks_list):
            return no_update, no_update
        trigger = ctx.triggered_id
        if not trigger:
            return no_update, no_update
        name = trigger["index"]
        if name in app_state.custom_metrics:
            # Check if any portfolio uses this metric as a filter column
            using_portfolios = [
                pname for pname, criteria in app_state.portfolios.items()
                if any(
                    f.get("column") == name
                    for f in (criteria.get("filters", []) if isinstance(criteria, dict) else [])
                )
            ]
            if using_portfolios:
                portfolios_str = ", ".join(using_portfolios)
                return (
                    html.Span(
                        f"Cannot delete '{name}' — used by portfolio(s): {portfolios_str}",
                        style={"color": "#ef4444", "fontSize": "12px"},
                    ),
                    no_update,
                )
            meta = app_state.custom_metrics[name]
            dataset_name = meta.get("dataset", "facilities") if isinstance(meta, dict) else "facilities"
            del app_state.custom_metrics[name]
            # Remove column from dataset
            if DatasetRegistry.has(dataset_name):
                ds = DatasetRegistry.get(dataset_name)
                if name in ds.full_df.columns:
                    ds.full_df = ds.full_df.drop(name)
                if name in ds.latest_df.columns:
                    ds.latest_df = ds.latest_df.drop(name)
                DatasetRegistry.invalidate_all_caches()
            # Persist
            current_user = user_management.get_current_user()
            if current_user:
                app_state.save_user_data(current_user)
            return (
                html.Span(f"Deleted '{name}'", style={"color": "#4D8B6F", "fontSize": "12px"}),
                (metric_counter or 0) + 1,
            )
        return no_update, no_update

    # ── Save metric ───────────────────────────────────────────────────────

    @app.callback(
        [Output("custom-metric-save-status", "children"),
         Output("custom-metric-name-input", "value"),
         Output("custom-metric-token-store", "data", allow_duplicate=True),
         Output("custom-metric-edit-name", "data", allow_duplicate=True),
         Output("custom-metric-store", "data", allow_duplicate=True)],
        Input("custom-metric-save-btn", "n_clicks"),
        [State("custom-metric-name-input", "value"),
         State("custom-metric-dataset-dropdown", "value"),
         State("custom-metric-token-store", "data"),
         State("custom-metric-edit-name", "data"),
         State("custom-metric-store", "data")],
        prevent_initial_call=True,
    )
    def save_metric(n_clicks, name, dataset_name, tokens, editing_name, metric_counter):
        _no_change = (no_update, no_update, no_update, no_update, no_update)
        _err = lambda msg: (html.Span(msg, style={"color": "#ef4444", "fontSize": "12px"}),
                            no_update, no_update, no_update, no_update)

        if not n_clicks:
            return _no_change

        # Validate
        if not name or not name.strip():
            return _err("Please enter a metric name.")
        if not tokens:
            return _err("Formula is empty.")
        if not dataset_name:
            return _err("Please select a dataset.")

        full_name = f"{name.strip()} (customized)"

        # Check for name collision (only if not editing the same metric)
        if full_name in app_state.custom_metrics and full_name != editing_name:
            return _err(f"'{full_name}' already exists.")

        # Build and evaluate expression
        try:
            expr = _tokens_to_polars_expr(tokens)
        except ValueError as e:
            return _err(str(e))

        # Apply to dataset
        if not DatasetRegistry.has(dataset_name):
            return _err(f"Dataset '{dataset_name}' not found.")

        ds = DatasetRegistry.get(dataset_name)

        # If editing, remove old column first (handles rename too)
        if editing_name and editing_name in app_state.custom_metrics:
            old_meta = app_state.custom_metrics[editing_name]
            old_ds_name = old_meta.get("dataset", "facilities") if isinstance(old_meta, dict) else "facilities"
            if DatasetRegistry.has(old_ds_name):
                old_ds = DatasetRegistry.get(old_ds_name)
                if editing_name in old_ds.full_df.columns:
                    old_ds.full_df = old_ds.full_df.drop(editing_name)
                if editing_name in old_ds.latest_df.columns:
                    old_ds.latest_df = old_ds.latest_df.drop(editing_name)
            del app_state.custom_metrics[editing_name]

        # Auto-detect metric type from expression result
        metric_type = detect_metric_type(expr, ds.full_df) if not ds.full_df.is_empty() else "numeric"
        if metric_type == "indicator":
            expr = expr.cast(pl.Utf8)
        try:
            ds.full_df = ds.full_df.with_columns(expr.alias(full_name))
            ds.latest_df = ds.latest_df.with_columns(expr.alias(full_name))
            DatasetRegistry.invalidate_all_caches()
        except Exception as e:
            return _err(f"Formula error: {e}")

        # Save to state and persist
        app_state.custom_metrics[full_name] = {
            "dataset": dataset_name,
            "tokens": tokens,
            "metric_type": metric_type,
        }
        current_user = user_management.get_current_user()
        if current_user:
            app_state.save_user_data(current_user)

        verb = "Updated" if editing_name else "Saved"
        return (
            html.Span(f"{verb} '{full_name}'", style={"color": "#4D8B6F", "fontSize": "12px"}),
            "",    # clear name input
            [],    # clear tokens
            None,  # clear edit mode
            (metric_counter or 0) + 1,  # bump signal to trigger tab re-render
        )




# Re-export from utils.custom_metrics for backward compatibility
from ..utils.custom_metrics import (  # noqa: F401
    tokens_to_polars_expr as _tokens_to_polars_expr,
    apply_custom_metrics,
    remove_custom_metric_columns,
    detect_metric_type,
)
