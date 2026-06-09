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
    tier = "gold"
    tier_tooltip = "Live macro / market-risk monitor"

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
    roll_color = _VERDICT_COLOR.get(snap.get("verdict"), "var(--text-primary)")
    return [
        html.Span(f"Issue #{snap.get('issue_number', 1)} · as of {snap.get('as_of_date', '')}",
                  className="mkt-eyebrow"),
        html.Span(snap.get("verdict_label", ""), className="mkt-pill",
                  style={"color": roll_color, "background": "color-mix(in srgb, "
                         + roll_color + " 14%, transparent)"}),
        html.Span([
            html.Span(f"R {snap.get('red_count', 0)}", style={"color": "var(--red-500)"}),
            " · ",
            html.Span(f"Y {snap.get('yellow_count', 0)}", style={"color": "var(--amber-500)"}),
            " · ",
            html.Span(f"G {snap.get('green_count', 0)}", style={"color": "var(--green-500)"}),
            html.Span(f"  ·  risk {snap.get('weighted_risk_score', 0):.0f}",
                      style={"color": "var(--text-muted)"}),
        ], className="mkt-dist", style={"fontSize": "var(--fs-xs)"}),
    ]


def _toolbar(snap: dict) -> html.Div:
    return html.Div([
        html.Div(_meta_text(snap), id="mkt-meta",
                 style={"display": "flex", "alignItems": "center", "gap": "12px", "flexWrap": "wrap"}),
        html.Button([html.Span(className="ic ic-refresh", style={"width": "13px", "height": "13px"}),
                     "Refresh"], id="mkt-refresh", n_clicks=0, className="mkt-btn"),
    ], className="section-head", style={"justifyContent": "space-between"})


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
        html.Div(f"Full history · {pts[0]['label']} – {pts[-1]['label']}", className="mkt-back-sub"),
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
