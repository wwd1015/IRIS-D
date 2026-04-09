"""
Vintage Analysis tab – cohort default rate curves.

Layout: WIDE_RIGHT (1fr config | 2fr chart).
"""

from __future__ import annotations

from datetime import date, timedelta

import plotly.graph_objs as go
import polars as pl
from dash import callback, dcc, html, Input, Output, no_update

from .registry import BaseTab, ContentLayout, TabContext, register_tab
from ..components.toolbar import DropdownControl


class VintageAnalysisTab(BaseTab):
    id = "vintage-analysis"
    label = "Vintage Analysis"
    order = 50
    tier = "silver"
    tier_tooltip = "Silver tier — set tier='silver' in your BaseTab subclass"
    content_layout = ContentLayout.WIDE_RIGHT
    primary_column = 1

    def get_toolbar_controls(self, ctx: TabContext):
        return [
            DropdownControl(
                id="va-type", label="Analysis",
                options=[
                    {"label": "Default Rates", "value": "default_rates"},
                    {"label": "Metric Trend", "value": "metric_trend"},
                ],
                value="default_rates", order=10,
            ),
        ]

    def render_content(self, ctx: TabContext):
        quarterly_opts, default_quarters = _quarter_options(ctx.facilities_df)
        metric_opts = _metric_options(ctx.facilities_df)
        fig = _build_vintage_chart(ctx.facilities_df, ctx.portfolios,
                                   ctx.selected_portfolio, default_quarters, "default_rates", None)
        return html.Div([
            # Left narrow panel — cohort selectors
            html.Div([
                html.H3("Cohort Settings", className="text-sm font-semibold mb-3"),
                html.Div([
                    html.Span("Quarterly Cohorts", className="control-label"),
                    dcc.Dropdown(
                        id="va-quarters", options=quarterly_opts, value=default_quarters,
                        multi=True, placeholder="Select cohorts…",
                        className="text-xs", style={"fontSize": "12px"},
                    ),
                ], className="mb-3"),
                html.Div([
                    html.Span("Metric (for trend)", className="control-label"),
                    dcc.Dropdown(
                        id="va-metric", options=metric_opts,
                        value=metric_opts[0]["value"] if metric_opts else None,
                        className="text-xs", style={"fontSize": "12px"},
                    ),
                ], id="va-metric-wrapper"),
            ], className="glass-card p-4"),
            # Right wide panel — chart
            html.Div([
                dcc.Graph(id="va-chart", figure=fig, config={"displayModeBar": False},
                          style={"height": "400px"}),
            ], className="glass-card p-4"),
        ])

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            Output("va-chart", "figure"),
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data"),
             Input("va-quarters", "value"),
             Input("va-type", "value"),
             Input("va-metric", "value")],
            prevent_initial_call=True,
        )
        def update(portfolio, _tw, quarters, analysis_type, metric):
            if not portfolio or not quarters:
                return no_update
            windowed = app_state._apply_time_window(app_state.facilities_df)
            filtered = _apply_filters(windowed, app_state.portfolios.get(portfolio, {}))
            return _build_vintage_chart(filtered, app_state.portfolios,
                                        portfolio, quarters, analysis_type or "default_rates", metric)


register_tab(VintageAnalysisTab())


# ── Helpers ──────────────────────────────────────────────────────────────────

_COLORS = ["#b53333", "#d97757", "#4d8b6f", "#5e5d59", "#c96442", "#87867f", "#6da58b", "#a0472e"]

_THEME = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(size=12, color="#b0aea5"),
    margin=dict(l=40, r=20, t=20, b=40), height=400,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    xaxis=dict(title="Quarters Since Cohort", tickmode="linear", showgrid=False,
               color="#87867f"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
               color="#87867f"),
)


def _apply_filters(df, criteria):
    from ..data.dataset import Dataset
    criteria = Dataset._migrate_criteria(criteria)
    for level in criteria.get("filters", []):
        col, vals = level.get("column"), level.get("values", [])
        if col and vals and col in df.columns:
            df = df.filter(pl.col(col).cast(pl.Utf8).is_in([str(v) for v in vals]))
    return df


def _quarter_options(df: pl.DataFrame):
    fdf = df
    if fdf["origination_date"].dtype == pl.Utf8:
        fdf = fdf.with_columns(pl.col("origination_date").str.to_datetime())
    dates = fdf["origination_date"].drop_nulls().unique().sort().to_list()
    seen, opts = set(), []
    for d in dates:
        if not hasattr(d, "year"):
            continue
        lbl = f"{d.year}Q{(d.month - 1) // 3 + 1}"
        if lbl not in seen:
            seen.add(lbl)
            opts.append({"label": lbl, "value": lbl})
    defaults = [o["value"] for o in opts[-3:]]
    return opts, defaults


def _metric_options(df: pl.DataFrame):
    exclude = {"facility_id", "obligor_name", "origination_date", "maturity_date",
                "reporting_date", "lob", "industry", "cre_property_type", "msa", "sir", "risk_category"}
    numeric = [c for c in df.columns if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32) and c not in exclude]
    return [{"label": c.replace("_", " ").title(), "value": c} for c in numeric]


def _quarter_bounds(year, q):
    sm = (q - 1) * 3 + 1
    start = date(year, sm, 1)
    end = date(year, sm + 3, 1) - timedelta(days=1) if q < 4 else date(year + 1, 1, 1) - timedelta(days=1)
    return start, end


def _build_vintage_chart(df, portfolios, portfolio, quarters, analysis_type, metric):
    fig = go.Figure()
    if len(df) == 0 or not quarters:
        fig.update_layout(**_THEME)
        return fig

    # Ensure datetime columns
    if df["origination_date"].dtype == pl.Utf8:
        df = df.with_columns(pl.col("origination_date").str.to_datetime())
    if df["reporting_date"].dtype == pl.Utf8:
        df = df.with_columns(pl.col("reporting_date").str.to_datetime())

    max_rd = df["reporting_date"].max()
    max_y, max_q = max_rd.year, (max_rd.month - 1) // 3 + 1

    for i, quarter in enumerate(quarters):
        year, q = int(quarter[:4]), int(quarter[5:])
        _, qe = _quarter_bounds(year, q)
        max_qts = max(1, min(((max_y - year) * 4 + (max_q - q)) + 1, 20))

        # Trailing 4-quarter cohort
        tq, ty = q - 3, year
        while tq <= 0:
            tq += 4
            ty -= 1
        ts = date(ty, (tq - 1) * 3 + 1, 1)

        cohort = df.filter((pl.col("origination_date") >= ts) & (pl.col("origination_date") <= qe))
        if len(cohort) == 0:
            continue
        obligors = cohort.filter(pl.col("obligor_rating") < 17)["obligor_name"].unique().to_list()
        n = len(obligors)
        if n == 0:
            continue

        values = []
        for qi in range(max_qts):
            ty2, tq2 = year, q + qi
            while tq2 > 4:
                tq2 -= 4
                ty2 += 1
            qs, qe2 = _quarter_bounds(ty2, tq2)
            qd = df.filter(
                pl.col("obligor_name").is_in(obligors)
                & (pl.col("reporting_date") >= qs)
                & (pl.col("reporting_date") <= qe2)
            )
            if analysis_type == "metric_trend" and metric and metric in qd.columns and len(qd) > 0:
                values.append(qd.filter(pl.col("obligor_rating") < 17)[metric].mean())
            elif len(qd) > 0:
                defaults = qd.filter(pl.col("obligor_rating") == 17)["obligor_name"].n_unique()
                values.append(defaults / n * 100)
            else:
                values.append(0 if analysis_type != "metric_trend" else None)

        fig.add_trace(go.Scatter(
            x=list(range(max_qts)), y=values, mode="lines+markers",
            name=f"{quarter} (n={n})",
            line=dict(color=_COLORS[i % len(_COLORS)], width=3),
            marker=dict(size=6),
        ))

    y_title = "Cumulative Default Rate (%)" if analysis_type != "metric_trend" else (
        metric.replace("_", " ").title() if metric else "Metric")
    fig.update_layout(**_THEME)
    fig.update_layout(yaxis_title=y_title)
    return fig
