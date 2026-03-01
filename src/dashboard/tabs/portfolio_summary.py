"""
Portfolio Summary tab – the default landing page.

Layout: WIDE_LEFT (2fr bar chart | 1fr placeholder).
Toolbar: Metric (all numeric cols) + Frequency (M/Q/A).
Left card: time-series bar chart with optional segmentation stacked bars.
"""

from __future__ import annotations

import plotly.graph_objs as go
import polars as pl
from dash import callback, dcc, html, Input, Output, no_update

from .registry import BaseTab, ContentLayout, TabContext, register_tab
from ..components.toolbar import DropdownControl
from ..components.mixins.click_detail import chart_with_detail_layout, register_detail_callback
from ..utils.helpers import plotly_theme


class PortfolioSummaryTab(BaseTab):
    id = "portfolio-summary"
    label = "Portfolio Summary"
    order = 10
    tier = "gold"
    tier_tooltip = "Gold tier — set tier='gold' in your BaseTab subclass"
    content_layout = ContentLayout.WIDE_LEFT

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
                html.Div("Placeholder — right panel coming soon",
                         className="p-4", style={"color": "var(--text-muted)"}),
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


register_tab(PortfolioSummaryTab())


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_metric_options(df: pl.DataFrame):
    exclude = {"facility_id", "obligor_name", "origination_date", "maturity_date",
               "reporting_date", "lob", "industry", "cre_property_type", "msa", "sir", "risk_category"}
    numeric = [c for c in df.columns if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32) and c not in exclude]
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
    criteria = Dataset._migrate_criteria(criteria)
    for level in criteria.get("filters", []):
        col, vals = level.get("column"), level.get("values", [])
        if col and vals and col in df.columns:
            df = df.filter(pl.col(col).cast(pl.Utf8).is_in([str(v) for v in vals]))
    return df


def _resample(df: pl.DataFrame, freq: str, metric: str, segmentation: str | None):
    """Aggregate metric by date (and optional segmentation) at the given frequency."""
    if "reporting_date" not in df.columns or metric not in df.columns:
        return pl.DataFrame()

    # Work with string dates — extract year/month via substring (fast, no parsing)
    rd = df["reporting_date"]
    date_col = pl.col("reporting_date")
    if rd.dtype != pl.Utf8:
        date_col = date_col.cast(pl.Utf8)

    year_expr = date_col.str.slice(0, 4)   # "2024"
    month_expr = date_col.str.slice(5, 2)  # "06"

    if freq == "quarterly":
        q_month = ((month_expr.cast(pl.Int32) - 1) // 3 * 3 + 1).cast(pl.Utf8).str.pad_start(2, "0")
        df = df.with_columns((year_expr + "-" + q_month + "-01").alias("_period"))
    elif freq == "annually":
        df = df.with_columns((year_expr + "-01-01").alias("_period"))
    else:
        df = df.with_columns((year_expr + "-" + month_expr + "-01").alias("_period"))

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
    fig = go.Figure()

    if portfolio not in portfolios:
        fig.update_layout(**plotly_theme(height=400))
        fig.add_annotation(text="Select a portfolio", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    filtered = _apply_filters(df, portfolios[portfolio])
    if len(filtered) == 0 or metric not in filtered.columns:
        fig.update_layout(**plotly_theme(height=400))
        fig.add_annotation(text="No data", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    agg = _resample(filtered, freq, metric, segmentation)
    if agg.is_empty():
        fig.update_layout(**plotly_theme(height=400))
        fig.add_annotation(text="No data", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

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
