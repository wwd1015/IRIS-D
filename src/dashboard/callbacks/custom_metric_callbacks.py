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


def _get_numeric_columns(dataset_name: str) -> list[dict]:
    """Return dropdown options for non-custom numeric columns in a dataset."""
    from ..data.registry import DatasetRegistry
    from ..app_state import app_state

    if not dataset_name or not DatasetRegistry.has(dataset_name):
        return []
    ds = DatasetRegistry.get(dataset_name)
    df = ds.latest_df
    # Exclude columns that are custom metrics
    custom_names = set(app_state.custom_metrics.keys())
    exclude_ids = {"facility_id", "reporting_date", "origination_date", "maturity_date"}
    numeric_cols = [
        col for col in df.columns
        if df[col].dtype in pl.NUMERIC_DTYPES
        and col not in custom_names
        and col not in exclude_ids
    ]
    return [{"label": col.replace("_", " ").title(), "value": col} for col in sorted(numeric_cols)]


def register(app) -> None:
    """Register all custom-metric callbacks."""

    from ..app_state import app_state
    from ..data.registry import DatasetRegistry
    from ..auth import user_management

    # ── Open / close modal ────────────────────────────────────────────────

    @app.callback(
        Output("custom-metric-modal", "style"),
        [Input("custom-metric-btn", "n_clicks"),
         Input("custom-metric-close-x", "n_clicks")],
        State("custom-metric-modal", "style"),
        prevent_initial_call=True,
    )
    def toggle_modal(open_clicks, close_clicks, current_style):
        trigger = ctx.triggered_id
        if trigger == "custom-metric-btn":
            return {**current_style, "display": "block"}
        return {**current_style, "display": "none"}

    # ── Populate column dropdown on modal open or dataset change ──────────

    @app.callback(
        Output("custom-metric-column-dropdown", "options"),
        [Input("custom-metric-modal", "style"),
         Input("custom-metric-dataset-dropdown", "value")],
        State("custom-metric-dataset-dropdown", "value"),
    )
    def update_column_options(modal_style, dataset_val, dataset_state):
        dataset_name = dataset_val or dataset_state
        return _get_numeric_columns(dataset_name)

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
        "custom-metric-op-if": "IF",
        "custom-metric-op-then": "THEN",
        "custom-metric-op-else": "ELSE",
    }

    @app.callback(
        [Output("custom-metric-token-store", "data"),
         Output("custom-metric-column-dropdown", "value"),
         Output("custom-metric-constant-input", "value")],
        [Input("custom-metric-add-col-btn", "n_clicks"),
         *[Input(k, "n_clicks") for k in _OP_MAP],
         Input("custom-metric-add-const-btn", "n_clicks"),
         Input("custom-metric-undo-btn", "n_clicks")],
        [State("custom-metric-token-store", "data"),
         State("custom-metric-column-dropdown", "value"),
         State("custom-metric-constant-input", "value")],
        prevent_initial_call=True,
    )
    def update_tokens(*args):
        tokens = args[-3] or []
        selected_col = args[-2]
        const_val = args[-1]
        trigger = ctx.triggered_id
        clear_col = no_update
        clear_const = no_update

        if trigger == "custom-metric-undo-btn":
            if tokens:
                tokens = tokens[:-1]
            return tokens, clear_col, clear_const

        if trigger == "custom-metric-add-col-btn":
            if selected_col:
                tokens = tokens + [{"type": "column", "value": selected_col}]
                clear_col = None
            return tokens, clear_col, clear_const

        if trigger == "custom-metric-add-const-btn":
            if const_val is not None and const_val != "":
                try:
                    float(const_val)
                    tokens = tokens + [{"type": "constant", "value": str(const_val)}]
                    clear_const = ""
                except (ValueError, TypeError):
                    pass
            return tokens, clear_col, clear_const

        if trigger in _OP_MAP:
            val = _OP_MAP[trigger]
            tok_type = "logic" if val in ("IF", "THEN", "ELSE") else "operator"
            tokens = tokens + [{"type": tok_type, "value": val}]

        return tokens, clear_col, clear_const

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
                pills.append(html.Span(
                    tok["value"],
                    className="inline-block px-2 py-0.5 mx-0.5 rounded text-xs font-medium",
                    style={
                        "background": "rgba(45, 212, 191, 0.15)",
                        "color": "var(--accent-400)",
                        "border": "1px solid rgba(45, 212, 191, 0.3)",
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
            items.append(html.Div([
                html.Span(name, className="text-sm", style={"color": "var(--text-primary)", "flex": "1"}),
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
        # Strip " (customized)" suffix for the name input
        display_name = name
        if display_name.endswith(" (customized)"):
            display_name = display_name[:-len(" (customized)")]
        return (
            meta.get("tokens", []),
            display_name,
            meta.get("dataset", "facilities"),
            name,  # store the full name being edited
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
                ds.invalidate_cache()
            # Persist
            current_user = user_management.get_current_user()
            if current_user:
                app_state.save_user_data(current_user)
            return (
                html.Span(f"Deleted '{name}'", style={"color": "#2dd4bf", "fontSize": "12px"}),
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

        try:
            ds.full_df = ds.full_df.with_columns(expr.alias(full_name))
            ds.latest_df = ds.latest_df.with_columns(expr.alias(full_name))
            ds.invalidate_cache()
        except Exception as e:
            return _err(f"Formula error: {e}")

        # Save to state and persist
        app_state.custom_metrics[full_name] = {
            "dataset": dataset_name,
            "tokens": tokens,
        }
        current_user = user_management.get_current_user()
        if current_user:
            app_state.save_user_data(current_user)

        verb = "Updated" if editing_name else "Saved"
        return (
            html.Span(f"{verb} '{full_name}'", style={"color": "#2dd4bf", "fontSize": "12px"}),
            "",    # clear name input
            [],    # clear tokens
            None,  # clear edit mode
            (metric_counter or 0) + 1,  # bump signal to trigger tab re-render
        )


def _tokens_to_polars_expr(tokens: list[dict]) -> pl.Expr:
    """Convert a token list to a Polars expression.

    Supports arithmetic (+, -, *, /), comparisons (>=, <=, >, <, ==),
    and conditional logic (IF ... THEN ... ELSE ...).

    IF/THEN/ELSE maps to ``pl.when(condition).then(value).otherwise(value)``.
    """
    if not tokens:
        raise ValueError("Empty formula")

    # Check for IF/THEN/ELSE pattern
    has_logic = any(tok.get("type") == "logic" for tok in tokens)
    if has_logic:
        return _build_conditional_expr(tokens)

    return _build_arithmetic_expr(tokens)


_ALLOWED_OPS = frozenset({"+", "-", "*", "/", "(", ")", ">=", "<=", ">", "<", "=="})


def _build_arithmetic_expr(tokens: list[dict]) -> pl.Expr:
    """Build a simple arithmetic/comparison expression."""
    parts: list[str] = []
    for tok in tokens:
        t, v = tok["type"], tok["value"]
        if t == "column":
            parts.append(f"pl.col('{v}')")
        elif t == "constant":
            parts.append(f"pl.lit({float(v)})")
        elif t == "operator":
            if v not in _ALLOWED_OPS:
                raise ValueError(f"Invalid operator: {v}")
            parts.append(v)
        else:
            raise ValueError(f"Unknown token type: {t}")

    expr_str = " ".join(parts)
    try:
        result = eval(expr_str, {"__builtins__": {}, "pl": pl})
    except Exception as e:
        raise ValueError(f"Invalid formula: {e}")

    if not isinstance(result, pl.Expr):
        raise ValueError("Formula did not produce a valid expression")
    return result


def _build_conditional_expr(tokens: list[dict]) -> pl.Expr:
    """Build a ``pl.when(...).then(...).otherwise(...)`` expression.

    Supported patterns:
    - ``IF cond THEN val ELSE val``
    - ``( IF cond THEN val ELSE val ) * col``
    - ``col * ( IF cond THEN val ELSE val )``
    - ``IF cond THEN val ELSE val * col``  (auto-split)
    """
    # Find the index of IF, THEN, ELSE logic tokens
    if_idx = _find_logic(tokens, "IF")
    then_idx = _find_logic(tokens, "THEN")
    else_idx = _find_logic(tokens, "ELSE")

    if if_idx is None:
        raise ValueError("Missing IF keyword")
    if then_idx is None:
        raise ValueError("Missing THEN keyword")
    if else_idx is None:
        raise ValueError("Missing ELSE keyword")

    # Split into regions
    prefix_tokens = tokens[:if_idx]
    cond_tokens = [t for t in tokens[if_idx + 1:then_idx] if t.get("type") != "logic"]
    then_tokens = [t for t in tokens[then_idx + 1:else_idx] if t.get("type") != "logic"]
    after_else = [t for t in tokens[else_idx + 1:] if t.get("type") != "logic"]

    if not cond_tokens:
        raise ValueError("Missing condition after IF")
    if not then_tokens:
        raise ValueError("Missing value after THEN")
    if not after_else:
        raise ValueError("Missing value after ELSE")

    # Split after_else into else-value and suffix
    # Look for a closing paren that matches an opening paren in prefix,
    # or an arithmetic op at depth 0 after a value
    else_tokens, suffix_tokens = _split_else_suffix(after_else, prefix_tokens)

    # Strip wrapping parens: prefix "(" and suffix start ")" that pair up
    if (prefix_tokens
            and prefix_tokens[-1].get("type") == "operator"
            and prefix_tokens[-1].get("value") == "("
            and suffix_tokens
            and suffix_tokens[0].get("type") == "operator"
            and suffix_tokens[0].get("value") == ")"):
        prefix_tokens = prefix_tokens[:-1]
        suffix_tokens = suffix_tokens[1:]

    condition = _build_arithmetic_expr(cond_tokens)
    then_val = _build_arithmetic_expr(then_tokens)
    else_val = _build_arithmetic_expr(else_tokens)

    result = pl.when(condition).then(then_val).otherwise(else_val)

    # Wrap with prefix / suffix arithmetic if present
    if prefix_tokens or suffix_tokens:
        combined = prefix_tokens + [{"type": "_cond", "value": "__cond__"}] + suffix_tokens
        parts: list[str] = []
        for tok in combined:
            t, v = tok["type"], tok["value"]
            if t == "_cond":
                parts.append("__cond__")
            elif t == "column":
                parts.append(f"pl.col('{v}')")
            elif t == "constant":
                parts.append(f"pl.lit({float(v)})")
            elif t == "operator":
                if v not in _ALLOWED_OPS:
                    raise ValueError(f"Invalid operator: {v}")
                parts.append(v)
        expr_str = " ".join(parts)
        try:
            result = eval(expr_str, {"__builtins__": {}, "pl": pl, "__cond__": result})
        except Exception as e:
            raise ValueError(f"Invalid formula: {e}")

    return result


def _find_logic(tokens: list[dict], keyword: str) -> int | None:
    """Find the index of a logic token with the given keyword."""
    for i, tok in enumerate(tokens):
        if tok.get("type") == "logic" and tok.get("value") == keyword:
            return i
    return None


def _split_else_suffix(after_else: list[dict], prefix: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split tokens after ELSE into the else-value and suffix arithmetic.

    Handles two patterns:
    - ``0 ) * balance`` → else=[0], suffix=[) * balance]  (paren-closed)
    - ``0 * balance``   → else=[0], suffix=[* balance]    (no parens)
    """
    _ARITHMETIC = {"+", "-", "*", "/"}

    # Check if prefix ends with "(" — then look for matching ")"
    prefix_has_open = (
        prefix
        and prefix[-1].get("type") == "operator"
        and prefix[-1].get("value") == "("
    )

    depth = 0
    saw_value = False
    for i, tok in enumerate(after_else):
        t, v = tok.get("type", ""), tok.get("value", "")

        if t in ("column", "constant"):
            saw_value = True
        elif t == "operator" and v == "(":
            depth += 1
        elif t == "operator" and v == ")":
            if depth > 0:
                depth -= 1
            elif prefix_has_open and saw_value:
                # This ")" closes the prefix "(", start suffix here
                return after_else[:i], after_else[i:]
        elif t == "operator" and v in _ARITHMETIC and depth == 0 and saw_value:
            return after_else[:i], after_else[i:]

    return after_else, []


def apply_custom_metrics(app_state_ref) -> None:
    """Apply all custom metrics from app_state to their datasets.

    Called after loading user profiles to recompute custom columns.
    """
    from ..data.registry import DatasetRegistry

    for name, meta in app_state_ref.custom_metrics.items():
        if not isinstance(meta, dict):
            continue
        dataset_name = meta.get("dataset", "facilities")
        tokens = meta.get("tokens", [])
        if not tokens or not DatasetRegistry.has(dataset_name):
            continue
        try:
            expr = _tokens_to_polars_expr(tokens)
            ds = DatasetRegistry.get(dataset_name)
            if name not in ds.full_df.columns:
                ds.full_df = ds.full_df.with_columns(expr.alias(name))
            if name not in ds.latest_df.columns:
                ds.latest_df = ds.latest_df.with_columns(expr.alias(name))
        except Exception as e:
            logger.warning("Failed to apply custom metric '%s': %s", name, e)


def remove_custom_metric_columns(app_state_ref) -> None:
    """Remove all custom metric columns from datasets.

    Called before switching user profiles to clean up old metrics.
    """
    from ..data.registry import DatasetRegistry

    for name, meta in list(app_state_ref.custom_metrics.items()):
        dataset_name = meta.get("dataset", "facilities") if isinstance(meta, dict) else "facilities"
        if DatasetRegistry.has(dataset_name):
            ds = DatasetRegistry.get(dataset_name)
            if name in ds.full_df.columns:
                ds.full_df = ds.full_df.drop(name)
            if name in ds.latest_df.columns:
                ds.latest_df = ds.latest_df.drop(name)
    DatasetRegistry.invalidate_all_caches()
