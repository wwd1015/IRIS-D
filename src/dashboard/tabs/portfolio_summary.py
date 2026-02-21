"""
Portfolio Summary tab – the default landing page.

Shows high-level portfolio metrics, charts, and a positions panel.
This is a fully-implemented tab that serves as a reference for building others.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from dash import html, dcc, callback, Input, Output, State, no_update
import plotly.graph_objs as go
import polars as pl
from ..tabs.registry import BaseTab, TabContext, register_tab
from ..components.toolbar import SliderControl, render_toolbar
from .. import config
from ..auth import user_management


class PortfolioSummaryTab(BaseTab):
    id = "portfolio-summary"
    label = "Portfolio Summary"
    order = 10
    grid_class = "grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)_340px] gap-4 items-stretch"

    # ── Layer 2: Toolbar ────────────────────────────────────────────────────

    def get_toolbar_controls(self, ctx: TabContext):
        # Determine how many reporting periods are available
        dates = ctx.facilities_df[ctx.facilities_df.columns[ctx.facilities_df.columns.index("reporting_date") if "reporting_date" in ctx.facilities_df.columns else 0]].unique().sort()
        max_p = len(dates)
        return [
            SliderControl(
                id="ps-time-window",
                label="Lookback (months)",
                min_val=1,
                max_val=min(max_p, 48),
                step=1,
                value=min(max_p, 48),  # default: show up to 48 months
                marks={1: "1", 12: "12", 24: "24", min(max_p, 48): f"{min(max_p, 48)} (All)"},
                order=10,
                width="min-w-[320px] flex-1",
            ),
        ]

    # ── Layer 3: Content ────────────────────────────────────────────────────

    def render_content(self, ctx: TabContext):
        # For this tab, "content" is really two panels: main + positions
        return html.Div([
            html.Div(
                id="main-content-container",
                children=_create_main_content(
                    ctx.selected_portfolio,
                    ctx.get_filtered_data,
                    ctx.facilities_df,
                    ctx.portfolios,
                ),
            ),
            html.Div(
                id="positions-panel-container",
                children=_create_positions_panel(
                    ctx.selected_portfolio,
                    ctx.facilities_df,
                    ctx.portfolios,
                    ctx.get_filtered_data,
                ),
            ),
        ])

    def render(self, ctx: TabContext):
        """Custom 2-column layout (main + positions) with Layer 2 toolbar above."""
        # Layer 2: toolbar
        toolbar_controls = self.get_toolbar_controls(ctx)
        toolbar = render_toolbar(toolbar_controls, ctx) if toolbar_controls else None

        # Layer 3: main content + positions panel (two-column grid)
        content = self.render_content(ctx)
        grid = html.Div(
            content.children,
            className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] gap-4 items-stretch",
        )

        parts = [p for p in [toolbar, grid] if p is not None]
        return html.Div(parts) if len(parts) > 1 else parts[0]

    # ── Callbacks ──────────────────────────────────────────────────────────

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            Output("main-content-container", "children"),
            [Input("universal-portfolio-dropdown", "value"),
             Input("ps-time-window", "value")],
            prevent_initial_call=True,
        )
        def update_main_content(selected_portfolio, n_periods):
            if not selected_portfolio:
                return no_update

            filtered_fdf = _filter_by_periods(app_state.facilities_df, n_periods)
            gfd = lambda p: app_state._apply_portfolio_filter(p, _get_latest(filtered_fdf))
            return _create_main_content(
                selected_portfolio, gfd, filtered_fdf, app_state.portfolios
            )

        @callback(
            Output("positions-panel-container", "children"),
            [Input("universal-portfolio-dropdown", "value"),
             Input("ps-time-window", "value")],
            prevent_initial_call=True,
        )
        def update_positions_panel(selected_portfolio, n_periods):
            if not selected_portfolio:
                return no_update

            filtered_fdf = _filter_by_periods(app_state.facilities_df, n_periods)
            gfd = lambda p: app_state._apply_portfolio_filter(p, _get_latest(filtered_fdf))
            return _create_positions_panel(
                selected_portfolio, filtered_fdf, app_state.portfolios, gfd
            )


def _filter_by_periods(facilities_df: pl.DataFrame, n_periods):
    """Return facilities from the most recent *n_periods* reporting periods."""
    if n_periods is None:
        return facilities_df
    dates = facilities_df["reporting_date"].unique().sort()
    if n_periods >= len(dates):
        return facilities_df
    cutoff_dates = dates.tail(n_periods)
    return facilities_df.filter(pl.col("reporting_date").is_in(cutoff_dates))


def _get_latest(facilities_df: pl.DataFrame) -> pl.DataFrame:
    """Return the latest-quarter snapshot from a (possibly filtered) DataFrame."""
    if facilities_df.is_empty():
        return facilities_df
    max_date = facilities_df["reporting_date"].max()
    return facilities_df.filter(pl.col("reporting_date") == max_date)


# Auto-register
register_tab(PortfolioSummaryTab())


# =============================================================================
# Private rendering helpers (merged from components/portfolio_summary.py)
# =============================================================================


def _create_charts(portfolio_data: pl.DataFrame):
    """Create charts for the selected portfolio with dark theme and purple styling"""

    if len(portfolio_data) == 0:
        empty_bar = go.Figure()
        empty_bar.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        empty_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', title="Top 10 Holdings by Borrower", height=300, font=dict(color='rgba(255,255,255,0.7)'))

        empty_pie = go.Figure()
        empty_pie.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        empty_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', title="Holdings by Industry", height=300, font=dict(color='rgba(255,255,255,0.7)'))

        return empty_bar, empty_pie

    # Top 10 holdings by borrower
    borrower_totals = (
        portfolio_data
        .group_by("obligor_name")
        .agg(pl.col("balance").sum())
        .sort("balance", descending=True)
        .head(10)
    )

    borrower_names = borrower_totals["obligor_name"].to_list()
    balances = borrower_totals["balance"].to_list()
    balances_m = [f"(${b/1e6:.1f}M)" for b in balances]
    labels = [f"{name}  {bal}" for name, bal in zip(borrower_names, balances_m)]

    bar_fig = go.Figure(data=[
        go.Bar(
            x=balances,
            y=list(range(len(balances))),
            orientation='h',
            marker_color=['#a78bfa','#8b5cf6','#7c3aed','#6d28d9','#5b21b6','#4c1d95','#a78bfa','#8b5cf6','#7c3aed','#6d28d9'],
            text=labels,
            texttemplate="%{text}",
            insidetextanchor='middle',
            textfont=dict(size=12, color='rgba(255,255,255,0.95)'),
            textposition='inside',
        )
    ])

    bar_fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12, color='rgba(255,255,255,0.7)'),
        height=300,
        showlegend=False,
        xaxis=dict(
            title="Balance ($)",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.06)',
            color='rgba(255,255,255,0.5)'
        ),
        yaxis=dict(
            title="",
            showticklabels=False,
            color='rgba(255,255,255,0.5)',
            range=[len(balances)-1, -1]
        )
    )

    # Holdings by industry/property type
    lob_values = portfolio_data["lob"].to_list()
    if 'Corporate Banking' in lob_values:
        cat_data = (
            portfolio_data.filter(pl.col("lob") == "Corporate Banking")["industry"]
            .value_counts()
            .sort("count", descending=True)
        )
        pie_labels = cat_data["industry"].to_list()
        pie_values = cat_data["count"].to_list()
    else:
        cat_data = (
            portfolio_data.filter(pl.col("lob") == "CRE")["cre_property_type"]
            .value_counts()
            .sort("count", descending=True)
        )
        pie_labels = cat_data["cre_property_type"].to_list()
        pie_values = cat_data["count"].to_list()

    pie_fig = go.Figure(data=[
        go.Pie(
            labels=pie_labels,
            values=pie_values,
            hole=0.4,
            marker_colors=['#a78bfa', '#8b5cf6', '#7c3aed', '#6d28d9', '#5b21b6', '#4c1d95', '#2dd4bf', '#14b8a6']
        )
    ])

    pie_fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        font=dict(size=12, color='rgba(255,255,255,0.7)'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=300
    )

    return bar_fig, pie_fig


def _create_watchlist_table(portfolio_data: pl.DataFrame, facilities_df: pl.DataFrame):
    """Create risk table for the selected portfolio with modern styling"""

    if len(portfolio_data) == 0:
        return html.Div("No data available for this portfolio.", className="p-4")

    # Ensure dates are comparable
    if portfolio_data["reporting_date"].dtype != pl.Date and portfolio_data["reporting_date"].dtype != pl.Datetime:
        portfolio_data = portfolio_data.with_columns(pl.col("reporting_date").cast(pl.Datetime))
    if facilities_df["reporting_date"].dtype != pl.Date and facilities_df["reporting_date"].dtype != pl.Datetime:
        facilities_df = facilities_df.with_columns(pl.col("reporting_date").cast(pl.Datetime))

    watchlist_rows = []
    for row in portfolio_data.iter_rows(named=True):
        fac_id = row['facility_id']
        obligor = row['obligor_name']
        current_rating = row['obligor_rating']
        current_balance = row['balance']
        current_date = row['reporting_date']

        prev_facility_data = (
            facilities_df
            .filter(
                (pl.col("facility_id") == fac_id)
                & (pl.col("reporting_date") < current_date)
            )
            .sort("reporting_date")
            .tail(1)
        )

        if not prev_facility_data.is_empty():
            prev_rating = prev_facility_data["obligor_rating"][0]
            rating_movement = "↓" if prev_rating < current_rating else "↑" if prev_rating > current_rating else "→"
            rating_color = "text-red-600" if rating_movement == "↓" else "text-green-600" if rating_movement == "↑" else "text-gray-600"
        else:
            rating_movement = "New"
            rating_color = "text-blue-600"

        is_watchlist = current_rating >= 6 or current_balance > 50000000

        if is_watchlist:
            watchlist_rows.append({
                'obligor': obligor,
                'balance': f"${current_balance/1e6:.1f}M",
                'rating': current_rating,
                'movement': rating_movement,
                'movement_color': rating_color,
                'risk_level': 'High' if current_rating >= 8 else 'Medium' if current_rating >= 6 else 'Watch'
            })

    if not watchlist_rows:
        return html.Div("No high-risk facilities in this portfolio.", className="p-4 text-center text-ink-500")

    watchlist_rows.sort(key=lambda x: (x['rating'], float(x['balance'].replace('$', '').replace('M', ''))), reverse=True)
    watchlist_rows = watchlist_rows[:10]

    table_rows = []
    for item in watchlist_rows:
        risk_badge_class = {
            'High': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
            'Medium': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
            'Watch': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
        }.get(item['risk_level'], 'bg-gray-100 text-gray-800')

        table_rows.append(
            html.Tr([
                html.Td(item['obligor'], className="px-3 py-2 text-xs font-medium"),
                html.Td(item['balance'], className="px-3 py-2 text-xs text-right"),
                html.Td(str(item['rating']), className="px-3 py-2 text-xs text-center"),
                html.Td([
                    html.Span(item['movement'], className=f"text-xs font-medium {item['movement_color']}")
                ], className="px-3 py-2 text-center"),
                html.Td([
                    html.Span(item['risk_level'], className=f"inline-flex px-2 py-1 text-xs font-medium rounded-full {risk_badge_class}")
                ], className="px-3 py-2 text-center")
            ], className="border-b border-slate-100 dark:border-ink-700")
        )

    return html.Div([
        html.Table([
            html.Thead([
                html.Tr([
                    html.Th("Obligor", className="px-3 py-2 text-left text-xs font-medium text-ink-600 dark:text-slate-400"),
                    html.Th("Balance", className="px-3 py-2 text-right text-xs font-medium text-ink-600 dark:text-slate-400"),
                    html.Th("Rating", className="px-3 py-2 text-center text-xs font-medium text-ink-600 dark:text-slate-400"),
                    html.Th("Trend", className="px-3 py-2 text-center text-xs font-medium text-ink-600 dark:text-slate-400"),
                    html.Th("Risk", className="px-3 py-2 text-center text-xs font-medium text-ink-600 dark:text-slate-400")
                ], className="border-b border-slate-200 dark:border-ink-700")
            ]),
            html.Tbody(table_rows)
        ], className="min-w-full")
    ], className="overflow-x-auto")


def _create_main_content(selected_portfolio, get_filtered_data, facilities_df, portfolios=None):
    """Create the main content area with dark theme and purple styling"""
    portfolio_data = get_filtered_data(selected_portfolio)
    bar_fig, pie_fig = _create_charts(portfolio_data)

    lob_values = portfolio_data["lob"].to_list() if len(portfolio_data) > 0 else []
    if len(portfolio_data) > 0 and 'Corporate Banking' in lob_values:
        pie_chart_title = "Holdings by Industry"
        bar_chart_subtitle = "Asset Type = Corporate Banking"
    else:
        pie_chart_title = "Holdings by Property Type"
        bar_chart_subtitle = "Asset Type = CRE"

    return html.Section([
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Top 10 Holdings by Borrowers", className="text-sm font-semibold"),
                    html.Div(bar_chart_subtitle, className="text-xs text-ink-500 dark:text-slate-400")
                ], className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-ink-700"),
                dcc.Graph(
                    figure=bar_fig,
                    config={'displayModeBar': False},
                    style={'height': '300px'}
                )
            ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 p-4"),
            html.Div([
                html.Div([
                    html.H3(pie_chart_title, className="text-sm font-semibold"),
                    html.Div("Portfolio Distribution", className="text-xs text-ink-500 dark:text-slate-400")
                ], className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-ink-700"),
                dcc.Graph(
                    figure=pie_fig,
                    config={'displayModeBar': False},
                    style={'height': '300px'}
                )
            ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 p-4")
        ], className="grid grid-cols-1 xl:grid-cols-2 gap-4"),
        html.Div([
            html.Div([
                html.H3("Credit Watchlist", className="text-sm font-semibold"),
                html.Div("High Risk Facilities", className="text-xs text-ink-500 dark:text-slate-400")
            ], className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-ink-700 mb-4"),
            _create_watchlist_table(portfolio_data, facilities_df)
        ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 p-4 mt-4 flex-1 min-h-0 overflow-y-auto")
    ], className="flex flex-col min-h-[600px]")


def _create_positions_panel(selected_portfolio, facilities_df: pl.DataFrame, portfolios, get_filtered_data):
    """Create portfolio positions panel with modern Tailwind styling"""
    portfolio_data = get_filtered_data(selected_portfolio)

    if len(portfolio_data) == 0:
        return html.Div("No data available for this portfolio.", className="p-4 positions-panel")

    all_portfolios_data = []
    for pname in portfolios.keys():
        pdata = get_filtered_data(pname)
        if len(pdata) > 0:
            all_portfolios_data.append(pdata)

    if all_portfolios_data:
        all_data = pl.concat(all_portfolios_data).unique()
    else:
        all_data = pl.DataFrame()

    if len(portfolio_data) == 0:
        return html.Div("No data available for this portfolio.", className="p-4 positions-panel")

    total_balance_all = all_data["balance"].sum() if len(all_data) > 0 and "balance" in all_data.columns else 0
    total_balance = portfolio_data["balance"].sum() if "balance" in portfolio_data.columns else 0
    pct_of_total = (total_balance / total_balance_all * 100) if total_balance_all > 0 else 0

    avg_rating = portfolio_data["obligor_rating"].mean() if "obligor_rating" in portfolio_data.columns else None

    today = datetime.today()
    # Handle maturity_date — cast to datetime if needed
    mat_df = portfolio_data
    if "maturity_date" in mat_df.columns:
        if mat_df["maturity_date"].dtype == pl.Utf8:
            mat_df = mat_df.with_columns(pl.col("maturity_date").str.to_datetime())
        maturity_days = mat_df.with_columns(
            ((pl.col("maturity_date") - pl.lit(today)).dt.total_days()).alias("days_to_mat")
        )
        avg_maturity_yrs = maturity_days["days_to_mat"].mean() / 365.25 if maturity_days["days_to_mat"].mean() is not None else 0

        mat_years = maturity_days["days_to_mat"].to_list()
        n = len(mat_years)
        buckets = [(1, 3), (3, 5), (5, 100)]
        maturity_percents = []
        for lo, hi in buckets:
            lo_days, hi_days = lo * 365.25, hi * 365.25
            count = sum(1 for d in mat_years if d is not None and lo_days <= d < hi_days)
            maturity_percents.append(count / n * 100 if n > 0 else 0)
        na_percent = 100 - sum(maturity_percents)
    else:
        avg_maturity_yrs = 0
        maturity_percents = [0, 0, 0]
        na_percent = 100

    rating_rows = []
    for rating in range(1, 18):
        rating_balance = portfolio_data.filter(pl.col("obligor_rating") == rating)["balance"].sum()
        percent = (rating_balance / total_balance * 100) if total_balance > 0 else 0

        if percent > 0:
            rating_rows.append(
                html.Div([
                    html.Span(f"{rating}", className="text-xs text-ink-700 dark:text-slate-300"),
                    html.Span(f"{percent:.1f}%", className="text-xs text-ink-600 dark:text-slate-400")
                ], className="flex justify-between")
            )

    return html.Div([
        html.Div([
            html.Div([
                html.Span("Portfolio", className="text-xs font-semibold text-ink-800 dark:text-slate-200"),
                html.Div([
                    html.Span(selected_portfolio, className="text-xs text-ink-700 dark:text-slate-300"),
                    html.Span(f"{pct_of_total:.1f}%", className="text-xs text-ink-600 dark:text-slate-400")
                ], className="flex justify-between mt-1")
            ]),
            html.Hr(className="my-2 border-slate-200 dark:border-ink-700"),
            html.Div([
                html.Span("Portfolio Totals", className="text-xs font-semibold text-ink-800 dark:text-slate-200"),
                html.Div([
                    html.Span("Total Balance", className="text-xs text-ink-700 dark:text-slate-300"),
                    html.Span(f"${total_balance:,.0f}", className="text-xs text-ink-600 dark:text-slate-400")
                ], className="flex justify-between"),
                html.Div([
                    html.Span("Avg Risk Rating", className="text-xs text-ink-700 dark:text-slate-300"),
                    html.Span(f"{avg_rating:.2f}" if avg_rating is not None else "N/A", className="text-xs text-ink-600 dark:text-slate-400")
                ], className="flex justify-between"),
                html.Div([
                    html.Span("Avg Maturity (Yrs)", className="text-xs text-ink-700 dark:text-slate-300"),
                    html.Span(f"{avg_maturity_yrs:.2f}", className="text-xs text-ink-600 dark:text-slate-400")
                ], className="flex justify-between")
            ], className="mt-2 space-y-1"),
            html.Hr(className="my-2 border-slate-200 dark:border-ink-700"),
            html.Div([
                html.Span("Eff. Maturities", className="text-xs font-semibold text-ink-800 dark:text-slate-200"),
                html.Div([
                    html.Span("1-3 Yrs", className="text-xs text-ink-700 dark:text-slate-300"),
                    html.Span(f"{maturity_percents[0]:.2f}%", className="text-xs text-ink-600 dark:text-slate-400")
                ], className="flex justify-between"),
                html.Div([
                    html.Span("3-5 Yrs", className="text-xs text-ink-700 dark:text-slate-300"),
                    html.Span(f"{maturity_percents[1]:.2f}%", className="text-xs text-ink-600 dark:text-slate-400")
                ], className="flex justify-between"),
                html.Div([
                    html.Span(">5 Yrs", className="text-xs text-ink-700 dark:text-slate-300"),
                    html.Span(f"{maturity_percents[2]:.2f}%", className="text-xs text-ink-600 dark:text-slate-400")
                ], className="flex justify-between"),
                html.Div([
                    html.Span("N/A", className="text-xs text-ink-700 dark:text-slate-300"),
                    html.Span(f"{na_percent:.2f}%", className="text-xs text-ink-600 dark:text-slate-400")
                ], className="flex justify-between")
            ], className="mt-2 space-y-1"),
            html.Hr(className="my-2 border-slate-200 dark:border-ink-700"),
            html.Div([
                html.Span("Ratings", className="text-xs font-semibold text-ink-800 dark:text-slate-200"),
                *rating_rows
            ], className="mt-2 space-y-1")
        ], className="p-4")
    ], className="chart-card positions-panel h-full")


# =============================================================================
# Private helpers (merged from components/portfolio_management.py)
# =============================================================================
