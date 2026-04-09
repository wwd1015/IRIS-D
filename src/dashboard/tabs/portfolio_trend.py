"""
Portfolio Trend tab – time-series metric chart with benchmark comparison.

Layout: WIDE_LEFT (2fr chart | 1fr metric summary stats).
"""

from __future__ import annotations

import io
import csv

import plotly.graph_objs as go
import polars as pl
from dash import callback, dcc, html, Input, Output, State, no_update

from .registry import BaseTab, ContentLayout, TabContext, register_tab
from ..components.toolbar import DropdownControl
from ..utils.helpers import plotly_theme


class PortfolioTrendTab(BaseTab):
    id = "portfolio-trend"
    label = "Portfolio Trend"
    order = 30
    tier = "silver"
    tier_tooltip = "Silver tier — set tier='silver' in your BaseTab subclass"
    content_layout = ContentLayout.WIDE_LEFT

    def get_toolbar_controls(self, ctx: TabContext):
        metric_opts = _get_metric_options(ctx.facilities_df)
        portfolio_opts = [{"label": p, "value": p} for p in ctx.available_portfolios]
        return [
            DropdownControl(
                id="pt-metric", label="Metric",
                options=metric_opts,
                value=metric_opts[0]["value"] if metric_opts else "balance",
                order=10,
            ),
            DropdownControl(
                id="pt-agg", label="Aggregation",
                options=[{"label": "Average", "value": "avg"}, {"label": "Sum", "value": "sum"}],
                value="avg", order=20,
            ),
            DropdownControl(
                id="pt-benchmark", label="Benchmark",
                options=portfolio_opts, value=None,
                placeholder="Select benchmark…", order=30,
            ),
        ]

    def render_content(self, ctx: TabContext):
        metric = "balance"
        agg = "avg"
        fig = _build_trend_chart(ctx.facilities_df, ctx.portfolios,
                                 ctx.selected_portfolio, None, metric, agg)
        stats = _build_stats_panel(ctx.facilities_df, ctx.portfolios,
                                   ctx.selected_portfolio, None, metric, agg)
        return html.Div([
            html.Div([
                html.Div([
                    html.Div(style={"flex": "1"}),
                    html.Button("Download CSV", id="pt-download-btn",
                                className="btn btn-outline btn-sm"),
                ], className="flex items-center mb-2"),
                dcc.Download(id="pt-download"),
                dcc.Graph(id="pt-chart", figure=fig, config={"displayModeBar": False},
                          style={"height": "400px"}),
            ], className="glass-card p-4"),
            html.Div(id="pt-stats", children=stats, className="glass-card p-4"),
        ])

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            [Output("pt-chart", "figure"),
             Output("pt-stats", "children")],
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data"),
             Input("pt-metric", "value"),
             Input("pt-agg", "value"),
             Input("pt-benchmark", "value")],
            prevent_initial_call=True,
        )
        def update_chart(portfolio, _tw, metric, agg, benchmark):
            if not portfolio:
                return no_update, no_update
            metric = metric or "balance"
            agg = agg or "avg"
            windowed = app_state._apply_time_window(app_state.facilities_df)
            fig = _build_trend_chart(windowed, app_state.portfolios,
                                     portfolio, benchmark, metric, agg)
            stats = _build_stats_panel(windowed, app_state.portfolios,
                                       portfolio, benchmark, metric, agg)
            return fig, stats

        @callback(
            Output("pt-download", "data"),
            Input("pt-download-btn", "n_clicks"),
            [State("universal-portfolio-dropdown", "value"),
             State("pt-metric", "value"),
             State("pt-agg", "value"),
             State("pt-benchmark", "value")],
            prevent_initial_call=True,
        )
        def download_csv(n_clicks, portfolio, metric, agg, benchmark):
            if not n_clicks or not portfolio:
                return no_update
            metric = metric or "balance"
            agg = agg or "avg"
            windowed = app_state._apply_time_window(app_state.facilities_df)
            dates, vals = _get_timeseries(windowed, app_state.portfolios,
                                          portfolio, metric, agg)
            buf = io.StringIO()
            writer = csv.writer(buf)
            if benchmark:
                bd, bv = _get_timeseries(windowed, app_state.portfolios,
                                         benchmark, metric, agg)
                writer.writerow(["Date", f"{portfolio} ({metric})", f"{benchmark} ({metric})"])
                bench_map = dict(zip([str(d) for d in bd], bv)) if bd else {}
                for d, v in zip(dates, vals):
                    writer.writerow([str(d), v, bench_map.get(str(d), "")])
            else:
                writer.writerow(["Date", f"{portfolio} ({metric})"])
                for d, v in zip(dates, vals):
                    writer.writerow([str(d), v])
            return dcc.send_string(buf.getvalue(),
                                   filename=f"portfolio_trend_{metric}.csv")


register_tab(PortfolioTrendTab())


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_metric_options(df: pl.DataFrame):
    exclude = {"facility_id", "obligor_name", "origination_date", "maturity_date",
                "reporting_date", "lob", "industry", "cre_property_type", "msa", "sir", "risk_category"}
    numeric = [c for c in df.columns if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32) and c not in exclude]
    return [{"label": c.replace("_", " ").title(), "value": c} for c in numeric]


def _apply_filters(df: pl.DataFrame, criteria):
    from ..data.dataset import Dataset
    return Dataset.apply_criteria(df, criteria)


def _get_timeseries(df, portfolios, name, metric, agg):
    """Return (dates, values) for a portfolio metric time-series."""
    if name not in portfolios or not metric:
        return [], []
    filtered = _apply_filters(df, portfolios[name])
    if metric not in filtered.columns or len(filtered) == 0:
        return [], []
    expr = pl.col(metric).sum() if agg == "sum" else pl.col(metric).mean()
    result = filtered.group_by("reporting_date").agg(expr).sort("reporting_date")
    if result.is_empty():
        return [], []
    return result["reporting_date"].to_list(), result[metric].to_list()


def _build_trend_chart(df, portfolios, selected, benchmark, metric, agg):
    fig = go.Figure()
    dates, vals = _get_timeseries(df, portfolios, selected, metric, agg)
    if dates:
        fig.add_trace(go.Scatter(x=dates, y=vals, mode="lines+markers", name="Selected",
                                 line=dict(color="#c96442", width=3)))
    if benchmark:
        bd, bv = _get_timeseries(df, portfolios, benchmark, metric, agg)
        if bd:
            fig.add_trace(go.Scatter(x=bd, y=bv, mode="lines+markers", name="Benchmark",
                                     line=dict(color="#4d8b6f", width=3, dash="dash")))
    theme = plotly_theme(
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_layout(**theme)
    if not dates:
        fig.add_annotation(text="Select a metric", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
    return fig


def _fmt(val, metric):
    """Format a metric value for display."""
    if val is None:
        return "N/A"
    if metric == "balance":
        return f"${val:,.0f}"
    return f"{val:,.2f}"


def _compute_stats(vals):
    """Compute summary statistics from a time-series values list."""
    if not vals:
        return None
    non_null = [v for v in vals if v is not None]
    if not non_null:
        return None

    current = non_null[-1]
    avg_all = sum(non_null) / len(non_null)
    peak = max(non_null)
    trough = min(non_null)

    recent_4 = non_null[-4:] if len(non_null) >= 4 else non_null
    avg_12m = sum(recent_4) / len(recent_4)

    recent_20 = non_null[-20:] if len(non_null) >= 20 else non_null
    avg_5y = sum(recent_20) / len(recent_20)

    return {
        "current": current, "average": avg_all,
        "peak": peak, "trough": trough,
        "avg_12m": avg_12m, "avg_5y": avg_5y,
    }


def _trend_badge(current, reference):
    """Return a pill-shaped badge with colored % change."""
    if current is None or reference is None or reference == 0:
        return html.Span("—", className="stat-trend-badge stat-trend-badge--neutral")
    pct = (current - reference) / abs(reference) * 100
    if pct > 0:
        cls = "stat-trend-badge stat-trend-badge--up"
        text = f"+{pct:.1f}%"
    elif pct < 0:
        cls = "stat-trend-badge stat-trend-badge--down"
        text = f"{pct:.1f}%"
    else:
        cls = "stat-trend-badge stat-trend-badge--neutral"
        text = "0.0%"
    return html.Span(text, className=cls)


def _stat_card(label, value_str, badge=None):
    """A single KPI-style stat with optional trend badge."""
    return html.Div([
        html.Div(label, className="stat-card-label"),
        html.Div([
            html.Span(value_str, className="stat-card-value"),
            *([] if badge is None else [badge]),
        ], className="stat-card-row"),
    ], className="stat-card")


def _section_header(text, color=None):
    style = {"color": color} if color else {}
    return html.Div(text, className="stat-section-header", style=style)


def _build_stats_panel(df, portfolios, portfolio, benchmark, metric, agg):
    """Build a modern stats panel summarizing the selected metric's time-series."""
    _, vals = _get_timeseries(df, portfolios, portfolio, metric, agg)
    stats = _compute_stats(vals)
    metric_label = metric.replace("_", " ").title() if metric else "Metric"

    if stats is None:
        return html.Div("No data available", className="p-4",
                         style={"color": "var(--text-muted)"})

    children = [
        html.Div(metric_label, className="stat-panel-title"),
        html.Div([
            _stat_card("Current", _fmt(stats["current"], metric)),
            _stat_card("Average", _fmt(stats["average"], metric)),
        ], className="stat-card-grid"),
        html.Div([
            _stat_card("Peak", _fmt(stats["peak"], metric)),
            _stat_card("Trough", _fmt(stats["trough"], metric)),
        ], className="stat-card-grid"),
        _section_header("Trend Comparison"),
        _stat_card("vs 12-Month Avg", _fmt(stats["avg_12m"], metric),
                   _trend_badge(stats["current"], stats["avg_12m"])),
        _stat_card("vs 5-Year Avg", _fmt(stats["avg_5y"], metric),
                   _trend_badge(stats["current"], stats["avg_5y"])),
    ]

    if benchmark:
        _, bv = _get_timeseries(df, portfolios, benchmark, metric, agg)
        bstats = _compute_stats(bv)
        if bstats:
            children.extend([
                _section_header(f"Benchmark: {benchmark}", "var(--accent-400)"),
                html.Div([
                    _stat_card("Current", _fmt(bstats["current"], metric)),
                    _stat_card("Average", _fmt(bstats["average"], metric)),
                ], className="stat-card-grid"),
                html.Div([
                    _stat_card("Peak", _fmt(bstats["peak"], metric)),
                    _stat_card("Trough", _fmt(bstats["trough"], metric)),
                ], className="stat-card-grid"),
                _stat_card("vs 12-Month Avg", _fmt(bstats["avg_12m"], metric),
                           _trend_badge(bstats["current"], bstats["avg_12m"])),
                _stat_card("vs 5-Year Avg", _fmt(bstats["avg_5y"], metric),
                           _trend_badge(bstats["current"], bstats["avg_5y"])),
            ])

    return html.Div(children, className="stat-panel")
