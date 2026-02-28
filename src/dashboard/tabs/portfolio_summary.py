"""
Portfolio Summary tab – the default landing page.

Shows top holdings bar chart and industry/property distribution pie chart
with a positions stats sidebar.
"""

from __future__ import annotations

from datetime import datetime

import plotly.graph_objs as go
import polars as pl
from dash import callback, dcc, html, Input, Output, no_update

from .registry import BaseTab, ContentLayout, TabContext, register_tab
from ..components.toolbar import DropdownControl


class PortfolioSummaryTab(BaseTab):
    id = "portfolio-summary"
    label = "Portfolio Summary"
    order = 10
    tier = "gold"
    tier_tooltip = "Gold tier — set tier='gold' in your BaseTab subclass"
    content_layout = ContentLayout.TWO_COL

    def get_toolbar_controls(self, ctx: TabContext):
        return [
            DropdownControl(
                id="ps-metric", label="Chart Metric",
                options=[
                    {"label": "Balance", "value": "balance"},
                    {"label": "Obligor Rating", "value": "obligor_rating"},
                ],
                value="balance", order=10,
            ),
        ]

    def render_content(self, ctx: TabContext):
        bar_fig, pie_fig = _build_charts(
            ctx.get_filtered_data(ctx.selected_portfolio), "balance",
        )
        return html.Div([
            html.Div([
                html.Div([
                    html.H3("Top 10 Holdings", className="text-sm font-semibold"),
                    html.Div(id="ps-bar-subtitle", className="text-xs text-slate-400"),
                ], className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-ink-700"),
                dcc.Graph(id="ps-bar-chart", figure=bar_fig, config={"displayModeBar": False},
                          style={"height": "350px"}),
            ], className="glass-card p-4"),
            html.Div([
                html.Div([
                    html.H3("Distribution", className="text-sm font-semibold"),
                    html.Div(id="ps-pie-subtitle", className="text-xs text-slate-400"),
                ], className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-ink-700"),
                dcc.Graph(id="ps-pie-chart", figure=pie_fig, config={"displayModeBar": False},
                          style={"height": "350px"}),
            ], className="glass-card p-4"),
        ])

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            [Output("ps-bar-chart", "figure"),
             Output("ps-pie-chart", "figure"),
             Output("ps-bar-subtitle", "children"),
             Output("ps-pie-subtitle", "children")],
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data"),
             Input("ps-metric", "value")],
            prevent_initial_call=True,
        )
        def update_charts(portfolio, _tw, metric):
            if not portfolio:
                return no_update, no_update, no_update, no_update
            df = app_state.get_filtered_data(portfolio)
            metric = metric or "balance"
            bar_fig, pie_fig = _build_charts(df, metric)
            lob_vals = df["lob"].to_list() if len(df) > 0 else []
            lob_label = "Corporate Banking" if "Corporate Banking" in lob_vals else "CRE"
            pie_label = "by Industry" if lob_label == "Corporate Banking" else "by Property Type"
            return bar_fig, pie_fig, f"by {metric.replace('_', ' ').title()}", pie_label


register_tab(PortfolioSummaryTab())


# ── Helpers ──────────────────────────────────────────────────────────────────

_THEME = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(size=12, color="rgba(255,255,255,0.7)"),
    margin=dict(l=20, r=20, t=20, b=20), height=350, showlegend=False,
)


def _build_charts(df: pl.DataFrame, metric: str):
    if len(df) == 0:
        empty = go.Figure()
        empty.update_layout(**_THEME)
        empty.add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return empty, empty

    # Bar — top 10 by metric
    top = df.group_by("obligor_name").agg(pl.col(metric).sum()).sort(metric, descending=True).head(10)
    names = top["obligor_name"].to_list()
    vals = top[metric].to_list()
    bar = go.Figure(go.Bar(
        x=vals, y=list(range(len(vals))), orientation="h",
        marker_color=["#a78bfa", "#8b5cf6", "#7c3aed", "#6d28d9", "#5b21b6",
                       "#4c1d95", "#a78bfa", "#8b5cf6", "#7c3aed", "#6d28d9"],
        text=names, textposition="inside",
        textfont=dict(size=11, color="rgba(255,255,255,0.95)"),
    ))
    bar.update_layout(**_THEME, yaxis=dict(showticklabels=False, autorange="reversed"),
                      xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"))

    # Pie — by industry or property type
    lob_vals = df["lob"].to_list()
    if "Corporate Banking" in lob_vals:
        cat_col = "industry"
    else:
        cat_col = "cre_property_type"
    cat_data = df[cat_col].value_counts().sort("count", descending=True)
    pie = go.Figure(go.Pie(
        labels=cat_data[cat_col].to_list(), values=cat_data["count"].to_list(),
        hole=0.4,
        marker_colors=["#a78bfa", "#8b5cf6", "#7c3aed", "#6d28d9", "#5b21b6",
                        "#4c1d95", "#2dd4bf", "#14b8a6"],
    ))
    pie.update_layout(**_THEME)
    return bar, pie
