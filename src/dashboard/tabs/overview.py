"""
Overview tab — Ledger editorial landing page (IRIS Redesign v2).

KPI figures · total-exposure line (2/3) · Market pulse digest (1/3) linking to
the Market Insight tab · footer rule. Pure presentation over existing data:
facilities via TabContext, market via data.market.get_snapshot().
"""

from __future__ import annotations

from datetime import datetime

import plotly.graph_objects as go
import polars as pl
from dash import dcc, html

from .registry import BaseTab, TabContext, register_tab
from ..data import market
from ..data.market import history as mkt_history
from ..utils.helpers import plotly_theme, empty_figure

_PRIMARY = "#9d3a4a"  # Ledger oxblood mid-tone (reads on both themes)

_VERDICT_COLOR = {
    "observation": "var(--green-500)",
    "caution": "var(--amber-500)",
    "alert": "var(--red-500)",
    "systemic_top": "#b91c1c",
}

_STATUS_RANK = {"red": 0, "yellow": 1, "green": 2}


class OverviewTab(BaseTab):
    id = "overview"
    label = "Overview"
    order = 5  # first tab — the landing page
    nav_group = "Home"
    tier = "gold"
    tier_tooltip = "Editorial landing — portfolio + market digest"

    def render(self, ctx: TabContext):
        from .portfolio_summary import _apply_filters, _compute_kpis, _kpi_strip

        if ctx.selected_portfolio in ctx.portfolios:
            pf = _apply_filters(ctx.facilities_df, ctx.portfolios[ctx.selected_portfolio])
        else:
            pf = ctx.facilities_df

        kpis = _compute_kpis(pf)
        fig = _exposure_line(pf)
        snap = market.get_snapshot()

        meta = _window_meta(pf)
        return html.Div([
            _kpi_strip(kpis),

            html.Div([
                # 2/3 — total exposure line
                html.Div([
                    html.Div([
                        html.H3(f"Total exposure, {(ctx.selected_portfolio or 'portfolio').lower()}"),
                        html.Span(meta, className="card-head-meta"),
                    ], className="card-head"),
                    html.Div(dcc.Graph(figure=fig, config={"displayModeBar": False},
                                       style={"height": "300px"}),
                             className="card-body pad-tight"),
                ], className="card"),

                # 1/3 — Market pulse digest
                html.Div(_market_pulse(snap), className="ov-pulse"),
            ], className="ov-grid"),

            # Footer rule
            html.Div([
                html.Span(
                    f"Issue #{snap.get('issue_number', 1)} · generated {snap.get('as_of_date', '')}"
                    f" · data through {_last_period(pf)}"),
                html.Span("Confidential — internal use"),
            ], className="ov-foot"),
        ], className="ov-wrap")


register_tab(OverviewTab())


# ── helpers ──────────────────────────────────────────────────────────────────

def _fmt_month(d) -> str:
    try:
        return datetime.fromisoformat(str(d)[:10]).strftime("%b '%y")
    except Exception:  # noqa: BLE001
        return str(d)[:7]


def _window_meta(df: pl.DataFrame) -> str:
    if df is None or df.is_empty() or "reporting_date" not in df.columns:
        return ""
    dates = df["reporting_date"].unique().sort().to_list()
    if not dates:
        return ""
    return f"{_fmt_month(dates[0])} – {_fmt_month(dates[-1])} · $"


def _last_period(df: pl.DataFrame) -> str:
    if df is None or df.is_empty() or "reporting_date" not in df.columns:
        return "—"
    dates = df["reporting_date"].unique().sort().to_list()
    return _fmt_month(dates[-1]) if dates else "—"


def _exposure_line(df: pl.DataFrame) -> go.Figure:
    """Single Ledger-accent line of total balance per reporting period."""
    if df is None or df.is_empty() or "reporting_date" not in df.columns:
        return empty_figure("No data in the selected window")
    agg = (df.group_by("reporting_date")
             .agg(pl.col("balance").sum().alias("total"))
             .sort("reporting_date"))
    xs = [_fmt_month(d) for d in agg["reporting_date"].to_list()]
    ys = agg["total"].to_list()
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color=_PRIMARY, width=1.75),
        marker=dict(size=4, color=_PRIMARY),
        hovertemplate="%{x} · $%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(**plotly_theme(showlegend=False))
    return fig


def _market_pulse(snap: dict) -> list:
    roll_color = _VERDICT_COLOR.get(snap.get("verdict"), "var(--amber-500)")
    indicators = snap.get("indicators", [])
    pulse = sorted(indicators, key=lambda i: _STATUS_RANK.get(i.get("status"), 3))[:5]
    spark = mkt_history.composite_history()

    rows = []
    for i, ind in enumerate(pulse):
        rows.append(html.Div([
            html.Span(ind.get("status", ""), className=f"mkt-status-pill {ind.get('status', 'green')}"),
            html.Span(ind.get("name", ""), className="ov-pulse-name"),
            html.Span(str(ind.get("value_display", "—")).split(" ")[0],
                      className="ov-pulse-val"),
        ], className="ov-pulse-row" + (" first" if i == 0 else "")))

    return [
        html.Div([
            html.H3("Market pulse"),
            html.Span(f"Issue #{snap.get('issue_number', 1)}", className="card-head-meta"),
        ], className="card-head", style={"borderTop": "none", "paddingTop": "0"}),
        html.Div([
            html.Span(f"{snap.get('weighted_risk_score', 0):.1f}",
                      className="ov-pulse-score", style={"color": roll_color}),
            html.Span(["composite · ",
                       html.Span(snap.get("verdict_label", ""),
                                 style={"color": roll_color, "fontWeight": "600"})],
                      className="ov-pulse-verdict"),
        ], style={"display": "flex", "alignItems": "baseline", "gap": "12px",
                  "flexWrap": "wrap"}),
        html.Div(_spark_svg(spark), className="ov-pulse-spark"),
        html.Div(rows, className="ov-pulse-list"),
        html.Button(f"Full monitor → {len(indicators)} indicators",
                    className="ov-market-link", n_clicks=0,
                    **{"data-target-tab": "tab-market-insight"}),
    ]


def _spark_svg(points: list[float]) -> html.Img | html.Span:
    """Amber composite sparkline as an inline SVG image."""
    pts = [p for p in (points or []) if p is not None]
    if len(pts) < 2:
        return html.Span()
    w, h, pad = 250, 48, 3
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1
    n = len(pts)
    xs = [pad + i * (w - 2 * pad) / (n - 1) for i in range(n)]
    ys = [h - pad - ((p - lo) * (h - 2 * pad) / rng) for p in pts]
    line = " ".join(f"{'M' if i == 0 else 'L'}{xs[i]:.1f},{ys[i]:.1f}" for i in range(n))
    c = "%23b08415"  # ledger amber mid
    svg = (
        f"%3Csvg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}'%3E"
        f"%3Cpath d='{line}' fill='none' stroke='{c}' stroke-width='1.25'/%3E"
        f"%3C/svg%3E"
    )
    return html.Img(src="data:image/svg+xml," + svg, width=w, height=h,
                    style={"display": "block"})
