"""
Portfolio Summary tab – the default landing page.

Layout: TWO_COL (bar chart | waterfall chart).
Toolbar: Metric (all numeric cols) + Frequency (M/Q/A).
Left card: time-series bar chart with optional segmentation stacked bars.
Right card: period-over-period waterfall (run-off / changes / new origination).
"""

from __future__ import annotations

import plotly.graph_objs as go
import polars as pl
from dash import callback, dcc, html, Input, Output, no_update

from .registry import BaseTab, ContentLayout, TabContext, register_tab
from ..components.toolbar import DropdownControl
from ..components.mixins.click_detail import chart_with_detail_layout, register_detail_callback
from ..utils.helpers import plotly_theme, empty_figure


class PortfolioSummaryTab(BaseTab):
    id = "portfolio-summary"
    label = "Portfolio Summary"
    order = 10
    tier = "gold"
    tier_tooltip = "Gold tier — set tier='gold' in your BaseTab subclass"
    content_layout = ContentLayout.TWO_COL

    def get_toolbar_controls(self, ctx: TabContext):
        metric_opts = _get_metric_options(ctx.facilities_df)
        default_metric = "balance" if any(o["value"] == "balance" for o in metric_opts) else (metric_opts[0]["value"] if metric_opts else "balance")
        return [
            DropdownControl(
                id="ps-metric", label="Metric",
                options=metric_opts,
                value=default_metric,
                order=10,
            ),
            DropdownControl(
                id="ps-freq", label="Frequency",
                options=[
                    {"label": "Monthly", "value": "monthly"},
                    {"label": "Quarterly", "value": "quarterly"},
                    {"label": "Annually", "value": "annually"},
                ],
                value="monthly", order=20,
            ),
        ]

    def render_content(self, ctx: TabContext):
        seg_opts = _get_segmentation_options(ctx.facilities_df)
        fig = _build_bar_chart(ctx.facilities_df, ctx.portfolios,
                               ctx.selected_portfolio, "balance", "monthly", None)
        fig_right = _build_waterfall_chart(ctx.facilities_df, ctx.portfolios,
                                           ctx.selected_portfolio, "balance", "monthly")
        return html.Div([
            html.Div([
                html.Div([
                    html.Div(style={"flex": "1"}),
                    html.Div([
                        html.Span("Segmentation", className="control-label"),
                        dcc.Dropdown(
                            id="ps-segmentation",
                            options=seg_opts,
                            value=None,
                            placeholder="None",
                            clearable=True,
                            persistence=True,
                            persistence_type="session",
                            style={"width": "160px", "fontSize": "13px"},
                        ),
                    ]),
                ], className="flex items-end gap-3 mb-2"),
                chart_with_detail_layout("ps-bar-chart", figure=fig, height=400),
            ], className="glass-card p-4"),
            html.Div([
                chart_with_detail_layout("ps-waterfall-chart", figure=fig_right, height=400),
            ], className="glass-card p-4"),
        ])

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            Output("ps-bar-chart", "figure"),
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data"),
             Input("custom-metric-store", "data"),
             Input("ps-metric", "value"),
             Input("ps-freq", "value"),
             Input("ps-segmentation", "value")],
            prevent_initial_call=True,
        )
        def update_chart(portfolio, _tw, _cm, metric, freq, segmentation):
            if not portfolio:
                return no_update
            metric = metric or "balance"
            freq = freq or "monthly"
            windowed = app_state._apply_time_window(app_state.facilities_df)
            return _build_bar_chart(windowed, app_state.portfolios,
                                    portfolio, metric, freq, segmentation)

        def _get_bar_detail(click_point, curve_name, x_value, portfolio):
            """Return filtered rows for the clicked bar's period + segment."""
            if not portfolio or portfolio not in app_state.portfolios:
                return None
            windowed = app_state._apply_time_window(app_state.facilities_df)
            filtered = _apply_filters(windowed, app_state.portfolios[portfolio])
            if filtered.is_empty():
                return None

            # Determine period column to match against
            if "reporting_date" not in filtered.columns:
                return None

            rd = filtered["reporting_date"]
            date_col = pl.col("reporting_date")
            if rd.dtype != pl.Utf8:
                date_col = date_col.cast(pl.Utf8)

            # Match rows whose reporting_date falls in the clicked period
            year_expr = date_col.str.slice(0, 4)
            month_expr = date_col.str.slice(5, 2)

            # x_value is the period string like "2024-06-01"
            period_year = x_value[:4]
            period_month = x_value[5:7] if len(x_value) >= 7 else "01"

            # Determine current frequency from the x_value pattern
            # We filter to rows matching the period
            result = filtered.filter(year_expr == period_year)
            if period_month != "01" or x_value.endswith("-01-01"):
                # Monthly or specific quarter start
                p_month = int(period_month)
                # Check if this is a quarter start (1,4,7,10)
                if p_month in (1, 4, 7, 10) and x_value.endswith("-01"):
                    # Could be quarterly — include 3 months
                    months = [str(m).zfill(2) for m in range(p_month, min(p_month + 3, 13))]
                    result = result.filter(month_expr.is_in(months))
                else:
                    result = result.filter(month_expr == period_month)

            # Filter by segment if stacked bar
            if curve_name and curve_name not in ("", x_value):
                # Find a categorical column that contains this segment value
                for col in filtered.columns:
                    if filtered[col].dtype in (pl.Utf8, pl.Categorical):
                        if curve_name in filtered[col].cast(pl.Utf8).unique().to_list():
                            result = result.filter(pl.col(col).cast(pl.Utf8) == curve_name)
                            break

            if result.is_empty():
                return None

            # Return a useful subset of columns
            show_cols = [c for c in result.columns if c not in ("_period",)]
            return result.select(show_cols).head(200)

        from dash import State as DashState
        register_detail_callback(
            app, "ps-bar-chart", detail_fn=_get_bar_detail,
            extra_states=[DashState("universal-portfolio-dropdown", "value")],
            reset_inputs=[
                Input("ps-metric", "value"),
                Input("ps-freq", "value"),
                Input("ps-segmentation", "value"),
            ],
        )

        @callback(
            Output("ps-waterfall-chart", "figure"),
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data"),
             Input("custom-metric-store", "data"),
             Input("ps-metric", "value"),
             Input("ps-freq", "value")],
            prevent_initial_call=True,
        )
        def update_waterfall_chart(portfolio, _tw, _cm, metric, freq):
            if not portfolio:
                return no_update
            metric = metric or "balance"
            freq = freq or "monthly"
            windowed = app_state._apply_time_window(app_state.facilities_df)
            return _build_waterfall_chart(windowed, app_state.portfolios,
                                          portfolio, metric, freq)

        def _get_waterfall_detail(click_point, curve_name, x_value, portfolio, freq):
            """Return facility rows for the clicked waterfall bar category."""
            if not portfolio or portfolio not in app_state.portfolios:
                return None
            windowed = app_state._apply_time_window(app_state.facilities_df)
            filtered = _apply_filters(windowed, app_state.portfolios[portfolio])
            if filtered.is_empty() or "reporting_date" not in filtered.columns:
                return None

            freq = freq or "monthly"
            df_with_period = _add_period_column(filtered, freq)
            periods = df_with_period["_period"].unique().sort().to_list()

            # Map x_value back to raw period
            curr_period = _x_value_to_period(x_value, periods, freq)
            if curr_period is None or curr_period not in periods:
                return None
            idx = periods.index(curr_period)
            if idx == 0:
                return None  # first period has no previous
            prev_period = periods[idx - 1]

            prev_rows = df_with_period.filter(pl.col("_period") == prev_period)
            curr_rows = df_with_period.filter(pl.col("_period") == curr_period)
            prev_ids = set(prev_rows["facility_id"].to_list())
            curr_ids = set(curr_rows["facility_id"].to_list())

            if curve_name == "Run-off":
                ids = prev_ids - curr_ids
                result = prev_rows.filter(pl.col("facility_id").is_in(list(ids)))
            elif curve_name == "New Origination":
                ids = curr_ids - prev_ids
                result = curr_rows.filter(pl.col("facility_id").is_in(list(ids)))
            elif curve_name == "Changes":
                ids = prev_ids & curr_ids
                result = curr_rows.filter(pl.col("facility_id").is_in(list(ids)))
            else:
                return None

            if result.is_empty():
                return None
            show_cols = [c for c in result.columns if c != "_period"]
            return result.select(show_cols).head(200)

        register_detail_callback(
            app, "ps-waterfall-chart", detail_fn=_get_waterfall_detail,
            extra_states=[DashState("universal-portfolio-dropdown", "value"),
                          DashState("ps-freq", "value")],
            reset_inputs=[
                Input("ps-metric", "value"),
                Input("ps-freq", "value"),
            ],
        )


register_tab(PortfolioSummaryTab())


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_metric_options(df: pl.DataFrame):
    from ..app_state import app_state
    # Always include balance; plus any user-defined custom metric columns
    allowed = {"balance"}
    allowed.update(app_state.custom_metrics.keys())
    numeric = [c for c in df.columns if c in allowed and df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32)]
    # Ensure balance appears first if present
    if "balance" in numeric:
        numeric.remove("balance")
        numeric.insert(0, "balance")
    return [{"label": c.replace("_", " ").title(), "value": c} for c in numeric]


def _get_segmentation_options(df: pl.DataFrame):
    """Return categorical columns suitable for segmentation."""
    exclude_ids = {"facility_id", "reporting_date", "origination_date", "maturity_date", "obligor_name"}
    cols = []
    for c in df.columns:
        if c in exclude_ids:
            continue
        if df[c].dtype in (pl.Utf8, pl.Categorical):
            cols.append({"label": c.replace("_", " ").title(), "value": c})
    return cols


def _apply_filters(df: pl.DataFrame, criteria):
    from ..data.dataset import Dataset
    return Dataset.apply_criteria(df, criteria)


def _resample(df: pl.DataFrame, freq: str, metric: str, segmentation: str | None):
    """Aggregate metric by date (and optional segmentation) at the given frequency."""
    if "reporting_date" not in df.columns or metric not in df.columns:
        return pl.DataFrame()

    df = _add_period_column(df, freq)

    group_cols = ["_period"]
    if segmentation and segmentation in df.columns:
        group_cols.append(segmentation)

    result = df.group_by(group_cols).agg(pl.col(metric).sum()).sort("_period")
    return result


# Palette for stacked segments
_COLORS = [
    "#a78bfa", "#2dd4bf", "#f97316", "#f472b6", "#60a5fa",
    "#fbbf24", "#34d399", "#e879f9", "#fb923c", "#38bdf8",
    "#a3e635", "#f87171", "#818cf8", "#c084fc", "#22d3ee",
]


_MONTH_ABBR = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _format_period(period_str: str, freq: str) -> str:
    """Format a period string like '2024-06-01' based on frequency."""
    year = period_str[:4]
    month = int(period_str[5:7])
    if freq == "annually":
        return year
    if freq == "quarterly":
        q = (month - 1) // 3 + 1
        return f"Q{q} {year}"
    return f"{_MONTH_ABBR[month]} {year}"


def _build_bar_chart(df, portfolios, portfolio, metric, freq, segmentation):
    """Build a (stacked) bar chart of the metric over time."""
    if portfolio not in portfolios:
        return empty_figure("Select a portfolio", 400)

    filtered = _apply_filters(df, portfolios[portfolio])
    if len(filtered) == 0 or metric not in filtered.columns:
        return empty_figure("No data", 400)

    agg = _resample(filtered, freq, metric, segmentation)
    if agg.is_empty():
        return empty_figure("No data", 400)

    fig = go.Figure()

    metric_label = metric.replace("_", " ").title()

    if segmentation and segmentation in agg.columns:
        segments = agg[segmentation].unique().sort().to_list()
        for i, seg in enumerate(segments):
            seg_data = agg.filter(pl.col(segmentation) == seg)
            seg_periods = seg_data["_period"].to_list()
            fig.add_trace(go.Bar(
                x=seg_periods,
                y=seg_data[metric].to_list(),
                name=str(seg),
                customdata=[[str(seg)] for _ in seg_periods],
                marker_color=_COLORS[i % len(_COLORS)],
            ))
        fig.update_layout(barmode="stack")
    else:
        periods_list = agg["_period"].to_list()
        fig.add_trace(go.Bar(
            x=periods_list,
            y=agg[metric].to_list(),
            customdata=[[metric_label] for _ in periods_list],
            marker_color="#a78bfa",
            name=metric_label,
        ))

    # Format x-axis tick labels based on frequency
    periods = agg["_period"].unique().sort().to_list()
    tick_labels = [_format_period(p, freq) for p in periods]

    theme = plotly_theme(
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_layout(**theme, yaxis_title=metric_label, clickmode="event")
    fig.update_xaxes(
        tickvals=periods,
        ticktext=tick_labels,
        tickangle=-45 if len(periods) > 12 else 0,
    )
    return fig


def _add_period_column(df: pl.DataFrame, freq: str) -> pl.DataFrame:
    """Add _period column to df using same logic as _resample."""
    rd = df["reporting_date"]
    date_col = pl.col("reporting_date")
    if rd.dtype != pl.Utf8:
        date_col = date_col.cast(pl.Utf8)
    year_expr = date_col.str.slice(0, 4)
    month_expr = date_col.str.slice(5, 2)
    if freq == "quarterly":
        q_month = ((month_expr.cast(pl.Int32) - 1) // 3 * 3 + 1).cast(pl.Utf8).str.pad_start(2, "0")
        return df.with_columns((year_expr + "-" + q_month + "-01").alias("_period"))
    elif freq == "annually":
        return df.with_columns((year_expr + "-01-01").alias("_period"))
    else:
        return df.with_columns((year_expr + "-" + month_expr + "-01").alias("_period"))


def _compute_period_changes(df: pl.DataFrame, freq: str, metric: str) -> pl.DataFrame:
    """Compute run-off, changes, and new origination between consecutive periods."""
    if "reporting_date" not in df.columns or metric not in df.columns or "facility_id" not in df.columns:
        return pl.DataFrame()

    df = _add_period_column(df, freq)
    periods = df["_period"].unique().sort().to_list()
    if len(periods) < 2:
        return pl.DataFrame()

    rows: list[dict] = []
    for i in range(1, len(periods)):
        prev_p, curr_p = periods[i - 1], periods[i]
        prev = df.filter(pl.col("_period") == prev_p)
        curr = df.filter(pl.col("_period") == curr_p)
        prev_ids = set(prev["facility_id"].to_list())
        curr_ids = set(curr["facility_id"].to_list())

        runoff_ids = prev_ids - curr_ids
        new_ids = curr_ids - prev_ids
        common_ids = prev_ids & curr_ids

        runoff_val = -prev.filter(pl.col("facility_id").is_in(list(runoff_ids)))[metric].sum() if runoff_ids else 0
        new_val = curr.filter(pl.col("facility_id").is_in(list(new_ids)))[metric].sum() if new_ids else 0
        if common_ids:
            common_list = list(common_ids)
            curr_sum = curr.filter(pl.col("facility_id").is_in(common_list))[metric].sum()
            prev_sum = prev.filter(pl.col("facility_id").is_in(common_list))[metric].sum()
            changes_val = curr_sum - prev_sum
        else:
            changes_val = 0

        rows.append({"_period": curr_p, "category": "Run-off", "value": runoff_val})
        rows.append({"_period": curr_p, "category": "Changes", "value": changes_val})
        rows.append({"_period": curr_p, "category": "New Origination", "value": new_val})

    return pl.DataFrame(rows)


_WATERFALL_COLORS = {
    "Run-off": "#f87171",
    "Changes": "#60a5fa",
    "New Origination": "#34d399",
}


def _build_waterfall_chart(df, portfolios, portfolio, metric, freq):
    """Build a period-over-period waterfall chart."""
    if portfolio not in portfolios:
        return empty_figure("Select a portfolio", 400)

    filtered = _apply_filters(df, portfolios[portfolio])
    if filtered.is_empty() or metric not in filtered.columns:
        return empty_figure("No data", 400)

    changes = _compute_period_changes(filtered, freq, metric)
    if changes.is_empty():
        return empty_figure("Not enough periods", 400)

    fig = go.Figure()

    for category in ["Run-off", "Changes", "New Origination"]:
        cat_data = changes.filter(pl.col("category") == category)
        periods_list = cat_data["_period"].to_list()
        fig.add_trace(go.Bar(
            x=periods_list,
            y=cat_data["value"].to_list(),
            name=category,
            customdata=[[category] for _ in periods_list],
            marker_color=_WATERFALL_COLORS[category],
        ))

    periods = changes["_period"].unique().sort().to_list()
    tick_labels = [_format_period(p, freq) for p in periods]
    metric_label = metric.replace("_", " ").title()

    theme = plotly_theme(
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_layout(**theme, barmode="relative", yaxis_title=f"{metric_label} Change",
                      clickmode="event")
    fig.update_xaxes(
        tickvals=periods,
        ticktext=tick_labels,
        tickangle=-45 if len(periods) > 12 else 0,
    )
    return fig



def _x_value_to_period(x_value: str, periods: list[str], freq: str) -> str | None:
    """Map an x_value (which may be a formatted label or raw period) to a raw period string."""
    if x_value in periods:
        return x_value
    # Try matching by formatted label
    for p in periods:
        if _format_period(p, freq) == x_value:
            return p
    return None
