"""
Custom metric formula parsing — token-to-Polars expression converter.

Converts a list of UI tokens (column, constant, operator, logic, boolean) into
a ``pl.Expr`` that can be applied to a DataFrame via ``.with_columns()``.

Supports arithmetic (+, -, *, /), comparisons (>=, <=, >, <, ==),
conditional logic (IF ... THEN ... ELSE ...), boolean literals (TRUE/FALSE),
and string constants (quoted values like ``"Large"``).

Result type is auto-detected via ``detect_metric_type()``:
- Numeric expressions → metric dropdowns
- Boolean expressions → indicator (cast to Utf8 for segmentation)
- String expressions → categorical (segmentation dropdowns)
"""

from __future__ import annotations

import logging

import polars as pl

logger = logging.getLogger(__name__)

_ALLOWED_OPS = frozenset({"+", "-", "*", "/", "(", ")", ">=", "<=", ">", "<", "==", "AND", "OR"})


def _token_to_part(t: str, v: str) -> str:
    """Convert a single token type+value to a Polars expression string fragment."""
    if t == "column":
        return f"pl.col('{v}')"
    if t == "constant":
        if v.startswith('"') and v.endswith('"'):
            return f"pl.lit({v})"
        return f"pl.lit({float(v)})"
    if t == "boolean":
        return f"pl.lit({v == 'true'})"
    if t == "operator":
        if v not in _ALLOWED_OPS:
            raise ValueError(f"Invalid operator: {v}")
        return v
    raise ValueError(f"Unknown token type: {t}")


def tokens_to_polars_expr(tokens: list[dict]) -> pl.Expr:
    """Convert a token list to a Polars expression.

    IF/THEN/ELSE maps to ``pl.when(condition).then(value).otherwise(value)``.
    """
    if not tokens:
        raise ValueError("Empty formula")

    has_logic = any(tok.get("type") == "logic" for tok in tokens)
    if has_logic:
        return _build_conditional_expr(tokens)

    return _build_arithmetic_expr(tokens)


def _split_at_logic(tokens: list[dict], keyword: str) -> list[list[dict]]:
    """Split token list at top-level (depth-0) occurrences of a logic keyword.

    Returns a list of token groups. If keyword is not found at depth 0,
    returns a single-element list containing the original tokens.
    """
    groups: list[list[dict]] = []
    current: list[dict] = []
    depth = 0
    for tok in tokens:
        t, v = tok.get("type", ""), tok.get("value", "")
        if t == "operator" and v == "(":
            depth += 1
        elif t == "operator" and v == ")":
            depth -= 1
        if depth == 0 and t == "operator" and v == keyword:
            groups.append(current)
            current = []
        else:
            current.append(tok)
    groups.append(current)
    return groups


def _strip_outer_parens(tokens: list[dict]) -> list[dict]:
    """Strip one layer of matching outer parentheses if they wrap the entire list."""
    while (len(tokens) >= 2
           and tokens[0].get("type") == "operator" and tokens[0].get("value") == "("
           and tokens[-1].get("type") == "operator" and tokens[-1].get("value") == ")"):
        # Verify the open paren at 0 matches the close paren at -1
        depth = 0
        matches_end = True
        for i, tok in enumerate(tokens):
            v = tok.get("value", "")
            if tok.get("type") == "operator" and v == "(":
                depth += 1
            elif tok.get("type") == "operator" and v == ")":
                depth -= 1
            if depth == 0 and i < len(tokens) - 1:
                matches_end = False
                break
        if matches_end:
            tokens = tokens[1:-1]
        else:
            break
    return tokens


def _build_arithmetic_expr(tokens: list[dict]) -> pl.Expr:
    """Build an arithmetic/comparison expression, with AND/OR support.

    Precedence (low→high): OR → AND → comparisons → arithmetic.
    Parentheses override precedence — splits only happen at depth 0.
    """
    # Strip matching outer parentheses so inner AND/OR can be split
    tokens = _strip_outer_parens(tokens)

    # Split on OR first (lowest precedence)
    or_groups = _split_at_logic(tokens, "OR")
    if len(or_groups) > 1:
        exprs = [_build_arithmetic_expr(g) for g in or_groups]
        result = exprs[0]
        for e in exprs[1:]:
            result = result | e
        return result

    # Then split on AND
    and_groups = _split_at_logic(tokens, "AND")
    if len(and_groups) > 1:
        exprs = [_build_arithmetic_expr(g) for g in and_groups]
        result = exprs[0]
        for e in exprs[1:]:
            result = result & e
        return result

    # Base case — flat arithmetic/comparison eval
    parts: list[str] = [_token_to_part(tok["type"], tok["value"]) for tok in tokens]

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
    if_idx = _find_logic(tokens, "IF")
    then_idx = _find_logic(tokens, "THEN")
    else_idx = _find_logic(tokens, "ELSE")

    if if_idx is None:
        raise ValueError("Missing IF keyword")
    if then_idx is None:
        raise ValueError("Missing THEN keyword")
    if else_idx is None:
        raise ValueError("Missing ELSE keyword")

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
        parts: list[str] = [
            "__cond__" if tok["type"] == "_cond" else _token_to_part(tok["type"], tok["value"])
            for tok in combined
        ]
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

    prefix_has_open = (
        prefix
        and prefix[-1].get("type") == "operator"
        and prefix[-1].get("value") == "("
    )

    depth = 0
    saw_value = False
    for i, tok in enumerate(after_else):
        t, v = tok.get("type", ""), tok.get("value", "")

        if t in ("column", "constant", "boolean"):
            saw_value = True
        elif t == "operator" and v == "(":
            depth += 1
        elif t == "operator" and v == ")":
            if depth > 0:
                depth -= 1
            elif prefix_has_open and saw_value:
                return after_else[:i], after_else[i:]
        elif t == "operator" and v in _ARITHMETIC and depth == 0 and saw_value:
            return after_else[:i], after_else[i:]

    return after_else, []


def detect_metric_type(expr: pl.Expr, df: pl.DataFrame) -> str:
    """Detect the result type of an expression via lazy schema probing."""
    try:
        schema = df.lazy().select(expr.alias("__probe__")).collect_schema()
        dtype = schema["__probe__"]
        if dtype == pl.Boolean:
            return "indicator"
        if dtype in (pl.Utf8, pl.Categorical):
            return "categorical"
        return "numeric"
    except Exception:
        return "numeric"


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
            expr = tokens_to_polars_expr(tokens)
            ds = DatasetRegistry.get(dataset_name)
            # Auto-detect type if not stored, then cast booleans to Utf8
            metric_type = meta.get("metric_type")
            if not metric_type:
                metric_type = detect_metric_type(expr, ds.full_df)
                meta["metric_type"] = metric_type
            if metric_type == "indicator":
                expr = expr.cast(pl.Utf8)
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
