"""
Financial Trends tab — borrower credit fundamentals vs. covenants.

For a lending book, "financial trends" track the BORROWERS' financial health
(early-warning credit signals) measured against covenant thresholds — not the
bank's own P&L. Each metric is monitored over time with a covenant line, a
shaded breach zone, a prior-year ghost, and a per-segment breach table.

Real columns used (from ``data/models.py``):
  CRE:  dscr, ltv                          (covenant monitoring)
  CB :  cash_flow_leverage, fixed_charge_coverage, liquidity, profitability, growth
"""

from __future__ import annotations

import plotly.graph_objs as go
import polars as pl
from dash import callback, dcc, html, Input, Output, no_update

from .registry import BaseTab, TabContext, register_tab
from ..utils.helpers import (
    plotly_theme, empty_figure, add_period_column, format_period,
)


# ── Metric configuration ────────────────────────────────────────────────────
# dir:  "high" = higher is healthier · "low" = lower is healthier
# fmt:  "ratio" → 1.80x · "pct100" → 56.8% (value already in %) · "pct1" → 15.0% (decimal)
# dim:  column to break the details table down by
FIN_METRICS: dict[str, dict] = {
    "dscr":                  {"label": "Debt Service Coverage", "short": "DSCR",      "fmt": "ratio",  "dir": "high", "covenant": 1.25, "dim": "cre_property_type"},
    "ltv":                   {"label": "Loan to Value",         "short": "LTV",       "fmt": "pct100", "dir": "low",  "covenant": 80.0, "dim": "cre_property_type"},
    "cash_flow_leverage":    {"label": "Cash Flow Leverage",    "short": "Leverage",  "fmt": "ratio",  "dir": "low",  "covenant": 5.0,  "dim": "industry"},
    "fixed_charge_coverage": {"label": "Fixed Charge Coverage", "short": "FCCR",      "fmt": "ratio",  "dir": "high", "covenant": 1.5,  "dim": "industry"},
    "liquidity":             {"label": "Liquidity Ratio",       "short": "Liquidity", "fmt": "ratio",  "dir": "high", "covenant": 1.0,  "dim": "industry"},
    "profitability":         {"label": "Profitability",         "short": "Profit.",   "fmt": "pct1",   "dir": "high", "covenant": 0.05, "dim": "industry"},
    "growth":                {"label": "Revenue Growth",        "short": "Growth",    "fmt": "pct1",   "dir": "high", "covenant": 0.0,  "dim": "industry"},
}
HEADLINE = ["dscr", "cash_flow_leverage", "liquidity"]
PRIMARY = "#4B6BFB"


class FinancialTrendTab(BaseTab):
    id = "financial-trend"
    label = "Financial Trend"
    order = 40
    tier = "silver"
    tier_tooltip = "Borrower credit fundamentals vs. covenants"

    # ── Full custom layout (KPI strip · trend + covenant · per-segment table) ──
    def render(self, ctx: TabContext):
        if ctx.selected_portfolio in ctx.portfolios:
            pf = _filter(ctx.facilities_df, ctx.portfolios[ctx.selected_portfolio])
        else:
            pf = ctx.facilities_df

        metric = _default_metric(pf)
        m = FIN_METRICS[metric]

        return html.Div([
            _headline_strip(pf),

            html.Div([
                html.Div([
                    # Status icon — matches the Portfolio Summary control row.
                    html.Span(className=f"tier-dot tier-badge--{self.tier}",
                              title=self.tier_tooltip or f"{self.tier.capitalize()} tier"),
                    html.Div([
                        dcc.RadioItems(
                            id="ft-metric",
                            options=[{"label": v["short"], "value": k} for k, v in FIN_METRICS.items()],
                            value=metric, className="chip-radio", inline=True,
                        ),
                        dcc.RadioItems(
                            id="ft-freq",
                            options=[{"label": "Monthly", "value": "monthly"},
                                     {"label": "Quarterly", "value": "quarterly"}],
                            value="monthly", className="chip-radio", inline=True,
                        ),
                    ], className="gc-group", style={"gap": "12px", "flexWrap": "wrap",
                                                    "justifyContent": "flex-end"}),
                ], className="section-head", style={"flexWrap": "wrap", "gap": "12px",
                                                    "justifyContent": "space-between"}),

                html.Div([
                    html.Div([
                        html.H3([
                            html.Span(m["label"], id="ft-chart-title"),
                            html.Span(" · portfolio-weighted · borrower-reported",
                                      style={"color": "var(--text-muted)", "fontWeight": "400",
                                             "fontSize": "var(--fs-xs)"}),
                        ]),
                        html.Div([
                            html.Span([html.Span(className="legend-swatch",
                                                 style={"background": PRIMARY}), "Latest"], className="legend-item"),
                            html.Span([html.Span(className="legend-swatch",
                                                 style={"background": "var(--text-muted)"}), "Prior yr"], className="legend-item"),
                            html.Span([html.Span(className="legend-swatch",
                                                 style={"background": "var(--red-500)"}), "Covenant"], className="legend-item"),
                        ], className="legend"),
                    ], className="card-head"),
                    html.Div(dcc.Graph(id="ft-trend-chart",
                                       figure=_build_chart(pf, metric, "monthly"),
                                       config={"displayModeBar": False}, style={"height": "340px"}),
                             className="card-body pad-tight"),
                    html.Div(_compare_strip(pf, metric, "monthly"), id="ft-compare"),
                ], className="card"),
            ], className="section"),

            html.Div([
                html.Div([
                    html.Div("Borrower fundamentals by segment", className="section-title"),
                    html.Span(id="ft-table-sub", className="section-sub",
                              children=_table_sub(pf, metric, "monthly")),
                ], className="section-head"),
                html.Div(html.Div(_lob_table(pf, metric, "monthly"), className="drill-table-wrap"),
                         className="card", id="ft-table"),
            ], className="section"),
        ])

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            [Output("ft-trend-chart", "figure"),
             Output("ft-compare", "children"),
             Output("ft-table", "children"),
             Output("ft-table-sub", "children"),
             Output("ft-chart-title", "children")],
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data"),
             Input("ft-metric", "value"),
             Input("ft-freq", "value")],
            prevent_initial_call=True,
        )
        def update(portfolio, _tw, metric, freq):
            if not portfolio or portfolio not in app_state.portfolios:
                return no_update, no_update, no_update, no_update, no_update
            metric = metric or "dscr"
            freq = freq or "monthly"
            windowed = app_state._apply_time_window(app_state.facilities_df)
            pf = _filter(windowed, app_state.portfolios[portfolio])
            return (
                _build_chart(pf, metric, freq),
                _compare_strip(pf, metric, freq),
                html.Div(_lob_table(pf, metric, freq), className="drill-table-wrap"),
                _table_sub(pf, metric, freq),
                FIN_METRICS[metric]["label"],
            )


register_tab(FinancialTrendTab())


# ── Formatting ──────────────────────────────────────────────────────────────

def _fmt(v, fmt: str) -> str:
    if v is None:
        return "—"
    if fmt == "ratio":
        return f"{v:.2f}x"
    if fmt == "pct100":
        return f"{v:.1f}%"
    if fmt == "pct1":
        return f"{v * 100:.1f}%"
    return f"{v:.2f}"


def _fmt_delta(v, fmt: str) -> str:
    if v is None:
        return "—"
    sign = "+" if v >= 0 else "−"
    if fmt == "ratio":
        return f"{sign}{abs(v):.2f}x"
    if fmt == "pct100":
        return f"{sign}{abs(v):.1f}%"
    if fmt == "pct1":
        return f"{sign}{abs(v) * 100:.1f}%"
    return f"{sign}{abs(v):.2f}"


def _breached(v, covenant, direction) -> bool:
    if v is None:
        return False
    return v < covenant if direction == "high" else v > covenant


# ── Data helpers ────────────────────────────────────────────────────────────

def _filter(df, criteria):
    from ..data.dataset import Dataset
    return Dataset.apply_criteria(df, criteria)


def _default_metric(df) -> str:
    """First metric (in config order) that has data in this portfolio."""
    for k in FIN_METRICS:
        if not df.is_empty() and k in df.columns and df[k].drop_nulls().len() > 0:
            return k
    return "dscr"


def _period_series(df, col, freq):
    """Return (labels, values) of the portfolio-mean metric per period."""
    if df.is_empty() or col not in df.columns:
        return [], []
    sub = df.filter(pl.col(col).is_not_null())
    if sub.is_empty():
        return [], []
    sub = add_period_column(sub, freq)
    agg = sub.group_by("_period").agg(pl.col(col).mean().alias("v")).sort("_period")
    periods = agg["_period"].to_list()
    labels = [format_period(p, freq) for p in periods]
    return labels, agg["v"].to_list()


# ── Chart ───────────────────────────────────────────────────────────────────

def _build_chart(df, metric, freq):
    m = FIN_METRICS[metric]
    labels, vals = _period_series(df, metric, freq)
    if not vals:
        return empty_figure("No covenant data for this segment", 340)

    cov = m["covenant"]
    direction = m["dir"]

    # Prior-year ghost: shift by a year's worth of periods
    shift = 4 if freq == "quarterly" else 12
    prior = [None] * len(vals)
    for i in range(len(vals)):
        if i - shift >= 0:
            prior[i] = vals[i - shift]

    all_v = [v for v in vals if v is not None] + [cov] + [v for v in prior if v is not None]
    pad = (max(all_v) - min(all_v)) * 0.18 or 1
    ymax, ymin = max(all_v) + pad, min(all_v) - pad

    fig = go.Figure()

    # Breach zone (beyond covenant in the unhealthy direction)
    if direction == "high":
        fig.add_hrect(y0=ymin, y1=cov, fillcolor="rgba(239,68,68,0.05)", line_width=0, layer="below")
    else:
        fig.add_hrect(y0=cov, y1=ymax, fillcolor="rgba(239,68,68,0.05)", line_width=0, layer="below")

    # Prior-year ghost
    if any(p is not None for p in prior):
        fig.add_trace(go.Scatter(
            x=labels, y=prior, mode="lines",
            line=dict(color="#9aa1ad", width=1.5, dash="dot"),
            name="Prior yr", hoverinfo="skip", connectgaps=False,
        ))

    # Actual — area + line, breached points in red
    fig.add_trace(go.Scatter(
        x=labels, y=vals, mode="lines", fill="tozeroy",
        line=dict(color=PRIMARY, width=2.5),
        fillcolor="rgba(75,107,251,0.12)", name="Latest",
    ))
    marker_colors = ["#ef4444" if _breached(v, cov, direction) else PRIMARY for v in vals]
    fig.add_trace(go.Scatter(
        x=labels, y=vals, mode="markers",
        marker=dict(color=marker_colors, size=6),
        name="", hoverinfo="y", showlegend=False,
    ))

    # Covenant threshold line
    fig.add_hline(y=cov, line=dict(color="#ef4444", width=1.6, dash="dash"),
                  annotation_text=f"covenant {_fmt(cov, m['fmt'])}",
                  annotation_position="top right",
                  annotation_font=dict(color="#ef4444", size=10))

    fig.update_layout(**plotly_theme(height=340, showlegend=False))
    fig.update_yaxes(range=[ymin, ymax])
    fig.update_xaxes(tickangle=-45 if len(labels) > 12 else 0)
    return fig


# ── Comparison strip ────────────────────────────────────────────────────────

def _compare_strip(df, metric, freq):
    m = FIN_METRICS[metric]
    _, vals = _period_series(df, metric, freq)
    if not vals:
        return []
    cur = vals[-1]
    prev = vals[-2] if len(vals) > 1 else cur
    delta = cur - prev
    improving = (delta > 0) if m["dir"] == "high" else (delta < 0)
    headroom = (cur - m["covenant"]) if m["dir"] == "high" else (m["covenant"] - cur)

    cells = [
        ("Latest", _fmt(cur, m["fmt"]), freq.capitalize(), None),
        ("vs Prior", _fmt_delta(delta, m["fmt"]),
         "improving" if improving else "deteriorating", "up" if improving else "down"),
        ("Covenant", _fmt(m["covenant"], m["fmt"]), "threshold", None),
        ("Headroom", _fmt_delta(headroom, m["fmt"]),
         "above covenant" if headroom >= 0 else "in breach", "up" if headroom >= 0 else "down"),
    ]
    return [html.Div([
        html.Div([
            html.Div(lbl, style={"fontSize": "10px", "color": "var(--text-muted)",
                                 "textTransform": "uppercase", "letterSpacing": "0.06em",
                                 "fontWeight": "600", "marginBottom": "4px"}),
            html.Div(val, className="mono tabular",
                     style={"fontSize": "var(--fs-lg)", "fontWeight": "700",
                            "color": "var(--green-500)" if tone == "up" else
                                     "var(--red-500)" if tone == "down" else "var(--text-primary)"}),
            html.Div(sub, style={"fontSize": "10px", "color": "var(--text-muted)",
                                 "fontFamily": "var(--font-mono)", "marginTop": "2px"}),
        ], style={"padding": "12px 16px",
                  "borderRight": "1px solid var(--border-hair)" if i < 3 else "none"})
        for i, (lbl, val, sub, tone) in enumerate(cells)
    ], style={"display": "grid", "gridTemplateColumns": "repeat(4, 1fr)",
              "borderTop": "1px solid var(--border-hair)"})]


# ── Per-segment details table ───────────────────────────────────────────────

def _table_sub(df, metric, freq):
    m = FIN_METRICS[metric]
    labels, _ = _period_series(df, metric, freq)
    if len(labels) >= 2:
        return f"{labels[-1]} vs {labels[-2]} · {m['label']}"
    return m["label"]


_SEG_COLORS = ["#6B8AFF", "#A78BFA", "#34D399", "#F59E0B", "#FB7185", "#60A5FA", "#0D9488", "#7C3AED"]


def _lob_table(df, metric, freq):
    m = FIN_METRICS[metric]
    dim = m["dim"]
    cov, direction, fmt = m["covenant"], m["dir"], m["fmt"]

    head = html.Thead(html.Tr([
        html.Th(dim.replace("cre_property_type", "Property type").replace("_", " ").title()),
        html.Th("Facilities", className="r"),
        html.Th("Latest", className="r"),
        html.Th("Prior", className="r"),
        html.Th("Δ", className="r"),
        html.Th("Covenant", className="r"),
        html.Th("Headroom", className="r"),
        html.Th("In breach", className="r"),
    ]))

    if df.is_empty() or metric not in df.columns or dim not in df.columns:
        return html.Table([head, html.Tbody(html.Tr(html.Td(
            "No data for this metric in the selected portfolio.",
            colSpan=8, style={"color": "var(--text-muted)", "padding": "16px"})))],
            className="drill-table")

    sub = df.filter(pl.col(metric).is_not_null() & pl.col(dim).is_not_null())
    if sub.is_empty():
        return html.Table([head, html.Tbody(html.Tr(html.Td(
            "No data for this metric in the selected portfolio.",
            colSpan=8, style={"color": "var(--text-muted)", "padding": "16px"})))],
            className="drill-table")

    sub = add_period_column(sub, freq)
    periods = sub["_period"].unique().sort().to_list()
    curr_p = periods[-1]
    prev_p = periods[-2] if len(periods) > 1 else periods[-1]

    # Top segments by facility count at the latest period
    groups = (sub.filter(pl.col("_period") == curr_p)
                 .group_by(dim).agg(pl.col("facility_id").n_unique().alias("n"))
                 .sort("n", descending=True).head(8))[dim].to_list()

    rows = []
    for i, g in enumerate(groups):
        gcur = sub.filter((pl.col("_period") == curr_p) & (pl.col(dim) == g))
        gprev = sub.filter((pl.col("_period") == prev_p) & (pl.col(dim) == g))
        a = gcur[metric].mean()
        p = gprev[metric].mean()
        if a is None:
            continue
        d = (a - p) if p is not None else None
        hr = (a - cov) if direction == "high" else (cov - a)
        n = gcur["facility_id"].n_unique()
        breach = gcur.filter(
            (pl.col(metric) < cov) if direction == "high" else (pl.col(metric) > cov)
        )["facility_id"].n_unique()
        imp = (d is not None and ((d > 0) if direction == "high" else (d < 0)))
        rows.append(html.Tr([
            html.Td(html.Span([
                html.Span(str(g)[:1].upper(), className="ticker-mark",
                          style={"background": _SEG_COLORS[i % len(_SEG_COLORS)]}),
                str(g),
            ], className="ticker")),
            html.Td(f"{n:,}", className="r mono", style={"color": "var(--text-muted)"}),
            html.Td(html.B(_fmt(a, fmt)), className="r mono"),
            html.Td(_fmt(p, fmt), className="r mono", style={"color": "var(--text-muted)"}),
            html.Td(html.Span(_fmt_delta(d, fmt),
                              className="chip-delta " + ("up" if imp else "down")), className="r"),
            html.Td(_fmt(cov, fmt), className="r mono", style={"color": "var(--text-muted)"}),
            html.Td(_fmt_delta(hr, fmt), className="r mono",
                    style={"color": "var(--green-500)" if hr >= 0 else "var(--red-500)", "fontWeight": "600"}),
            html.Td([
                html.Span(str(breach), className="mono",
                          style={"color": "var(--red-500)" if breach > 0 else "var(--text-secondary)", "fontWeight": "600"}),
                html.Span(f" / {n:,}", style={"color": "var(--text-muted)", "fontSize": "10px"}),
            ], className="r"),
        ]))

    # Total row
    tot_cur = sub.filter(pl.col("_period") == curr_p)
    tot_prev = sub.filter(pl.col("_period") == prev_p)
    a = tot_cur[metric].mean()
    p = tot_prev[metric].mean()
    d = (a - p) if (a is not None and p is not None) else None
    hr = ((a - cov) if direction == "high" else (cov - a)) if a is not None else None
    n = tot_cur["facility_id"].n_unique()
    breach = tot_cur.filter(
        (pl.col(metric) < cov) if direction == "high" else (pl.col(metric) > cov)
    )["facility_id"].n_unique()
    imp = (d is not None and ((d > 0) if direction == "high" else (d < 0)))
    rows.append(html.Tr([
        html.Td("Total portfolio", style={"fontWeight": "700"}),
        html.Td(f"{n:,}", className="r mono", style={"color": "var(--text-muted)", "fontWeight": "700"}),
        html.Td(html.B(_fmt(a, fmt)), className="r mono"),
        html.Td(_fmt(p, fmt), className="r mono", style={"color": "var(--text-muted)"}),
        html.Td(html.Span(_fmt_delta(d, fmt), className="chip-delta " + ("up" if imp else "down")), className="r"),
        html.Td(_fmt(cov, fmt), className="r mono", style={"color": "var(--text-muted)"}),
        html.Td(_fmt_delta(hr, fmt), className="r mono",
                style={"color": "var(--green-500)" if (hr or 0) >= 0 else "var(--red-500)", "fontWeight": "700"}),
        html.Td(html.Span(str(breach), className="mono", style={"color": "var(--red-500)", "fontWeight": "700"}), className="r"),
    ], style={"background": "var(--bg-surface)"}))

    return html.Table([head, html.Tbody(rows)], className="drill-table")


# ── Headline KPI strip ──────────────────────────────────────────────────────

def _headline_strip(df):
    cards = []
    for metric in HEADLINE:
        m = FIN_METRICS[metric]
        _, vals = _period_series(df, metric, "monthly")
        if not vals:
            cards.append(_kpi(m["label"], "—", None, True, []))
            continue
        cur = vals[-1]
        prev = vals[-2] if len(vals) > 1 else cur
        d = cur - prev if prev is not None else 0
        imp = (d > 0) if m["dir"] == "high" else (d < 0)
        hr = (cur - m["covenant"]) if m["dir"] == "high" else (m["covenant"] - cur)
        sub = (_fmt_delta(abs(hr) if hr is not None else 0, m["fmt"]).lstrip("+")
               + (" headroom" if hr >= 0 else " breach"))
        cards.append(_kpi(m["label"], _fmt(cur, m["fmt"]), imp, m["dir"] == "high",
                          vals[-12:], dp=(d / prev * 100 if prev else 0), sub=sub))

    cards.append(_breaches_card(df))
    return html.Div(cards, className="kpi-strip")


def _kpi(label, value, improving, higher_good, spark, dp=0.0, sub="vs prev period"):
    from .portfolio_summary import _spark_img
    if improving is None:
        delta_el = html.Span("—", className="kpi-subtext")
        color = PRIMARY
    else:
        cls = "up" if improving else "down"
        arrow = "↑" if dp >= 0 else "↓"
        delta_el = html.Span(f"{arrow} {abs(dp):.1f}%", className=f"kpi-delta {cls}")
        color = "#22c55e" if improving else "#ef4444"
    return html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
        html.Div([delta_el, html.Span(sub, className="kpi-subtext")], className="kpi-sub"),
        html.Div(_spark_img(spark, color), className="kpi-spark"),
    ], className="kpi rise")


def _breaches_card(df):
    total = 0
    if not df.is_empty() and "reporting_date" in df.columns:
        last = df["reporting_date"].max()
        cur = df.filter(pl.col("reporting_date") == last)
        ids: set = set()
        for metric, m in FIN_METRICS.items():
            if metric not in cur.columns:
                continue
            cov, direction = m["covenant"], m["dir"]
            breached = cur.filter(
                pl.col(metric).is_not_null() &
                ((pl.col(metric) < cov) if direction == "high" else (pl.col(metric) > cov))
            )
            ids |= set(breached["facility_id"].to_list())
        total = len(ids)
    return html.Div([
        html.Div("Covenant Breaches", className="kpi-label"),
        html.Div(str(total), className="kpi-value", style={"color": "var(--red-500)"}),
        html.Div([html.Span("facilities · all covenants", className="kpi-subtext")], className="kpi-sub"),
    ], className="kpi rise", style={"borderColor": "var(--red-bg)"})
