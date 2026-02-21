"""
Portfolio Trend tab – time-series charts comparing portfolio metrics.

Shows up to three configurable metric charts with benchmark comparison,
custom metric creation, and aggregation options.
"""

from __future__ import annotations

from dash import html, dcc
import plotly.graph_objs as go
import pandas as pd

from ..tabs.registry import BaseTab, TabContext, register_tab


class PortfolioTrendTab(BaseTab):
    id = "portfolio-trend"
    label = "Portfolio Trend"
    order = 30

    # ── Layer 2: Toolbar ────────────────────────────────────────────────────

    def get_toolbar_controls(self, ctx: TabContext):
        from ..components.toolbar import DropdownControl
        portfolio_opts = [{"label": p, "value": p} for p in ctx.available_portfolios]
        return [
            DropdownControl(
                id="financial-trends-benchmark-dropdown",
                label="Benchmark Portfolio",
                options=portfolio_opts,
                value=None,
                placeholder="Select benchmark…",
                order=10,
                width="min-w-[220px]",
            ),
        ]

    # ── Content ─────────────────────────────────────────────────────────────

    def render_content(self, ctx: TabContext):
        return _create_portfolio_trend_content(
            ctx.selected_portfolio, ctx.custom_metrics,
            ctx.portfolios, ctx.facilities_df, ctx.get_filtered_data,
        )

    # ── Callbacks ────────────────────────────────────────────────────────────

    def register_callbacks(self, app) -> None:
        from dash import Input, Output, State, callback, no_update
        from ..app_state import app_state

        @callback(
            [Output('financial-trends-chart-1', 'figure'),
             Output('financial-trends-chart-2', 'figure'),
             Output('financial-trends-chart-3', 'figure')],
            [Input('financial-trends-metric-dropdown-1', 'value'),
             Input('financial-trends-metric-dropdown-2', 'value'),
             Input('financial-trends-metric-dropdown-3', 'value'),
             Input('financial-trends-agg-dropdown-1', 'value'),
             Input('financial-trends-agg-dropdown-2', 'value'),
             Input('financial-trends-agg-dropdown-3', 'value'),
             Input('financial-trends-benchmark-dropdown', 'value'),
             Input('universal-portfolio-dropdown', 'value')],
            prevent_initial_call=False,
        )
        def update_trend_charts(m1, m2, m3, a1, a2, a3, benchmark, portfolio):
            sel = portfolio or app_state.default_portfolio
            return create_portfolio_trends_charts(
                app_state.facilities_df, app_state.portfolios,
                sel, benchmark, m1, m2, m3, a1, a2, a3,
            )


register_tab(PortfolioTrendTab())


# =============================================================================
# Private rendering helpers
# =============================================================================



def _create_custom_metric_panel():
    """Collapsible custom metric creation panel rendered at the top of the content area."""
    return html.Details([
        html.Summary("Create Custom Metric",
                     className="text-sm font-semibold text-brand-500 cursor-pointer select-none px-4 py-3"),
        html.Div([
            html.Div([
                html.Label("Formula:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                html.P(
                    "Supports conditions & backticks, e.g. (`Obligor Rating` == 15) * Balance",
                    className="text-xs text-ink-500 dark:text-slate-400 mb-2",
                ),
                dcc.Input(
                    id="custom-metric-formula", type="text",
                    placeholder="e.g., (`Obligor Rating` == 15 or `Obligor Rating` == 16) * Balance",
                    className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-ink-600 rounded-md focus:ring-2 focus:ring-brand-500",
                ),
            ], className="mb-3"),
            html.Div([
                html.Label("Metric Name:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Input(
                    id="custom-metric-name", type="text", placeholder="Enter metric name…",
                    className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-ink-600 rounded-md focus:ring-2 focus:ring-brand-500",
                ),
            ], className="mb-3"),
            html.Button("Create Metric", id="create-metric-btn",
                        className="px-3 py-2 text-xs bg-brand-500 text-white rounded-md hover:bg-brand-400 transition-colors"),
            html.Div(id="metric-creation-alert", className="mt-3"),
        ], className="px-4 pb-4"),
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 mb-4")


def _get_portfolio_metrics(selected_portfolio, custom_metrics, portfolios, facilities_df):
    """Get appropriate metrics based on available numeric columns in the data."""
    exclude_cols = {'facility_id', 'obligor_name', 'origination_date', 'maturity_date',
                    'reporting_date', 'lob', 'industry', 'cre_property_type', 'msa', 'sir',
                    'risk_category'}
    numeric_cols = [
        col for col in facilities_df.select_dtypes(include='number').columns
        if col not in exclude_cols
    ]

    metric_options = [
        {'label': col.replace('_', ' ').title(), 'value': col}
        for col in numeric_cols
    ]

    for metric_name in custom_metrics:
        metric_options.append({'label': f"{metric_name} (Custom)", 'value': metric_name})

    return metric_options


def _create_portfolio_trend_content(selected_portfolio, custom_metrics, portfolios, facilities_df, get_filtered_data):
    """Create the Portfolio Trend tab content (custom metric panel + three charts)."""
    metrics_options = _get_portfolio_metrics(selected_portfolio, custom_metrics, portfolios, facilities_df)
    default_metric_1 = metrics_options[0]['value'] if metrics_options else 'balance'
    default_metric_2 = metrics_options[1]['value'] if len(metrics_options) > 1 else 'balance'
    default_metric_3 = metrics_options[2]['value'] if len(metrics_options) > 2 else 'balance'

    return html.Div([
        _create_custom_metric_panel(),
        # First Chart
        html.Div([
            html.Div([
                html.Div([
                    html.Label("Metric 1:", className="form-label"),
                    dcc.Dropdown(
                        id='financial-trends-metric-dropdown-1',
                        options=metrics_options,
                        value=default_metric_1,
                        className="form-select"
                    )
                ], style={"width": "40%", "marginRight": "10px"}),
                html.Div([
                    html.Label("Aggregation:", className="form-label"),
                    dcc.Dropdown(
                        id='financial-trends-agg-dropdown-1',
                        options=[
                            {'label': 'Average', 'value': 'avg'},
                            {'label': 'Sum', 'value': 'sum'}
                        ],
                        value='avg',
                        className="form-select"
                    )
                ], style={"width": "25%", "marginRight": "10px"}),
                html.Div([
                    html.Label("", className="form-label", style={"visibility": "hidden"}),
                    html.Button("Download Data", id="download-btn-1", className="btn btn-outline", 
                               style={"fontSize": "12px", "padding": "6px 12px", "whiteSpace": "nowrap"})
                ], style={"width": "25%", "display": "flex", "justifyContent": "flex-end", "alignItems": "end"}),
            ], className="form-group", style={"display": "flex", "alignItems": "end", "marginBottom": "10px"}),
            html.Div([
                dcc.Download(id="download-data-1"),
                dcc.Graph(id='financial-trends-chart-1', config={'displayModeBar': False})
            ])
        ], className="chart-card", style={"marginBottom": "20px"}),
        
        # Second Chart
        html.Div([
            html.Div([
                html.Div([
                    html.Label("Metric 2:", className="form-label"),
                    dcc.Dropdown(
                        id='financial-trends-metric-dropdown-2',
                        options=metrics_options,
                        value=default_metric_2,
                        className="form-select"
                    )
                ], style={"width": "40%", "marginRight": "10px"}),
                html.Div([
                    html.Label("Aggregation:", className="form-label"),
                    dcc.Dropdown(
                        id='financial-trends-agg-dropdown-2',
                        options=[
                            {'label': 'Average', 'value': 'avg'},
                            {'label': 'Sum', 'value': 'sum'}
                        ],
                        value='avg',
                        className="form-select"
                    )
                ], style={"width": "25%", "marginRight": "10px"}),
                html.Div([
                    html.Label("", className="form-label", style={"visibility": "hidden"}),
                    html.Button("Download Data", id="download-btn-2", className="btn btn-outline", 
                               style={"fontSize": "12px", "padding": "6px 12px", "whiteSpace": "nowrap"})
                ], style={"width": "25%", "display": "flex", "justifyContent": "flex-end", "alignItems": "end"}),
            ], className="form-group", style={"display": "flex", "alignItems": "end", "marginBottom": "10px"}),
            html.Div([
                dcc.Download(id="download-data-2"),
                dcc.Graph(id='financial-trends-chart-2', config={'displayModeBar': False})
            ])
        ], className="chart-card", style={"marginBottom": "20px"}),
        
        # Third Chart
        html.Div([
            html.Div([
                html.Div([
                    html.Label("Metric 3:", className="form-label"),
                    dcc.Dropdown(
                        id='financial-trends-metric-dropdown-3',
                        options=metrics_options,
                        value=default_metric_3,
                        className="form-select"
                    )
                ], style={"width": "40%", "marginRight": "10px"}),
                html.Div([
                    html.Label("Aggregation:", className="form-label"),
                    dcc.Dropdown(
                        id='financial-trends-agg-dropdown-3',
                        options=[
                            {'label': 'Average', 'value': 'avg'},
                            {'label': 'Sum', 'value': 'sum'}
                        ],
                        value='avg',
                        className="form-select"
                    )
                ], style={"width": "25%", "marginRight": "10px"}),
                html.Div([
                    html.Label("", className="form-label", style={"visibility": "hidden"}),
                    html.Button("Download Data", id="download-btn-3", className="btn btn-outline", 
                               style={"fontSize": "12px", "padding": "6px 12px", "whiteSpace": "nowrap"})
                ], style={"width": "25%", "display": "flex", "justifyContent": "flex-end", "alignItems": "end"}),
            ], className="form-group", style={"display": "flex", "alignItems": "end", "marginBottom": "10px"}),
            html.Div([
                dcc.Download(id="download-data-3"),
                dcc.Graph(id='financial-trends-chart-3', config={'displayModeBar': False})
            ])
        ], className="chart-card")
    ], className="main-content")


def _apply_filters(df, criteria):
    """Apply the new filter-list format to a DataFrame."""
    from ..app_state import AppState
    criteria = AppState._migrate_criteria(criteria)
    for level in criteria.get("filters", []):
        col, vals = level.get("column"), level.get("values", [])
        if col and vals and col in df.columns:
            df = df[df[col].astype(str).isin([str(v) for v in vals])]
    return df


def _get_timeseries(facilities_df, portfolios, portfolio_name, metric, agg_method='avg'):
    """Get time series for a portfolio and metric."""
    if portfolio_name not in portfolios or not metric:
        return pd.Series()

    df = facilities_df.copy()
    df = _apply_filters(df, portfolios[portfolio_name])

    if metric not in df.columns:
        return pd.Series()

    date_col = 'reporting_date'
    if date_col not in df.columns:
        return pd.Series()

    df[date_col] = pd.to_datetime(df[date_col])
    group = df.groupby(date_col)

    if agg_method == 'sum':
        return group[metric].sum()
    return group[metric].mean()


def build_portfolio_trend_chart(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric, agg_method='avg'):
    """Build chart for a portfolio trend metric.
    
    Note: Public because it's called from app.py callbacks.
    """
    if not metric:
        fig = go.Figure()
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            height=350,
            margin=dict(l=40, r=20, t=20, b=100),
            font=dict(size=12, color='rgba(255,255,255,0.7)'),
            autosize=True
        )
        fig.add_annotation(text="Select a metric to view chart", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
        
    ts_main = _get_timeseries(facilities_df, portfolios, selected_portfolio, metric, agg_method)
    ts_bench = _get_timeseries(facilities_df, portfolios, benchmark_portfolio, metric, agg_method) if benchmark_portfolio else None
    
    fig = go.Figure()
    
    if not ts_main.empty:
        fig.add_trace(go.Scatter(
            x=ts_main.index,
            y=ts_main.values,
            mode='lines+markers',
            name='Selected Portfolio',
            line=dict(color='#a78bfa', width=3, dash='solid'),
            marker=dict(color='#a78bfa')
        ))
    
    if ts_bench is not None and not ts_bench.empty:
        fig.add_trace(go.Scatter(
            x=ts_bench.index,
            y=ts_bench.values,
            mode='lines+markers',
            name='Benchmark Portfolio',
            line=dict(color='#2dd4bf', width=3, dash='dash'),
            marker=dict(color='#2dd4bf')
        ))
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=40, r=20, t=20, b=100),
        font=dict(size=12, color='rgba(255,255,255,0.7)'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        autosize=True,
        xaxis=dict(
            rangeslider=dict(
                visible=True,
                thickness=0.15,
                bgcolor='rgba(0,0,0,0)',
                bordercolor='rgba(0,0,0,0)'
            ),
            showgrid=True,
            gridcolor='rgba(255,255,255,0.06)',
            color='rgba(255,255,255,0.5)'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.06)',
            color='rgba(255,255,255,0.5)'
        )
    )
    
    return fig


def create_portfolio_trends_charts(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric1, metric2, metric3, agg1, agg2, agg3):
    """Create all three portfolio trend charts.
    
    Note: Public because it's called from app.py callbacks.
    """
    chart1 = build_portfolio_trend_chart(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric1, agg1)
    chart2 = build_portfolio_trend_chart(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric2, agg2)
    chart3 = build_portfolio_trend_chart(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric3, agg3)
    
    return chart1, chart2, chart3
