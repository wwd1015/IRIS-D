"""
Role-gated tabs – SIR Analysis, Location Analysis, Financial Projection, Model Backtesting.

Each tab has basic visualizations derived from facility data.
"""

from __future__ import annotations

import plotly.graph_objs as go
import polars as pl
from dash import callback, dcc, html, Input, Output, no_update

from .registry import BaseTab, ContentLayout, TabContext, register_tab
from ..components.toolbar import DropdownControl

_THEME = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(size=12, color="rgba(255,255,255,0.7)"),
    margin=dict(l=40, r=20, t=20, b=40), showlegend=False,
)


def _apply_filters(df, criteria):
    from ..data.dataset import Dataset
    criteria = Dataset._migrate_criteria(criteria)
    for level in criteria.get("filters", []):
        col, vals = level.get("column"), level.get("values", [])
        if col and vals and col in df.columns:
            df = df.filter(pl.col(col).cast(pl.Utf8).is_in([str(v) for v in vals]))
    return df


# ── SIR Analysis (FULL) ─────────────────────────────────────────────────────

class SIRAnalysisTab(BaseTab):
    id = "sir-analysis"
    label = "SIR Analysis"
    order = 60
    required_roles = ["SAG"]
    tier = "bronze"
    tier_tooltip = "Bronze tier — set tier='bronze' in your BaseTab subclass"
    content_layout = ContentLayout.FULL

    def render_content(self, ctx: TabContext):
        fig = _build_rating_distribution(ctx.get_filtered_data(ctx.selected_portfolio))
        return html.Div([
            html.Div([
                html.H3("Rating Distribution", className="text-sm font-semibold pb-2 border-b border-ink-700"),
                dcc.Graph(id="sir-chart", figure=fig, config={"displayModeBar": False},
                          style={"height": "400px"}),
            ], className="glass-card p-4"),
        ])

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            Output("sir-chart", "figure"),
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data")],
            prevent_initial_call=True,
        )
        def update(portfolio, _tw):
            if not portfolio:
                return no_update
            return _build_rating_distribution(app_state.get_filtered_data(portfolio))


def _build_rating_distribution(df: pl.DataFrame):
    fig = go.Figure()
    if len(df) == 0:
        fig.update_layout(**_THEME, height=400)
        return fig
    counts = df["obligor_rating"].value_counts().sort("obligor_rating")
    ratings = counts["obligor_rating"].to_list()
    vals = counts["count"].to_list()
    colors = ["#22c55e" if r <= 13 else "#f59e0b" if r <= 15 else "#ef4444" for r in ratings]
    fig.add_trace(go.Bar(x=[str(r) for r in ratings], y=vals, marker_color=colors))
    fig.update_layout(**_THEME, height=400,
                      xaxis=dict(title="Rating", color="rgba(255,255,255,0.5)"),
                      yaxis=dict(title="Count", showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                                 color="rgba(255,255,255,0.5)"))
    return fig


# ── Location Analysis (FOUR_COL) ────────────────────────────────────────────

class LocationAnalysisTab(BaseTab):
    id = "location-analysis"
    label = "Location Analysis"
    order = 70
    required_roles = ["CRE SCO"]
    tier = "bronze"
    tier_tooltip = "Bronze tier — set tier='bronze' in your BaseTab subclass"
    content_layout = ContentLayout.FOUR_COL

    def render_content(self, ctx: TabContext):
        df = ctx.get_filtered_data(ctx.selected_portfolio)
        cards = _build_location_metric_cards(df)
        return html.Div(cards)

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            Output("la-metrics-container", "children"),
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data")],
            prevent_initial_call=True,
        )
        def update(portfolio, _tw):
            if not portfolio:
                return no_update
            return _build_location_metric_cards(app_state.get_filtered_data(portfolio))


def _build_location_metric_cards(df: pl.DataFrame):
    if len(df) == 0:
        return [html.Div("No data", className="glass-card p-4")] * 4

    total_bal = df["balance"].sum()
    n_loans = df["facility_id"].n_unique()
    n_markets = df["msa"].n_unique() if "msa" in df.columns else 0
    avg_bal = total_bal / n_loans if n_loans > 0 else 0

    metrics = [
        ("Total Balance", f"${total_bal:,.0f}"),
        ("Total Loans", str(n_loans)),
        ("Markets (MSAs)", str(n_markets)),
        ("Avg Loan Size", f"${avg_bal:,.0f}"),
    ]
    cards = []
    for label, value in metrics:
        cards.append(html.Div([
            html.Div(value, className="text-lg font-bold"),
            html.Div(label, className="text-xs text-slate-400 mt-1"),
        ], className="glass-card p-4 text-center"))
    return html.Div(cards, id="la-metrics-container")


# ── Financial Projection (TWO_COL) ──────────────────────────────────────────

class FinancialProjectionTab(BaseTab):
    id = "financial-projection"
    label = "Financial Projection"
    order = 80
    required_roles = ["Corp SCO"]
    tier = "bronze"
    tier_tooltip = "Bronze tier — set tier='bronze' in your BaseTab subclass"
    content_layout = ContentLayout.TWO_COL

    def get_toolbar_controls(self, ctx: TabContext):
        return [
            DropdownControl(
                id="fp-metric", label="Metric",
                options=[
                    {"label": "Balance", "value": "balance"},
                    {"label": "Free Cash Flow", "value": "free_cash_flow"},
                    {"label": "Profitability", "value": "profitability"},
                ],
                value="balance", order=10,
            ),
        ]

    def render_content(self, ctx: TabContext):
        df = ctx.get_filtered_data(ctx.selected_portfolio)
        hist_fig = _build_hist_chart(ctx.facilities_df, ctx.portfolios,
                                     ctx.selected_portfolio, "balance")
        dist_fig = _build_distribution(df, "balance")
        return html.Div([
            html.Div([
                html.H3("Historical Trend", className="text-sm font-semibold pb-2 border-b border-ink-700"),
                dcc.Graph(id="fp-hist-chart", figure=hist_fig,
                          config={"displayModeBar": False}, style={"height": "350px"}),
            ], className="glass-card p-4"),
            html.Div([
                html.H3("Current Distribution", className="text-sm font-semibold pb-2 border-b border-ink-700"),
                dcc.Graph(id="fp-dist-chart", figure=dist_fig,
                          config={"displayModeBar": False}, style={"height": "350px"}),
            ], className="glass-card p-4"),
        ])

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            [Output("fp-hist-chart", "figure"),
             Output("fp-dist-chart", "figure")],
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data"),
             Input("fp-metric", "value")],
            prevent_initial_call=True,
        )
        def update(portfolio, _tw, metric):
            if not portfolio:
                return no_update, no_update
            metric = metric or "balance"
            windowed = app_state._apply_time_window(app_state.facilities_df)
            hist = _build_hist_chart(windowed, app_state.portfolios, portfolio, metric)
            dist = _build_distribution(app_state.get_filtered_data(portfolio), metric)
            return hist, dist


def _build_hist_chart(df, portfolios, portfolio, metric):
    fig = go.Figure()
    if portfolio not in portfolios:
        fig.update_layout(**_THEME, height=350)
        return fig
    filtered = _apply_filters(df, portfolios[portfolio])
    if metric not in filtered.columns or len(filtered) == 0:
        fig.update_layout(**_THEME, height=350)
        return fig
    ts = filtered.group_by("reporting_date").agg(pl.col(metric).mean()).sort("reporting_date")
    fig.add_trace(go.Scatter(
        x=ts["reporting_date"].to_list(), y=ts[metric].to_list(),
        mode="lines+markers", line=dict(color="#a78bfa", width=2),
    ))
    fig.update_layout(**_THEME, height=350,
                      xaxis=dict(showgrid=False, color="rgba(255,255,255,0.5)"),
                      yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                                 color="rgba(255,255,255,0.5)"))
    return fig


def _build_distribution(df: pl.DataFrame, metric):
    fig = go.Figure()
    if len(df) == 0 or metric not in df.columns:
        fig.update_layout(**_THEME, height=350)
        return fig
    vals = df[metric].drop_nulls().to_list()
    fig.add_trace(go.Histogram(x=vals, nbinsx=30, marker_color="#8b5cf6"))
    fig.update_layout(**_THEME, height=350,
                      xaxis=dict(title=metric.replace("_", " ").title(),
                                 color="rgba(255,255,255,0.5)"),
                      yaxis=dict(title="Count", showgrid=True,
                                 gridcolor="rgba(255,255,255,0.06)",
                                 color="rgba(255,255,255,0.5)"))
    return fig


# ── Model Backtesting (WIDE_LEFT) ───────────────────────────────────────────

class ModelBacktestingTab(BaseTab):
    id = "model-backtesting"
    label = "Model Backtesting"
    order = 90
    required_roles = ["BA"]
    tier = "bronze"
    tier_tooltip = "Bronze tier — set tier='bronze' in your BaseTab subclass"
    content_layout = ContentLayout.WIDE_LEFT

    def render_content(self, ctx: TabContext):
        df = ctx.get_filtered_data(ctx.selected_portfolio)
        fig = _build_rating_migration(df)
        summary = _build_backtest_summary(df)
        return html.Div([
            html.Div([
                html.H3("Rating Migration", className="text-sm font-semibold pb-2 border-b border-ink-700"),
                dcc.Graph(id="mb-chart", figure=fig, config={"displayModeBar": False},
                          style={"height": "400px"}),
            ], className="glass-card p-4"),
            html.Div(id="mb-summary", children=summary, className="glass-card p-4"),
        ])

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            [Output("mb-chart", "figure"),
             Output("mb-summary", "children")],
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data")],
            prevent_initial_call=True,
        )
        def update(portfolio, _tw):
            if not portfolio:
                return no_update, no_update
            df = app_state.get_filtered_data(portfolio)
            return _build_rating_migration(df), _build_backtest_summary(df)


def _build_rating_migration(df: pl.DataFrame):
    fig = go.Figure()
    if len(df) == 0:
        fig.update_layout(**_THEME, height=400)
        return fig
    # Rating bucket counts
    buckets = {"Pass (1-13)": 0, "Watch (14)": 0, "Criticized (15-16)": 0, "Default (17)": 0}
    for row in df.iter_rows(named=True):
        r = row.get("obligor_rating")
        if r is None:
            continue
        if r <= 13:
            buckets["Pass (1-13)"] += 1
        elif r == 14:
            buckets["Watch (14)"] += 1
        elif r <= 16:
            buckets["Criticized (15-16)"] += 1
        else:
            buckets["Default (17)"] += 1
    colors = ["#22c55e", "#f59e0b", "#f97316", "#ef4444"]
    fig.add_trace(go.Bar(
        x=list(buckets.keys()), y=list(buckets.values()),
        marker_color=colors,
    ))
    fig.update_layout(**_THEME, height=400,
                      xaxis=dict(color="rgba(255,255,255,0.5)"),
                      yaxis=dict(title="Facilities", showgrid=True,
                                 gridcolor="rgba(255,255,255,0.06)",
                                 color="rgba(255,255,255,0.5)"))
    return fig


def _build_backtest_summary(df: pl.DataFrame):
    if len(df) == 0:
        return html.Div("No data", className="text-slate-400")
    n = len(df)
    n_default = len(df.filter(pl.col("obligor_rating") == 17))
    default_rate = n_default / n * 100 if n > 0 else 0
    avg_rating = df["obligor_rating"].mean()

    def _row(label, value):
        return html.Div([
            html.Span(label, className="text-xs text-slate-400"),
            html.Span(value, className="text-xs font-semibold"),
        ], className="flex justify-between")

    return html.Div([
        html.H3("Summary", className="text-sm font-semibold mb-3"),
        html.Hr(className="border-slate-700 mb-3"),
        html.Div([
            _row("Total Facilities", str(n)),
            _row("Defaults", str(n_default)),
            _row("Default Rate", f"{default_rate:.2f}%"),
            _row("Avg Rating", f"{avg_rating:.1f}" if avg_rating else "N/A"),
        ], className="space-y-2"),
    ])


# ── Register all ─────────────────────────────────────────────────────────────

register_tab(SIRAnalysisTab())
register_tab(LocationAnalysisTab())
register_tab(FinancialProjectionTab())
register_tab(ModelBacktestingTab())
