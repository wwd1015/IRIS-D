"""
Market Insight tab — broad-market overheat monitor (mirrors Kestrel's Market view).

A categorized grid of market-risk indicators, each fetched live from public web
sources (FRED / Yahoo / scrapes — ported from Kestrel into
``data/market/``), flagged red / yellow / green against a threshold.

Render is instant (seeded snapshot); the "Refresh" button runs the live web
fetch on demand.
"""

from __future__ import annotations

import json
from datetime import datetime

from dash import Input, Output, callback, dcc, html, no_update

from .registry import BaseTab, TabContext, register_tab
from ..data import market
from ..data.market import history


_VERDICT_COLOR = {
    "observation": "var(--green-500)",
    "caution": "var(--amber-500)",
    "alert": "var(--red-500)",
    "systemic_top": "#b91c1c",
}

# Status → solid accent used for the back-face current value + band fills.
_BAND_FILL = {"red": "var(--red-500)", "yellow": "var(--amber-500)", "green": "var(--green-500)"}


def _icon(name: str, size: int = 12) -> html.Span:
    return html.Span(className=f"ic ic-{name}",
                     style={"width": f"{size}px", "height": f"{size}px"})


class MarketInsightTab(BaseTab):
    id = "market-insight"
    label = "Market Insight"
    order = 30
    nav_group = "Risk"
    tier = "gold"
    tier_tooltip = "Live macro / market-risk monitor"

    # ── Overview digest contribution (market risk pulse) ──
    def overview_summary(self, ctx: TabContext):
        from ..utils.helpers import sparkline_svg
        snap = market.get_snapshot()
        inds = snap.get("indicators", [])
        if not inds:
            return None
        verdict_color = _VERDICT_COLOR.get(snap.get("verdict"), "var(--amber-500)")
        rank = {"red": 0, "yellow": 1, "green": 2}
        top = sorted(inds, key=lambda i: rank.get(i.get("status"), 3))[:4]
        spark = history.composite_history()

        rows = [html.Div([
            html.Span(i.get("status", ""), className=f"mkt-status-pill {i.get('status', 'green')}"),
            html.Span(i.get("name", ""), className="ov-pulse-name"),
            html.Span(str(i.get("value_display", "—")).split(" ")[0], className="ov-pulse-val"),
        ], className="ov-pulse-row" + (" first" if k == 0 else "")) for k, i in enumerate(top)]

        body = html.Div([
            html.Div([
                html.Span(f"{snap.get('weighted_risk_score', 0):.1f}",
                          className="ov-pulse-score", style={"color": verdict_color}),
                html.Span(["composite · ",
                           html.Span(snap.get("verdict_label", ""),
                                     style={"color": verdict_color, "fontWeight": "600"})],
                          className="ov-pulse-verdict"),
            ], style={"display": "flex", "alignItems": "baseline", "gap": "10px", "flexWrap": "wrap"}),
            html.Div(sparkline_svg(spark, color="#b08415", h=40, fill=False),
                     className="ov-pulse-spark"),
            html.Div(rows, className="ov-pulse-list"),
        ])
        return {"title": "Market risk", "body": body, "span": 1,
                "link_label": "Full monitor", "order": 30}

    def render(self, ctx: TabContext):
        snap = market.get_snapshot()
        return html.Div([
            _toolbar(snap),
            dcc.Loading(
                html.Div(_grid(snap), id="mkt-grid"),
                type="default", color="var(--primary-500)",
            ),
        ], className="mkt-wrap")

    def register_callbacks(self, app):
        @callback(
            Output("mkt-grid", "children"),
            Output("mkt-meta", "children"),
            Input("mkt-refresh", "n_clicks"),
            prevent_initial_call=True,
        )
        def do_refresh(n):
            if not n:
                return no_update, no_update
            snap = market.refresh()
            return _grid(snap), _meta_text(snap)


register_tab(MarketInsightTab())


# ── helpers ──────────────────────────────────────────────────────────────────

def _fmt_time(iso: str) -> str:
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return d.strftime("%b %-d, %-I:%M %p")
    except Exception:
        return str(iso)[:16].replace("T", " ")


def _meta_text(snap: dict) -> list:
    """Ledger rollup strip — serif composite score · R/Y/G counts · issue meta."""
    roll_color = _VERDICT_COLOR.get(snap.get("verdict"), "var(--text-primary)")
    total = (snap.get("red_count", 0) + snap.get("yellow_count", 0)
             + snap.get("green_count", 0))
    return [
        html.Span([
            html.Span(f"{snap.get('weighted_risk_score', 0):.1f}",
                      className="mkt-roll-score", style={"color": roll_color}),
            html.Span(["composite risk · ",
                       html.Span(snap.get("verdict_label", ""),
                                 style={"color": roll_color, "fontWeight": "600"})],
                      className="mkt-roll-verdict"),
        ], style={"display": "inline-flex", "alignItems": "baseline", "gap": "10px"}),
        html.Span([
            html.Span(f"R {snap.get('red_count', 0)}",
                      style={"color": "var(--red-500)", "fontWeight": "700"}),
            " · ",
            html.Span(f"Y {snap.get('yellow_count', 0)}",
                      style={"color": "var(--amber-500)", "fontWeight": "700"}),
            " · ",
            html.Span(f"G {snap.get('green_count', 0)}",
                      style={"color": "var(--green-500)", "fontWeight": "700"}),
            f" of {total}",
        ], className="mkt-dist", style={"fontSize": "11px"}),
        html.Span(
            f"As of {snap.get('as_of_date', '')} · click any card for history",
            className="mkt-eyebrow", style={"textTransform": "none",
                                            "letterSpacing": "0.02em"},
        ),
    ]


def _toolbar(snap: dict) -> html.Div:
    return html.Div([
        html.Div(_meta_text(snap), id="mkt-meta",
                 style={"display": "flex", "alignItems": "baseline", "gap": "26px",
                        "flexWrap": "wrap"}),
        html.Button([html.Span(className="ic ic-refresh", style={"width": "13px", "height": "13px"}),
                     "Refresh"], id="mkt-refresh", n_clicks=0, className="mkt-btn"),
    ], className="mkt-rollup")


def _indicator_card(ind: dict) -> html.Div:
    """An indicator card that flips on click to reveal the metric's full history."""
    status = ind.get("status", "green")
    ind_id = ind.get("id", "")
    src_name = ind.get("source_name", "")
    src_url = ind.get("source_url")
    src = (html.A(src_name, href=src_url, target="_blank", rel="noopener noreferrer",
                  className="src-name")
           if src_url else html.Span(src_name, className="src-name"))
    tags = []
    if ind.get("stale"):
        tags.append(html.Span("STALE", className="mkt-tag-mini stale"))
    if ind.get("auto"):
        tags.append(html.Span("AUTO", className="mkt-tag-mini auto"))

    hist = history.build_hist(ind_id)

    # ── Front face ──
    front_children = [
        html.Div([
            html.Div(ind.get("name", ""), className="mkt-ind-name"),
            html.Span(status, className=f"mkt-status-pill {status}"),
        ], className="mkt-ind-head"),
        html.Div(ind.get("value_display", "—"), className="mkt-ind-value"),
    ]
    if ind.get("note"):
        front_children.append(html.Div(ind["note"], className="mkt-ind-note"))
    front_children.append(html.Div(ind.get("threshold_text", ""), className="mkt-ind-thr"))
    front_children.append(html.Div([
        html.Div([src, html.Span(f"· {_fmt_time(ind.get('last_updated', ''))}"), *tags],
                 className="mkt-ind-src"),
    ], className="mkt-ind-foot"))
    if hist:
        front_children.append(html.Span(["History ", _icon("chart", 11)], className="mkt-flip-hint"))

    front_attrs = {"role": "button", "tabIndex": 0} if hist else {}
    front = html.Div(front_children,
                     className="mkt-face mkt-front" + (" clickable" if hist else ""),
                     **front_attrs)

    if not hist:
        return html.Div(html.Div([front], className="mkt-flip"), className=f"mkt-ind {status}")

    # ── Back face (history chart, rendered client-side from data-hist) ──
    pts = hist["points"]
    cur_txt = history.format_value(hist["current"], hist["prefix"], hist["suffix"])
    payload = {
        "id": ind_id, "name": ind.get("name", ""), "status": status,
        "threshold": ind.get("threshold_text", ""), "source": src_name,
        "current": hist["current"], "prefix": hist["prefix"], "suffix": hist["suffix"],
        "points": pts, "bands": hist["bands"],
    }
    back = html.Div([
        html.Button(_icon("download", 12), className="mkt-dl", n_clicks=0,
                    title="Download full history (CSV)",
                    **{"aria-label": "Download history data as CSV"}),
        html.Div([
            html.Div(ind.get("name", ""), className="mkt-back-title"),
            html.Span(cur_txt, className="mkt-back-current",
                      style={"color": _BAND_FILL.get(status, "var(--text-primary)")}),
        ], className="mkt-back-head"),
        html.Div(f"{pts[0]['label']} – {pts[-1]['label']} · click to flip back",
                 className="mkt-back-sub"),
        html.Div(className="mkt-hist-wrap"),
        html.Span([_icon("arrow-left", 11), " Back"], className="mkt-flip-hint back"),
    ], className="mkt-face mkt-back", **{"data-hist": json.dumps(payload, separators=(",", ":"))})

    return html.Div(html.Div([front, back], className="mkt-flip"), className=f"mkt-ind {status}")


def _grid(snap: dict) -> list:
    order = snap.get("category_order") or market.CATEGORY_ORDER
    labels = snap.get("category_label") or market.CATEGORY_LABEL
    grouped: dict[str, list] = {c: [] for c in order}
    for ind in snap.get("indicators", []):
        grouped.setdefault(ind.get("category"), []).append(ind)

    sections = []
    for cat in order:
        inds = grouped.get(cat) or []
        if not inds:
            continue
        sections.append(html.Div([
            html.Div([
                html.Span(labels.get(cat, cat), className="mkt-cat-label"),
                html.Span(className="mkt-cat-rule"),
                html.Span(f"{len(inds)} indicators", className="mkt-cat-count"),
            ], className="mkt-cat-head"),
            html.Div([_indicator_card(i) for i in inds], className="mkt-ind-grid"),
        ], className="mkt-cat"))
    return sections
