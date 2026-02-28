"""
Financial Trend tab – three metric sparkline cards for period comparison.

Layout: THREE_COL — each column shows a different metric's trend over time.
"""

from __future__ import annotations

import plotly.graph_objs as go
import polars as pl
from dash import callback, dcc, html, Input, Output, no_update

from .registry import BaseTab, ContentLayout, TabContext, register_tab
from ..components.toolbar import DropdownControl


class FinancialTrendTab(BaseTab):
    id = "financial-trend"
    label = "Financial Trend"
    order = 40
    tier = "silver"
    tier_tooltip = "Silver tier — set tier='silver' in your BaseTab subclass"
    content_layout = ContentLayout.THREE_COL

    def get_toolbar_controls(self, ctx: TabContext):
        metric_opts = _get_metric_options(ctx.get_filtered_data(ctx.selected_portfolio))
        defaults = [o["value"] for o in metric_opts[:3]]
        return [
            DropdownControl(
                id="ft-metric-1", label="Metric 1",
                options=metric_opts, value=defaults[0] if len(defaults) > 0 else None,
                order=10,
            ),
            DropdownControl(
                id="ft-metric-2", label="Metric 2",
                options=metric_opts, value=defaults[1] if len(defaults) > 1 else None,
                order=20,
            ),
            DropdownControl(
                id="ft-metric-3", label="Metric 3",
                options=metric_opts, value=defaults[2] if len(defaults) > 2 else None,
                order=30,
            ),
        ]

    def render_content(self, ctx: TabContext):
        df = ctx.get_filtered_data(ctx.selected_portfolio)
        metric_opts = _get_metric_options(df)
        defaults = [o["value"] for o in metric_opts[:3]]
        cards = []
        for i in range(3):
            m = defaults[i] if i < len(defaults) else None
            fig = _build_sparkline(ctx.facilities_df, ctx.portfolios,
                                   ctx.selected_portfolio, m)
            label = m.replace("_", " ").title() if m else "No metric"
            current = _current_value(df, m)
            cards.append(html.Div([
                html.Div([
                    html.H3(label, className="text-sm font-semibold"),
                    html.Div(current, className="text-xl font-bold mt-1",
                             id=f"ft-value-{i+1}"),
                ], className="pb-2 border-b border-slate-100 dark:border-ink-700"),
                dcc.Graph(id=f"ft-chart-{i+1}", figure=fig,
                          config={"displayModeBar": False}, style={"height": "250px"}),
            ], className="glass-card p-4"))
        return html.Div(cards)

    def register_callbacks(self, app):
        from ..app_state import app_state

        for i in range(1, 4):
            @callback(
                [Output(f"ft-chart-{i}", "figure"),
                 Output(f"ft-value-{i}", "children")],
                [Input("universal-portfolio-dropdown", "value"),
                 Input("time-window-store", "data"),
                 Input(f"ft-metric-{i}", "value")],
                prevent_initial_call=True,
            )
            def update(portfolio, _tw, metric, _idx=i):
                if not portfolio or not metric:
                    return no_update, no_update
                windowed = app_state._apply_time_window(app_state.facilities_df)
                fig = _build_sparkline(windowed, app_state.portfolios, portfolio, metric)
                df = app_state.get_filtered_data(portfolio)
                val = _current_value(df, metric)
                return fig, val


register_tab(FinancialTrendTab())


# ── Helpers ──────────────────────────────────────────────────────────────────

_THEME = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(size=11, color="rgba(255,255,255,0.6)"),
    margin=dict(l=35, r=10, t=10, b=30), height=250, showlegend=False,
    xaxis=dict(showgrid=False, color="rgba(255,255,255,0.4)"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", color="rgba(255,255,255,0.4)"),
)


def _get_metric_options(df: pl.DataFrame):
    exclude = {"facility_id", "obligor_name", "origination_date", "maturity_date",
                "reporting_date", "lob", "industry", "cre_property_type", "msa", "sir", "risk_category"}
    if len(df) == 0:
        return []
    numeric = [c for c in df.columns if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32) and c not in exclude]
    return [{"label": c.replace("_", " ").title(), "value": c} for c in numeric]


def _apply_filters(df, criteria):
    from ..data.dataset import Dataset
    criteria = Dataset._migrate_criteria(criteria)
    for level in criteria.get("filters", []):
        col, vals = level.get("column"), level.get("values", [])
        if col and vals and col in df.columns:
            df = df.filter(pl.col(col).cast(pl.Utf8).is_in([str(v) for v in vals]))
    return df


def _build_sparkline(facilities_df, portfolios, portfolio, metric):
    fig = go.Figure()
    if not metric or portfolio not in portfolios:
        fig.update_layout(**_THEME)
        return fig
    filtered = _apply_filters(facilities_df, portfolios[portfolio])
    if metric not in filtered.columns or len(filtered) == 0:
        fig.update_layout(**_THEME)
        return fig
    ts = filtered.group_by("reporting_date").agg(pl.col(metric).mean()).sort("reporting_date")
    fig.add_trace(go.Scatter(
        x=ts["reporting_date"].to_list(), y=ts[metric].to_list(),
        mode="lines", fill="tozeroy",
        line=dict(color="#a78bfa", width=2),
        fillcolor="rgba(167,139,250,0.1)",
    ))
    fig.update_layout(**_THEME)
    return fig


def _current_value(df: pl.DataFrame, metric):
    if not metric or len(df) == 0 or metric not in df.columns:
        return "N/A"
    val = df[metric].mean()
    if val is None:
        return "N/A"
    if metric == "balance":
        return f"${val:,.0f}"
    return f"{val:,.2f}"
