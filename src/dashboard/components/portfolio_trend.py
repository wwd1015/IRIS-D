from dash import html, dcc
import plotly.graph_objs as go
import pandas as pd


def create_portfolio_trend_sidebar(selected_portfolio, available_portfolios):
    """Create simplified sidebar for Portfolio Trend tab with consistent styling"""
    return html.Section([
        html.Header([
            html.H2("Portfolio Trend", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700 flex items-center justify-between"),
        html.Div([
            html.Div([
                html.Label("Portfolio:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='portfolio-dropdown',
                    options=[{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios],
                    value=selected_portfolio,
                    placeholder="Select portfolio...",
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-3"),
            html.Div([
                html.Label("Benchmark Portfolio:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='financial-trends-benchmark-dropdown',
                    options=[{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios],
                    value=None,
                    placeholder="Select benchmark portfolio...",
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-4"),
            html.Hr(className="border-slate-200 dark:border-ink-700 mb-4"),
            html.H3("Create Custom Metric", className="text-sm font-semibold mb-3 text-brand-500"),
            html.Div([
                html.Label("Formula:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                html.P("Supports conditions & backticks. Use 'or' for multiple values. Examples: (`Obligor Rating` == 15 or `Obligor Rating` == 16) * Balance, `free cash flow` / liquidity", 
                       className="text-xs text-ink-500 dark:text-slate-400 mb-2"),
                dcc.Input(
                    id='custom-metric-formula',
                    type='text',
                    placeholder="e.g., (`Obligor Rating` == 15 or `Obligor Rating` == 16) * Balance",
                    className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-ink-600 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                )
            ], className="mb-3"),
            html.Div([
                html.Label("Metric Name:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Input(
                    id='custom-metric-name',
                    type='text',
                    placeholder="Enter metric name...",
                    className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-ink-600 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                )
            ], className="mb-3"),
            html.Button("Create Metric", id='create-metric-btn', 
                       className="w-full px-3 py-2 text-xs bg-brand-500 text-white rounded-md hover:bg-brand-400 transition-colors"),
            html.Div(id='metric-creation-alert', className="mt-3")
        ], className="p-4 flex-1 overflow-auto")
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden flex flex-col min-h-[640px]")


def get_portfolio_metrics(selected_portfolio, custom_metrics, portfolios, facilities_df):
    """Get appropriate metrics based on portfolio type and available data columns"""
    
    # Common metrics available for all portfolio types
    common_metrics = ['balance', 'obligor_rating']
    
    # Portfolio-specific metrics based on actual facilities.csv columns
    corporate_banking_metrics = ['free_cash_flow', 'fixed_charge_coverage', 'cash_flow_leverage', 'liquidity', 'profitability', 'growth']
    cre_metrics = ['noi', 'property_value', 'dscr', 'ltv']
    
    # Get all available columns from the dataframe
    exclude_cols = ['facility_id', 'obligor_name', 'origination_date', 'maturity_date', 'reporting_date', 'lob', 'industry', 'cre_property_type', 'msa', 'sir']
    all_numeric_cols = [col for col in facilities_df.columns if col not in exclude_cols]
    
    # Determine which metrics to show based on portfolio type
    available_cols = common_metrics.copy()
    
    if selected_portfolio and selected_portfolio in portfolios:
        portfolio_criteria = portfolios[selected_portfolio]
        lob = portfolio_criteria.get('lob')
        
        if lob == 'Corporate Banking':
            # Add Corporate Banking specific metrics
            for metric in corporate_banking_metrics:
                if metric in all_numeric_cols:
                    available_cols.append(metric)
        elif lob == 'CRE':
            # Add CRE specific metrics
            for metric in cre_metrics:
                if metric in all_numeric_cols:
                    available_cols.append(metric)
        else:
            # For mixed or custom portfolios, include all relevant metrics
            available_cols.extend([col for col in corporate_banking_metrics + cre_metrics if col in all_numeric_cols])
    else:
        # Default: show all available metrics
        available_cols = all_numeric_cols
    
    # Create human-readable labels
    metric_options = []
    for col in available_cols:
        if col in facilities_df.columns:
            # Convert snake_case to Title Case
            label = col.replace('_', ' ').title()
            metric_options.append({'label': label, 'value': col})
    
    # Add custom metrics
    for metric_name, formula in custom_metrics.items():
        metric_options.append({'label': f"{metric_name} (Custom)", 'value': metric_name})
    
    return metric_options


def create_portfolio_trend_content(selected_portfolio, custom_metrics, portfolios, facilities_df, get_filtered_data):
    """Create the Portfolio Trend tab content"""
    metrics_options = get_portfolio_metrics(selected_portfolio, custom_metrics, portfolios, facilities_df)
    default_metric_1 = metrics_options[0]['value'] if metrics_options else 'balance'
    default_metric_2 = metrics_options[1]['value'] if len(metrics_options) > 1 else 'balance'
    default_metric_3 = metrics_options[2]['value'] if len(metrics_options) > 2 else 'balance'
    
    # Get available date range for time slider
    if selected_portfolio and selected_portfolio in portfolios:
        portfolio_data = get_filtered_data(selected_portfolio)
        if len(portfolio_data) > 0:
            # Get all dates for this portfolio from facilities_df
            portfolio_criteria = portfolios[selected_portfolio]
            all_facility_data = facilities_df.copy()
            if portfolio_criteria['lob']:
                all_facility_data = all_facility_data[all_facility_data['lob'] == portfolio_criteria['lob']]
            if portfolio_criteria['lob'] == 'Corporate Banking' and portfolio_criteria['industry']:
                if isinstance(portfolio_criteria['industry'], list):
                    all_facility_data = all_facility_data[all_facility_data['industry'].astype(str).isin([str(i) for i in portfolio_criteria['industry']])]
                else:
                    all_facility_data = all_facility_data[all_facility_data['industry'] == portfolio_criteria['industry']]
            if portfolio_criteria['lob'] == 'CRE' and portfolio_criteria['property_type']:
                if isinstance(portfolio_criteria['property_type'], list):
                    all_facility_data = all_facility_data[all_facility_data['cre_property_type'].astype(str).isin([str(i) for i in portfolio_criteria['property_type']])]
                else:
                    all_facility_data = all_facility_data[all_facility_data['cre_property_type'] == portfolio_criteria['property_type']]
            
            unique_dates = sorted(all_facility_data['reporting_date'].unique())
    
    return html.Div([
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


def get_timeseries(facilities_df, portfolios, portfolio_name, metric, agg_method='avg'):
    """Get time series for a portfolio and metric"""
    # Use facilities_df directly
    df = facilities_df.copy()
    
    if portfolio_name not in portfolios or not metric:
        return pd.Series()
    
    # Apply portfolio filters
    criteria = portfolios[portfolio_name]
    if 'lob' in df.columns and criteria.get('lob'):
        df = df[df['lob'] == criteria['lob']]
    if 'industry' in df.columns and criteria.get('lob') == 'Corporate Banking' and criteria.get('industry'):
        if isinstance(criteria['industry'], list):
            df = df[df['industry'].astype(str).isin([str(i) for i in criteria['industry']])]
        else:
            df = df[df['industry'] == criteria['industry']]
    if 'cre_property_type' in df.columns and criteria.get('lob') == 'CRE' and criteria.get('property_type'):
        if isinstance(criteria['property_type'], list):
            df = df[df['cre_property_type'].astype(str).isin([str(i) for i in criteria['property_type']])]
        else:
            df = df[df['cre_property_type'] == criteria['property_type']]
    
    # Filter by obligors (alternative to industry/property type)
    if 'obligor_name' in df.columns and criteria.get('obligors'):
        if isinstance(criteria['obligors'], list):
            df = df[df['obligor_name'].astype(str).isin([str(i) for i in criteria['obligors']])]
        else:
            df = df[df['obligor_name'] == criteria['obligors']]
    
    # Check if metric column exists in data
    if metric not in df.columns:
        return pd.Series()
    
    # Group by reporting_date
    date_col = 'reporting_date'
    if date_col not in df.columns:
        return pd.Series()
    
    df[date_col] = pd.to_datetime(df[date_col])
    
    group = df.groupby(date_col)
    
    # Calculate aggregated value based on selected method
    if agg_method == 'sum':
        ts = group[metric].sum()
    else:  # default to 'avg'
        ts = group[metric].mean()
    
    return ts


def build_portfolio_trend_chart(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric, agg_method='avg'):
    """Build chart for a portfolio trend metric"""
    if not metric:
        # Return empty chart if no metric specified
        fig = go.Figure()
        fig.update_layout(
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            height=350,
            margin=dict(l=40, r=20, t=20, b=100),
            font=dict(size=12, color='#1f2937'),
            autosize=True
        )
        fig.add_annotation(text="Select a metric to view chart", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
        
    ts_main = get_timeseries(facilities_df, portfolios, selected_portfolio, metric, agg_method)
    ts_bench = get_timeseries(facilities_df, portfolios, benchmark_portfolio, metric, agg_method) if benchmark_portfolio else None
    
    fig = go.Figure()
    
    if not ts_main.empty:
        fig.add_trace(go.Scatter(
            x=ts_main.index,
            y=ts_main.values,
            mode='lines+markers',
            name='Selected Portfolio',
            line=dict(color='#1e3a8a', width=3, dash='solid'),
            marker=dict(color='#1e3a8a')
        ))
    
    if ts_bench is not None and not ts_bench.empty:
        fig.add_trace(go.Scatter(
            x=ts_bench.index,
            y=ts_bench.values,
            mode='lines+markers',
            name='Benchmark Portfolio',
            line=dict(color='#60a5fa', width=3, dash='dash'),
            marker=dict(color='#60a5fa')
        ))
    
    fig.update_layout(
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        height=350,
        margin=dict(l=40, r=20, t=20, b=100),
        font=dict(size=12, color='#1f2937'),
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
            gridcolor='#e5e7eb',
            color='#374151'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#e5e7eb',
            color='#374151'
        )
    )
    
    return fig


def create_portfolio_trends_charts(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric1, metric2, metric3, agg1, agg2, agg3):
    """Create all three portfolio trend charts"""
    chart1 = build_portfolio_trend_chart(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric1, agg1)
    chart2 = build_portfolio_trend_chart(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric2, agg2)
    chart3 = build_portfolio_trend_chart(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric3, agg3)
    
    return chart1, chart2, chart3