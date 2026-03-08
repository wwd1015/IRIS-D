"""Tests for custom metric formula parsing (tokens → Polars expressions)."""

import polars as pl
import pytest

from src.dashboard.utils.custom_metrics import tokens_to_polars_expr


def _col(name: str) -> dict:
    return {"type": "column", "value": name}


def _const(val: float | int | str) -> dict:
    if isinstance(val, str):
        return {"type": "constant", "value": f'"{val}"'}
    return {"type": "constant", "value": str(val)}


def _bool(val: bool) -> dict:
    return {"type": "boolean", "value": "true" if val else "false"}


def _op(val: str) -> dict:
    return {"type": "operator", "value": val}


def _logic(val: str) -> dict:
    return {"type": "logic", "value": val}


# Small test DataFrame
DF = pl.DataFrame({
    "balance": [500.0, 1500.0, 2000.0],
    "rating": [10, 14, 20],
    "a": [0, 2, 5],
    "b": [0, 3, 1],
    "c": [4, 0, 0],
})


def _apply(tokens: list[dict]) -> list:
    expr = tokens_to_polars_expr(tokens)
    return DF.with_columns(expr.alias("result"))["result"].to_list()


class TestArithmetic:
    def test_addition(self):
        result = _apply([_col("balance"), _op("+"), _const(100)])
        assert result == [600.0, 1600.0, 2100.0]

    def test_multiplication(self):
        result = _apply([_col("balance"), _op("*"), _col("rating")])
        assert result == [5000.0, 21000.0, 40000.0]


class TestComparison:
    def test_greater_than(self):
        result = _apply([_col("balance"), _op(">"), _const(1000)])
        assert result == [False, True, True]


class TestIfThenElse:
    def test_basic(self):
        tokens = [_logic("IF"), _col("balance"), _op(">"), _const(1000),
                  _logic("THEN"), _const(1), _logic("ELSE"), _const(0)]
        assert _apply(tokens) == [0.0, 1.0, 1.0]

    def test_with_prefix_suffix(self):
        # ( IF balance > 1000 THEN 1 ELSE 0 ) * balance
        tokens = [
            _op("("), _logic("IF"), _col("balance"), _op(">"), _const(1000),
            _logic("THEN"), _const(1), _logic("ELSE"), _const(0), _op(")"),
            _op("*"), _col("balance"),
        ]
        assert _apply(tokens) == [0.0, 1500.0, 2000.0]


class TestAND:
    def test_and_condition(self):
        # IF balance > 1000 AND rating >= 14 THEN 1 ELSE 0
        tokens = [
            _logic("IF"),
            _col("balance"), _op(">"), _const(1000),
            _op("AND"),
            _col("rating"), _op(">="), _const(14),
            _logic("THEN"), _const(1), _logic("ELSE"), _const(0),
        ]
        # row0: 500>1000=F → 0, row1: 1500>1000=T AND 14>=14=T → 1, row2: 2000>1000=T AND 20>=14=T → 1
        assert _apply(tokens) == [0.0, 1.0, 1.0]


class TestOR:
    def test_or_condition(self):
        # IF balance > 1000 OR rating >= 14 THEN 1 ELSE 0
        tokens = [
            _logic("IF"),
            _col("balance"), _op(">"), _const(1000),
            _op("OR"),
            _col("rating"), _op(">="), _const(14),
            _logic("THEN"), _const(1), _logic("ELSE"), _const(0),
        ]
        # row0: 500>1000=F OR 10>=14=F → 0, row1: T OR T → 1, row2: T OR T → 1
        assert _apply(tokens) == [0.0, 1.0, 1.0]


class TestMixedPrecedence:
    def test_and_binds_tighter_than_or(self):
        # IF a > 1 AND b > 2 OR c > 3 THEN 1 ELSE 0
        # → (a>1 AND b>2) OR c>3
        tokens = [
            _logic("IF"),
            _col("a"), _op(">"), _const(1),
            _op("AND"),
            _col("b"), _op(">"), _const(2),
            _op("OR"),
            _col("c"), _op(">"), _const(3),
            _logic("THEN"), _const(1), _logic("ELSE"), _const(0),
        ]
        # row0: (0>1=F AND 0>2=F)=F OR 4>3=T → 1
        # row1: (2>1=T AND 3>2=T)=T OR 0>3=F → 1
        # row2: (5>1=T AND 1>2=F)=F OR 0>3=F → 0
        assert _apply(tokens) == [1.0, 1.0, 0.0]

    def test_parens_override_precedence(self):
        # IF a > 1 AND ( b > 2 OR c > 3 ) THEN 1 ELSE 0
        tokens = [
            _logic("IF"),
            _col("a"), _op(">"), _const(1),
            _op("AND"),
            _op("("), _col("b"), _op(">"), _const(2),
            _op("OR"),
            _col("c"), _op(">"), _const(3), _op(")"),
            _logic("THEN"), _const(1), _logic("ELSE"), _const(0),
        ]
        # row0: 0>1=F AND (...)=? → F → 0
        # row1: 2>1=T AND (3>2=T OR 0>3=F)=T → 1
        # row2: 5>1=T AND (1>2=F OR 0>3=F)=F → 0
        assert _apply(tokens) == [0.0, 1.0, 0.0]


class TestErrors:
    def test_empty_formula(self):
        with pytest.raises(ValueError, match="Empty formula"):
            tokens_to_polars_expr([])

    def test_missing_then(self):
        with pytest.raises(ValueError, match="Missing THEN"):
            tokens_to_polars_expr([_logic("IF"), _col("a"), _op(">"), _const(1),
                                   _logic("ELSE"), _const(0)])

    def test_invalid_operator(self):
        with pytest.raises(ValueError, match="Invalid operator"):
            tokens_to_polars_expr([_col("a"), _op("DROP"), _col("b")])

    def test_unknown_token_type(self):
        with pytest.raises(ValueError, match="Unknown token type"):
            tokens_to_polars_expr([{"type": "unknown", "value": "x"}])


class TestStringConstants:
    def test_if_then_else_string(self):
        # IF balance > 1000 THEN "Large" ELSE "Small"
        tokens = [
            _logic("IF"), _col("balance"), _op(">"), _const(1000),
            _logic("THEN"), _const("Large"), _logic("ELSE"), _const("Small"),
        ]
        result = _apply(tokens)
        assert result == ["Small", "Large", "Large"]

    def test_string_in_arithmetic_context(self):
        # Just a string literal
        tokens = [_const("hello")]
        expr = tokens_to_polars_expr(tokens)
        result = DF.with_columns(expr.alias("result"))["result"].to_list()
        assert result == ["hello", "hello", "hello"]


class TestBooleanTokens:
    def test_boolean_true(self):
        tokens = [_bool(True)]
        expr = tokens_to_polars_expr(tokens)
        result = DF.with_columns(expr.alias("result"))["result"].to_list()
        assert result == [True, True, True]

    def test_boolean_false(self):
        tokens = [_bool(False)]
        expr = tokens_to_polars_expr(tokens)
        result = DF.with_columns(expr.alias("result"))["result"].to_list()
        assert result == [False, False, False]

    def test_if_then_else_boolean(self):
        # IF balance > 1000 THEN TRUE ELSE FALSE
        tokens = [
            _logic("IF"), _col("balance"), _op(">"), _const(1000),
            _logic("THEN"), _bool(True), _logic("ELSE"), _bool(False),
        ]
        result = _apply(tokens)
        assert result == [False, True, True]

    def test_boolean_in_conditional_with_prefix(self):
        # ( IF rating >= 14 THEN TRUE ELSE FALSE )
        tokens = [
            _op("("), _logic("IF"), _col("rating"), _op(">="), _const(14),
            _logic("THEN"), _bool(True), _logic("ELSE"), _bool(False), _op(")"),
        ]
        result = _apply(tokens)
        assert result == [False, True, True]


class TestDetectMetricType:
    def test_numeric(self):
        from src.dashboard.utils.custom_metrics import detect_metric_type
        expr = tokens_to_polars_expr([_col("balance"), _op("+"), _const(1)])
        assert detect_metric_type(expr, DF) == "numeric"

    def test_indicator(self):
        from src.dashboard.utils.custom_metrics import detect_metric_type
        expr = tokens_to_polars_expr([_col("balance"), _op(">"), _const(1000)])
        assert detect_metric_type(expr, DF) == "indicator"

    def test_categorical(self):
        from src.dashboard.utils.custom_metrics import detect_metric_type
        tokens = [
            _logic("IF"), _col("balance"), _op(">"), _const(1000),
            _logic("THEN"), _const("Large"), _logic("ELSE"), _const("Small"),
        ]
        expr = tokens_to_polars_expr(tokens)
        assert detect_metric_type(expr, DF) == "categorical"

    def test_empty_df_still_detects_type(self):
        from src.dashboard.utils.custom_metrics import detect_metric_type
        empty = pl.DataFrame({"balance": pl.Series([], dtype=pl.Float64)})
        # Schema probing works even on empty df — comparison is still Boolean
        expr = tokens_to_polars_expr([_col("balance"), _op(">"), _const(1000)])
        assert detect_metric_type(expr, empty) == "indicator"
        # Arithmetic is still numeric
        expr2 = tokens_to_polars_expr([_col("balance"), _op("+"), _const(1)])
        assert detect_metric_type(expr2, empty) == "numeric"
