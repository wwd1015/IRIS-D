"""
Holdings tab – detailed facility-level data view with filters.

Shows a collapsible facility table with dynamic sidebar filters
(varying by LOB) and expandable time-series detail rows.
"""

from __future__ import annotations

import math

import pandas as pd
from dash import html, dcc, callback, Input, Output, State, no_update, ALL, callback_context

from ..tabs.registry import BaseTab, TabContext, register_tab
from ..utils.helpers import sidebar_wrapper, card_wrapper, dropdown_filter


# =============================================================================
# HoldingsTab  (Layer 3 — orchestration, sidebar, content, callbacks)
# =============================================================================


class HoldingsTab(BaseTab):
    id = "holdings"
    label = "Holdings"
    order = 20

    # ── Layer 3: Sidebar ────────────────────────────────────────────────────

    def render_sidebar(self, ctx: TabContext):
        portfolio_data = ctx.get_filtered_data(ctx.selected_portfolio)
        lob = ctx.portfolios.get(ctx.selected_portfolio, {}).get("lob", "")

        # ── Dynamic filters ─────────────────────────────────────────────────
        filters: list = []

        if len(portfolio_data) > 0:
            obligor_opts = sorted(portfolio_data["obligor_name"].unique())
            filters.append(dropdown_filter(
                id="holdings-obligor-filter",
                label="Obligor",
                options=[{"label": o, "value": o} for o in obligor_opts],
                multi=True,
                placeholder="All obligors…",
            ))

            rating_opts = sorted(portfolio_data["obligor_rating"].unique())
            filters.append(dropdown_filter(
                id="holdings-rating-filter",
                label="Rating",
                options=[{"label": str(r), "value": r} for r in rating_opts],
                multi=True,
                placeholder="All ratings…",
            ))

            # LOB-specific filters
            if lob == "Corporate Banking":
                industry_opts = sorted(portfolio_data["industry"].dropna().unique())
                filters.append(dropdown_filter(
                    id="holdings-industry-filter",
                    label="Industry",
                    options=[{"label": i, "value": i} for i in industry_opts],
                    multi=True,
                    placeholder="All industries…",
                ))
            elif lob == "CRE":
                prop_opts = sorted(portfolio_data["cre_property_type"].dropna().unique())
                filters.append(dropdown_filter(
                    id="holdings-property-filter",
                    label="Property Type",
                    options=[{"label": p, "value": p} for p in prop_opts],
                    multi=True,
                    placeholder="All property types…",
                ))
                msa_opts = sorted(portfolio_data["msa"].dropna().unique())
                filters.append(dropdown_filter(
                    id="holdings-msa-filter",
                    label="MSA",
                    options=[{"label": m, "value": m} for m in msa_opts],
                    multi=True,
                    placeholder="All MSAs…",
                ))

            # Balance range slider
            max_bal = portfolio_data["balance"].max()
            max_m = math.ceil(max_bal / 1_000_000) if max_bal > 0 else 1
            filters.append(html.Div([
                html.Label(
                    "Balance Range ($M)",
                    className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300",
                ),
                dcc.RangeSlider(
                    id="holdings-balance-filter",
                    min=0, max=max_m, value=[0, max_m], step=1,
                    tooltip={"placement": "bottom", "always_visible": True},
                    marks={0: "$0M", max_m: f"${max_m}M"},
                ),
            ], className="mb-3"))

        # Hidden inputs for LOB-specific filters that aren't rendered
        hidden_inputs = []
        if lob != "Corporate Banking":
            hidden_inputs.append(
                dcc.Dropdown(id="holdings-industry-filter", style={"display": "none"})
            )
        if lob != "CRE":
            hidden_inputs.append(
                dcc.Dropdown(id="holdings-property-filter", style={"display": "none"})
            )
            hidden_inputs.append(
                dcc.Dropdown(id="holdings-msa-filter", style={"display": "none"})
            )

        return sidebar_wrapper(
            title="Holdings",
            subtitle=f"Portfolio: {ctx.selected_portfolio}",
            children=filters + hidden_inputs,
        )

    # ── Layer 3: Content ────────────────────────────────────────────────────

    def render_content(self, ctx: TabContext):
        portfolio_data = ctx.get_filtered_data(ctx.selected_portfolio)
        n_facilities = len(portfolio_data["facility_id"].unique()) if len(portfolio_data) else 0

        return card_wrapper([
            html.Div([
                html.H3("Holdings", className="text-sm font-semibold text-ink-700 dark:text-slate-300"),
                html.Div(f"{n_facilities} facilities",
                         className="text-xs text-ink-500 dark:text-slate-400"),
            ], className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-ink-700"),
            html.Div(
                id="holdings-table-container",
                children=_create_holdings_table(portfolio_data),
            ),
        ])

    # ── Callbacks ──────────────────────────────────────────────────────────

    def register_callbacks(self, app):

        @callback(
            Output("holdings-table-container", "children"),
            [
                Input("universal-portfolio-dropdown", "value"),
                Input("holdings-obligor-filter", "value"),
                Input("holdings-rating-filter", "value"),
                Input("holdings-industry-filter", "value"),
                Input("holdings-property-filter", "value"),
                Input("holdings-msa-filter", "value"),
                Input("holdings-balance-filter", "value"),
            ],
            prevent_initial_call=True,
        )
        def update_holdings_table(
            selected_portfolio, obligor, rating, industry, prop_type, msa, balance
        ):
            from ..app import portfolios, latest_facilities, get_filtered_data as _gfd
            if not selected_portfolio:
                return no_update
            data = _gfd(selected_portfolio, portfolios, latest_facilities)
            return _create_holdings_table(
                data,
                rating_filter=rating,
                obligor_filter=obligor,
                industry_filter=industry,
                property_filter=prop_type,
                msa_filter=msa,
                balance_filter=balance,
            )

        @callback(
            Output({"type": "expanded-content", "index": ALL}, "children"),
            Output({"type": "expanded-content", "index": ALL}, "style"),
            Input({"type": "expand-btn", "index": ALL}, "n_clicks"),
            prevent_initial_call=True,
        )
        def toggle_expansion(n_clicks_list):
            from ..app import facilities_df, custom_metrics

            ctx = callback_context
            if not ctx.triggered:
                return no_update, no_update

            triggered_id = ctx.triggered[0]["prop_id"]
            children_out = [no_update] * len(n_clicks_list)
            styles_out = [no_update] * len(n_clicks_list)

            for i, n in enumerate(n_clicks_list):
                if n is None:
                    continue
                btn_id = ctx.inputs_list[0][i]["id"]
                prop_id_str = f'{{"index":"{btn_id["index"]}","type":"expand-btn"}}.n_clicks'
                if prop_id_str != triggered_id:
                    continue

                facility_id = btn_id["index"]
                if n % 2 == 1:
                    fac_row = facilities_df[facilities_df["facility_id"] == facility_id]
                    if len(fac_row) == 0:
                        continue
                    latest = fac_row.sort_values("reporting_date").iloc[-1]
                    children_out[i] = _create_time_series_table(
                        latest, facilities_df, custom_metrics
                    )
                    styles_out[i] = {"display": "block"}
                else:
                    children_out[i] = []
                    styles_out[i] = {"display": "none"}

            return children_out, styles_out


register_tab(HoldingsTab())


# =============================================================================
# Private rendering helpers
# =============================================================================


def _create_holdings_table(
    portfolio_data,
    rating_filter=None,
    obligor_filter=None,
    industry_filter=None,
    property_filter=None,
    msa_filter=None,
    balance_filter=None,
):
    """Build the collapsible facility table with optional filters."""
    if len(portfolio_data) == 0:
        return html.Div("No data available for this portfolio.", className="p-4")

    # ── Apply filters ───────────────────────────────────────────────────────
    if rating_filter:
        portfolio_data = portfolio_data[portfolio_data["obligor_rating"].isin(rating_filter)]
    if obligor_filter:
        portfolio_data = portfolio_data[portfolio_data["obligor_name"].isin(obligor_filter)]
    if industry_filter:
        portfolio_data = portfolio_data[portfolio_data["industry"].isin(industry_filter)]
    if property_filter:
        portfolio_data = portfolio_data[portfolio_data["cre_property_type"].isin(property_filter)]
    if msa_filter:
        portfolio_data = portfolio_data[portfolio_data["msa"].isin(msa_filter)]
    if balance_filter:
        lo, hi = balance_filter[0] * 1_000_000, balance_filter[1] * 1_000_000
        portfolio_data = portfolio_data[
            (portfolio_data["balance"] >= lo) & (portfolio_data["balance"] <= hi)
        ]

    if len(portfolio_data) == 0:
        return html.Div("No data matches the selected filters.", className="p-4")

    # ── Build table rows ────────────────────────────────────────────────────
    facilities = portfolio_data["facility_id"].unique()
    table_rows = []

    for fid in facilities:
        fac = portfolio_data[portfolio_data["facility_id"] == fid]
        latest = fac.sort_values("reporting_date").iloc[-1]

        main_row = html.Tr([
            html.Td([html.Button(
                "▼",
                id={"type": "expand-btn", "index": fid},
                className="expand-button",
                style={"border": "none", "background": "none", "cursor": "pointer"},
            )]),
            html.Td(fid),
            html.Td(latest["obligor_name"]),
            html.Td(latest["obligor_rating"]),
            html.Td(f"${latest['balance']:,.0f}"),
            html.Td(latest["origination_date"]),
            html.Td(latest["maturity_date"]),
        ], id={"type": "facility-row", "index": fid})

        expanded = html.Tr([html.Td(
            colSpan=7,
            children=[html.Div(
                id={"type": "expanded-content", "index": fid},
                style={"display": "none"},
            )],
        )])
        table_rows.extend([main_row, expanded])

    table = html.Table([
        html.Thead([html.Tr([
            html.Th(""), html.Th("Facility ID"), html.Th("Obligor Name"),
            html.Th("Rating"), html.Th("Balance"),
            html.Th("Origination"), html.Th("Maturity"),
        ])]),
        html.Tbody(table_rows),
    ], className="table holdings-table")

    return html.Div([
        html.Div([table], style={
            "overflowX": "auto", "width": "100%",
            "height": "calc(100vh - 250px)", "overflowY": "auto",
        })
    ], className="table-container")


def _create_time_series_table(facility_data, facilities_df, custom_metrics=None):
    """Build per-facility time-series table shown when a row is expanded."""
    facility_id = facility_data["facility_id"]
    fac_history = facilities_df[
        facilities_df["facility_id"] == facility_id
    ].sort_values("reporting_date")

    if len(fac_history) == 0:
        return html.Div("No historical data available.")

    dates = fac_history["reporting_date"].unique()
    formatted_dates = [pd.to_datetime(d).strftime("%Y-%m-%d") for d in dates]

    # ── Metric pools by LOB ─────────────────────────────────────────────────
    lob = facility_data.get("lob", "Unknown")
    corp_metrics = [
        "obligor_rating", "balance", "free_cash_flow", "fixed_charge_coverage",
        "cash_flow_leverage", "liquidity", "profitability", "growth",
    ]
    cre_metrics = [
        "obligor_rating", "balance", "noi", "property_value", "dscr", "ltv",
    ]

    if lob == "Corporate Banking":
        candidates = corp_metrics
    elif lob == "CRE":
        candidates = cre_metrics
    else:
        candidates = list(set(corp_metrics + cre_metrics))

    if custom_metrics:
        candidates.extend(custom_metrics.keys())

    metrics = [
        m for m in candidates
        if m in fac_history.columns and fac_history[m].notna().sum() > 0
    ]

    # ── Build rows ──────────────────────────────────────────────────────────
    _NAMES = {
        "ltv": "LTV (%)", "dscr": "DSCR", "noi": "NOI",
        "free_cash_flow": "Free Cash Flow",
        "fixed_charge_coverage": "Fixed Charge Coverage",
        "cash_flow_leverage": "Cash Flow Leverage",
    }

    table_rows = []
    for metric in metrics:
        values = []
        for date in dates:
            row = fac_history[fac_history["reporting_date"] == date]
            if len(row) == 0:
                values.append("N/A"); continue
            val = row[metric].iloc[0]
            if pd.isna(val):
                values.append("N/A")
            elif metric == "balance":
                values.append(f"${val:,.0f}")
            elif metric == "property_value":
                values.append(f"${val:,.0f}")
            elif metric == "obligor_rating":
                values.append(str(int(val)))
            elif metric in ("ltv", "dscr", "profitability", "growth",
                            "free_cash_flow", "fixed_charge_coverage",
                            "cash_flow_leverage", "liquidity", "noi"):
                values.append(f"{val:.2f}")
            else:
                values.append(str(val))

        name = _NAMES.get(metric)
        if name is None:
            name = (f"{metric} (Custom)" if custom_metrics and metric in custom_metrics
                    else metric.replace("_", " ").title())

        table_rows.append(html.Tr(
            [html.Td(name, style={"fontWeight": "bold", "width": "150px"})]
            + [html.Td(v, style={"width": "120px"}) for v in values]
        ))

    header = html.Tr(
        [html.Th("Metric", style={"width": "150px"})]
        + [html.Th(d, style={"width": "120px"}) for d in formatted_dates]
    )
    tw = 150 + len(formatted_dates) * 120

    return html.Div([
        html.Div([
            html.Table([
                html.Thead([header]), html.Tbody(table_rows),
            ], className="table time-series-table", style={
                "fontSize": "11px", "width": f"{tw}px",
                "minWidth": f"{tw}px", "tableLayout": "fixed",
            })
        ], style={"overflowX": "auto", "width": "100%"})
    ], style={"padding": "10px", "backgroundColor": "#f8f9fa"})
