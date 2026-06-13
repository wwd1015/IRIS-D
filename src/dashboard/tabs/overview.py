"""
Overview tab — Ledger editorial landing page (IRIS Redesign v2).

A digest of the whole dashboard: cross-cutting KPI figures, then a grid of
summary panels contributed by every other tab via ``BaseTab.overview_summary``.
New tabs appear here automatically just by implementing that method — the
Overview tab never needs editing to add a panel.
"""

from __future__ import annotations

from dash import html

from .registry import BaseTab, TabContext, register_tab, get_all_tabs


class OverviewTab(BaseTab):
    id = "overview"
    label = "Overview"
    order = 5  # first tab — the landing page
    nav_group = "Home"
    tier = "gold"
    tier_tooltip = "Editorial landing — cross-tab digest"

    def render(self, ctx: TabContext):
        from .portfolio_summary import _apply_filters, _compute_kpis, _kpi_strip
        from ..auth import user_management

        if ctx.selected_portfolio in ctx.portfolios:
            pf = _apply_filters(ctx.facilities_df, ctx.portfolios[ctx.selected_portfolio])
        else:
            pf = ctx.facilities_df

        kpis = _compute_kpis(pf)

        # Collect digest panels from every accessible tab (extensible — any tab
        # that implements overview_summary() shows up here).
        role = user_management.get_current_user_role()
        panels = []
        for tab in get_all_tabs():
            if tab.id == self.id:
                continue
            if tab.required_roles and role not in tab.required_roles:
                continue
            try:
                summ = tab.overview_summary(ctx)
            except Exception:  # noqa: BLE001 — a broken panel must not blank the page
                summ = None
            if not summ:
                continue
            summ["_tab"] = tab
            summ.setdefault("order", getattr(tab, "order", 100))
            panels.append(summ)
        panels.sort(key=lambda s: s["order"])

        children = [_kpi_strip(kpis)] if kpis else []
        if panels:
            children.append(html.Div([_panel(s) for s in panels], className="ov-summary-grid"))
        else:
            children.append(html.Div("No summaries available for the current selection.",
                                     className="ov-empty"))

        children.append(html.Div([
            html.Span(f"Portfolio: {ctx.selected_portfolio or '—'} · {_window_meta(pf)}"),
            html.Span("Confidential — internal use"),
        ], className="ov-foot"))

        return html.Div(children, className="ov-wrap")


register_tab(OverviewTab())


# ── panel + helpers ──────────────────────────────────────────────────────────

def _panel(summ: dict) -> html.Div:
    tab = summ["_tab"]
    link_label = summ.get("link_label", "View")
    span = summ.get("span", 1)
    return html.Div([
        html.Div([
            html.H3(summ.get("title", tab.label)),
            html.Button([link_label, html.Span(" →", className="ov-card-arrow")],
                        className="ov-card-link", n_clicks=0,
                        **{"data-target-tab": f"tab-{tab.id}"}),
        ], className="card-head"),
        html.Div(summ.get("body"), className="ov-card-body"),
    ], className="ov-card", style={"gridColumn": f"span {span}"})


def _window_meta(df) -> str:
    import polars as pl  # local — keep import cost off the hot path
    from datetime import datetime
    if df is None or df.is_empty() or "reporting_date" not in df.columns:
        return ""
    dates = df["reporting_date"].unique().sort().to_list()
    if not dates:
        return ""

    def fmt(d):
        try:
            return datetime.fromisoformat(str(d)[:10]).strftime("%b '%y")
        except Exception:  # noqa: BLE001
            return str(d)[:7]

    return f"{fmt(dates[0])} – {fmt(dates[-1])}"
