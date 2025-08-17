from dash import html, dcc
import math
import pandas as pd


def create_holdings_sidebar(selected_portfolio, available_portfolios, portfolios, get_filtered_data):
    """Create simplified sidebar for Holdings tab with consistent styling"""
    return html.Section([
        html.Header([
            html.H2("Holdings", className="text-sm font-semibold")
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
            ], className="mb-4"),
            html.Hr(className="border-slate-200 dark:border-ink-700 mb-4"),
            html.H3("Filters", className="text-sm font-semibold mb-3 text-brand-500"),
            html.Div(id='holdings-filters-container', children=create_holdings_filters(selected_portfolio, portfolios, get_filtered_data))
        ], className="p-4 flex-1 overflow-auto")
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden flex flex-col min-h-[640px]")


def create_holdings_filters(selected_portfolio, portfolios, get_filtered_data):
    """Create dynamic filters based on portfolio type"""
    if not selected_portfolio or selected_portfolio not in portfolios:
        return []
    
    portfolio_criteria = portfolios[selected_portfolio]
    portfolio_data = get_filtered_data(selected_portfolio)
    filters = []
    
    # Obligor filter
    obligor_options = sorted(portfolio_data['obligor_name'].unique())
    filters.append(
        html.Div([
            html.Label("Obligor:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
            dcc.Dropdown(
                id='holdings-obligor-filter',
                options=[{'label': obligor, 'value': obligor} for obligor in obligor_options],
                value=None,
                placeholder="All obligors...",
                className="text-xs",
                style={"fontSize": "12px"},
                multi=True
            )
        ], className="mb-3")
    )
    
    # Rating filter (common to all portfolios)
    rating_options = sorted(portfolio_data['obligor_rating'].unique())
    filters.append(
        html.Div([
            html.Label("Rating:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
            dcc.Dropdown(
                id='holdings-rating-filter',
                options=[{'label': str(rating), 'value': rating} for rating in rating_options],
                value=None,
                placeholder="All ratings...",
                className="text-xs",
                style={"fontSize": "12px"},
                multi=True
            )
        ], className="mb-3")
    )
    
    # Portfolio-specific filters
    if portfolio_criteria['lob'] == 'Corporate Banking':
        # Industry filter for Corporate Banking
        industry_options = sorted(portfolio_data['industry'].dropna().unique())
        filters.append(
            html.Div([
                html.Label("Industry:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='holdings-industry-filter',
                    options=[{'label': industry, 'value': industry} for industry in industry_options],
                    value=None,
                    placeholder="All industries...",
                    className="text-xs",
                    style={"fontSize": "12px"},
                    multi=True
                )
            ], className="mb-3")
        )
    
    elif portfolio_criteria['lob'] == 'CRE':
        # Property type filter for CRE
        property_options = sorted(portfolio_data['cre_property_type'].dropna().unique())
        filters.append(
            html.Div([
                html.Label("Property Type:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='holdings-property-filter',
                    options=[{'label': prop_type, 'value': prop_type} for prop_type in property_options],
                    value=None,
                    placeholder="All property types...",
                    className="text-xs",
                    style={"fontSize": "12px"},
                    multi=True
                )
            ], className="mb-3")
        )
        
        # MSA filter for CRE
        msa_options = sorted(portfolio_data['msa'].dropna().unique())
        filters.append(
            html.Div([
                html.Label("MSA:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='holdings-msa-filter',
                    options=[{'label': msa, 'value': msa} for msa in msa_options],
                    value=None,
                    placeholder="All MSAs...",
                    className="text-xs",
                    style={"fontSize": "12px"},
                    multi=True
                )
            ], className="mb-3")
        )
    
    # Balance range filter
    max_balance = portfolio_data['balance'].max()
    min_balance_m = 0  # Set minimum to 0
    max_balance_m = math.ceil(max_balance / 1000000)  # Round up to whole integer
    
    filters.append(
        html.Div([
            html.Label("Balance Range ($ Millions):", className="form-label"),
            dcc.RangeSlider(
                id='holdings-balance-filter',
                min=min_balance_m,
                max=max_balance_m,
                value=[min_balance_m, max_balance_m],
                step=1,
                tooltip={"placement": "bottom", "always_visible": True},
                marks={
                    min_balance_m: f"${min_balance_m}M",
                    max_balance_m: f"${max_balance_m}M"
                }
            )
        ], className="form-group", style={"marginBottom": "20px"})
    )
    
    return filters


def create_holdings_content(selected_portfolio, get_filtered_data):
    """Create the Holdings tab content"""
    return html.Div([
        html.Div(id='holdings-table-container', children=create_holdings_table(get_filtered_data(selected_portfolio))),
    ], className="main-content")


def create_holdings_table(portfolio_data, rating_filter=None, obligor_filter=None, industry_filter=None, property_filter=None, msa_filter=None, balance_filter=None):
    """Create collapsible table for Holdings tab with optional filters"""
    
    if len(portfolio_data) == 0:
        return html.Div("No data available for this portfolio.", className="p-4")
    
    # Apply filters
    if rating_filter:
        portfolio_data = portfolio_data[portfolio_data['obligor_rating'].isin(rating_filter)]
    
    if obligor_filter:
        portfolio_data = portfolio_data[portfolio_data['obligor_name'].isin(obligor_filter)]
    
    if industry_filter:
        portfolio_data = portfolio_data[portfolio_data['industry'].isin(industry_filter)]
    
    if property_filter:
        portfolio_data = portfolio_data[portfolio_data['cre_property_type'].isin(property_filter)]
    
    if msa_filter:
        portfolio_data = portfolio_data[portfolio_data['msa'].isin(msa_filter)]
    
    if balance_filter:
        # Convert million values back to actual balance values
        min_balance_actual = balance_filter[0] * 1000000
        max_balance_actual = balance_filter[1] * 1000000
        portfolio_data = portfolio_data[
            (portfolio_data['balance'] >= min_balance_actual) & 
            (portfolio_data['balance'] <= max_balance_actual)
        ]
    
    if len(portfolio_data) == 0:
        return html.Div("No data matches the selected filters.", className="p-4")
    
    # Get unique facilities
    facilities = portfolio_data['facility_id'].unique()
    
    # Create collapsible table rows
    table_rows = []
    
    for facility_id in facilities:
        facility_data = portfolio_data[portfolio_data['facility_id'] == facility_id]
        latest_record = facility_data.sort_values('reporting_date').iloc[-1]
        
        # Main facility row
        main_row = html.Tr([
            html.Td([
                html.Button(
                    "▼",
                    id={"type": "expand-btn", "index": facility_id},
                    className="expand-button",
                    style={"border": "none", "background": "none", "cursor": "pointer"}
                )
            ]),
            html.Td(facility_id),
            html.Td(latest_record['obligor_name']),
            html.Td(latest_record['obligor_rating']),
            html.Td(f"${latest_record['balance']:,.0f}"),
            html.Td(latest_record['origination_date']),
            html.Td(latest_record['maturity_date'])
        ], id={"type": "facility-row", "index": facility_id})
        
        # Expandable content (initially hidden)
        expanded_content = html.Tr([
            html.Td(colSpan=7, children=[
                html.Div(id={"type": "expanded-content", "index": facility_id}, 
                        style={"display": "none"})
            ])
        ])
        
        table_rows.extend([main_row, expanded_content])
    
    # Create table
    table = html.Table([
        html.Thead([
            html.Tr([
                html.Th(""),
                html.Th("Facility ID"),
                html.Th("Obligor Name"),
                html.Th("Rating"),
                html.Th("Balance"),
                html.Th("Origination"),
                html.Th("Maturity")
            ])
        ]),
        html.Tbody(table_rows)
    ], className="table holdings-table")
    
    return html.Div([
        html.Div([
            table
        ], style={"overflowX": "auto", "width": "100%", "height": "calc(100vh - 250px)", "overflowY": "auto"})
    ], className="table-container")


def create_time_series_table(facility_data, facilities_df):
    """Create time series table for expanded facility details"""
    facility_id = facility_data['facility_id']
    
    # Get all records for this facility
    fac_history = facilities_df[facilities_df['facility_id'] == facility_id].sort_values('reporting_date')
    
    if len(fac_history) == 0:
        return html.Div("No historical data available.")
    
    # Get unique dates and metrics
    dates = fac_history['reporting_date'].unique()
    formatted_dates = [pd.to_datetime(d).strftime('%Y-%m-%d') for d in dates]
    
    metrics = ['obligor_rating', 'balance', 'ltv', 'dscr']
    
    # Create table rows for each metric
    table_rows = []
    for metric in metrics:
        if metric in fac_history.columns:
            metric_values = []
            for date in dates:
                date_data = fac_history[fac_history['reporting_date'] == date]
                if len(date_data) > 0:
                    value = date_data[metric].iloc[0]
                    if metric == 'balance':
                        formatted_value = f"${value:,.0f}" if pd.notna(value) else "N/A"
                    elif metric in ['ltv', 'dscr']:
                        formatted_value = f"{value:.2f}" if pd.notna(value) else "N/A"
                    else:
                        formatted_value = str(value) if pd.notna(value) else "N/A"
                    metric_values.append(formatted_value)
                else:
                    metric_values.append("N/A")
            
            # Create row for this metric
            row = html.Tr([
                html.Td(metric.replace('_', ' ').title(), style={"fontWeight": "bold", "width": "150px"})
            ] + [html.Td(val, style={"width": "120px"}) for val in metric_values])
            table_rows.append(row)
    
    # Create header row
    header_row = html.Tr([
        html.Th("Metric", style={"width": "150px"})
    ] + [html.Th(date, style={"width": "120px"}) for date in formatted_dates])
    
    # Calculate table width based on number of columns
    table_width = 150 + (len(formatted_dates) * 120)
    
    time_series_table = html.Table([
        html.Thead([header_row]),
        html.Tbody(table_rows)
    ], className="table time-series-table", style={
        "fontSize": "11px",
        "width": f"{table_width}px",
        "minWidth": f"{table_width}px",
        "tableLayout": "fixed"
    })
    
    return html.Div([
        html.Div([
            time_series_table
        ], style={"overflowX": "auto", "width": "100%"})
    ], style={"padding": "10px", "backgroundColor": "#f8f9fa"})