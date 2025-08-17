from dash import html, dcc, dash_table
import pandas as pd


def create_financial_trend_sidebar(selected_portfolio):
    """Create sidebar for Financial Trend tab with test.py styling"""
    return html.Div([
        html.Div([
            html.H2("Financial Trend", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700"),
        html.Div([
            # View filter matching test.py
            html.Div([
                html.Label("View", className="text-xs font-medium text-ink-600 dark:text-slate-400 mb-1 block"),
                dcc.Dropdown(
                    id='ft-details-view-dropdown',
                    options=[
                        {'label': "Moody's Industry", 'value': 'moodys_industry'},
                        {'label': 'LOB', 'value': 'lob'},
                        {'label': 'Individual Deals', 'value': 'individual'}
                    ],
                    value='individual',
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-4"),
            
            # Time period filters
            html.Div([
                html.Label("Primary Period", className="text-xs font-medium text-ink-600 dark:text-slate-400 mb-1 block"),
                dcc.Dropdown(
                    id='ft-details-primary-period',
                    options=[
                        {'label': 'Current Quarter', 'value': 'current'},
                        {'label': 'Previous Quarter', 'value': 'previous'},
                        {'label': 'Year to Date', 'value': 'ytd'}
                    ],
                    value='current',
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-4"),
            
            html.Div([
                html.Label("Comparison Period", className="text-xs font-medium text-ink-600 dark:text-slate-400 mb-1 block"),
                dcc.Dropdown(
                    id='ft-details-comparison-period',
                    options=[
                        {'label': 'Prior Year', 'value': 'prior_year'},
                        {'label': 'Prior Quarter', 'value': 'prior_quarter'},
                        {'label': 'Year-Start vs Year-End', 'value': 'year_comparison'}
                    ],
                    value='prior_year',
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-4"),
            
            # Financial type filter
            html.Div([
                html.Label("Financial Type", className="text-xs font-medium text-ink-600 dark:text-slate-400 mb-1 block"),
                dcc.Dropdown(
                    id='ft-details-financial-type',
                    options=[
                        {'label': 'Monthly', 'value': 'monthly'},
                        {'label': 'Quarterly', 'value': 'quarterly'},
                        {'label': 'Annual', 'value': 'annual'}
                    ],
                    value='quarterly',
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-4"),
        ], className="p-4")
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden")


def create_financial_trend_content(selected_portfolio):
    """Create Financial Trend content with test.py table styling"""
    return html.Div([
        # Main card with table following test.py pattern
        html.Div([
            # Card header matching test.py
            html.Div([
                html.Div([
                    html.H3("Financial Trend Details (DL)", className="text-sm font-semibold text-ink-700 dark:text-slate-300"),
                    html.Div("Individual Deal Level Financial Comparison", className="text-xs text-ink-500 dark:text-slate-400")
                ], className="flex-1"),
                html.Div("Filters are illustrative only", className="text-xs text-ink-500 dark:text-slate-400")
            ], className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-ink-700"),
            
            # Table container with horizontal scroll
            html.Div([
                html.Div(id='financial-trend-details-table')
            ], className="overflow-x-auto"),
            
            # Footer matching test.py
            html.Div([
                html.Div("1 of 124", className="text-xs text-ink-600 dark:text-slate-400"),
                html.Div("100 per page", className="text-xs text-ink-600 dark:text-slate-400")
            ], className="flex justify-between items-center p-3 border-t border-slate-200 dark:border-ink-700 bg-white dark:bg-ink-800")
            
        ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden")
        
    ], className="main-content")


def create_financial_trend_details_table(facilities_df, view_type=None, primary_period=None, comparison_period=None, financial_type=None):
    """Create Financial Trend Details table based on filters using actual dataset"""
    
    if facilities_df.empty:
        return "No data available"
    
    # Get all data for time series comparison
    df = facilities_df.copy()
    
    # Sort by reporting date to get time series data
    df = df.sort_values(['facility_id', 'reporting_date'])
    
    # Get unique reporting dates
    unique_dates = sorted(df['reporting_date'].unique())
    
    if len(unique_dates) < 2:
        # If we don't have enough time periods, just show current data
        details_data = df.groupby('facility_id').last().reset_index()
    else:
        # Get current period (latest) and prior period data
        current_date = unique_dates[-1]
        prior_date = unique_dates[-2] if len(unique_dates) >= 2 else unique_dates[-1]
        
        current_data = df[df['reporting_date'] == current_date].set_index('facility_id')
        prior_data = df[df['reporting_date'] == prior_date].set_index('facility_id')
        
        # Merge current and prior data
        details_list = []
        for facility_id in current_data.index:
            current_row = current_data.loc[facility_id]
            prior_row = prior_data.loc[facility_id] if facility_id in prior_data.index else current_row
            
            # Calculate changes for available metrics
            balance_change = ((current_row.get('balance', 0) - prior_row.get('balance', 0)) / prior_row.get('balance', 1)) if prior_row.get('balance', 0) != 0 else 0
            
            details_list.append({
                'facility_id': facility_id,
                'obligor_name': current_row.get('obligor_name', ''),
                'lob': current_row.get('lob', ''),
                'industry': current_row.get('industry', ''),
                'cre_property_type': current_row.get('cre_property_type', ''),
                'obligor_rating': current_row.get('obligor_rating', ''),
                'balance_current': current_row.get('balance', 0),
                'balance_prior': prior_row.get('balance', 0),
                'balance_change': balance_change,
                'origination_date': current_row.get('origination_date', ''),
                'maturity_date': current_row.get('maturity_date', ''),
                'reporting_date': current_row.get('reporting_date', ''),
                # Corporate Banking specific metrics
                'free_cash_flow': current_row.get('free_cash_flow', None),
                'fixed_charge_coverage': current_row.get('fixed_charge_coverage', None),
                'cash_flow_leverage': current_row.get('cash_flow_leverage', None),
                'liquidity': current_row.get('liquidity', None),
                'profitability': current_row.get('profitability', None),
                'growth': current_row.get('growth', None),
                # CRE specific metrics
                'noi': current_row.get('noi', None),
                'property_value': current_row.get('property_value', None),
                'dscr': current_row.get('dscr', None),
                'ltv': current_row.get('ltv', None),
                'sir': current_row.get('sir', None),
            })
        
        details_data = pd.DataFrame(details_list)
    
    # Apply view filter
    if view_type == 'lob':
        # Group by LOB if requested
        pass  # Show all data grouped by LOB
    elif view_type == 'moodys_industry':
        # Group by industry if requested
        pass  # Show all data grouped by industry
    # For 'individual', show all individual deals
    
    # Define columns based on actual dataset
    columns = [
        {"name": "Facility ID", "id": "facility_id"},
        {"name": "Obligor Name", "id": "obligor_name"},
        {"name": "LOB", "id": "lob"},
        {"name": "Industry", "id": "industry"},
        {"name": "Property Type", "id": "cre_property_type"},
        {"name": "Rating", "id": "obligor_rating", "type": "numeric"},
        {"name": "Current Balance", "id": "balance_current", "type": "numeric", 
         "format": {"specifier": "$,.0f"}},
        {"name": "Prior Balance", "id": "balance_prior", "type": "numeric",
         "format": {"specifier": "$,.0f"}},
        {"name": "Balance Change %", "id": "balance_change", "type": "numeric", 
         "format": {"specifier": "+.1%"}},
        {"name": "Origination Date", "id": "origination_date"},
        {"name": "Maturity Date", "id": "maturity_date"},
        {"name": "Free Cash Flow", "id": "free_cash_flow", "type": "numeric", 
         "format": {"specifier": ".2f"}},
        {"name": "Fixed Charge Coverage", "id": "fixed_charge_coverage", "type": "numeric", 
         "format": {"specifier": ".2f"}},
        {"name": "Cash Flow Leverage", "id": "cash_flow_leverage", "type": "numeric", 
         "format": {"specifier": ".2f"}},
        {"name": "Liquidity", "id": "liquidity", "type": "numeric", 
         "format": {"specifier": ".2f"}},
        {"name": "Profitability", "id": "profitability", "type": "numeric", 
         "format": {"specifier": ".3f"}},
        {"name": "Growth", "id": "growth", "type": "numeric", 
         "format": {"specifier": ".3f"}},
        {"name": "NOI", "id": "noi", "type": "numeric", 
         "format": {"specifier": "$,.0f"}},
        {"name": "Property Value", "id": "property_value", "type": "numeric", 
         "format": {"specifier": "$,.0f"}},
        {"name": "DSCR", "id": "dscr", "type": "numeric", 
         "format": {"specifier": ".2f"}},
        {"name": "LTV", "id": "ltv", "type": "numeric", 
         "format": {"specifier": ".2f"}},
        {"name": "SIR", "id": "sir", "type": "numeric", 
         "format": {"specifier": "$,.0f"}},
    ]
    
    # Create DataTable with styling
    table = dash_table.DataTable(
        data=details_data.to_dict('records'),
        columns=columns,
        page_size=25,
        fixed_rows={'headers': True},
        style_table={
            'overflowX': 'auto',
            'minWidth': '1200px',
            'width': '100%'
        },
        style_header={
            'backgroundColor': '#f8fafc',
            'borderBottom': '1px solid #e6ebf2',
            'fontWeight': 600,
            'textAlign': 'left',
            'padding': '10px 12px',
            'position': 'sticky',
            'top': 0,
            'color': '#475569',
            'fontFamily': 'Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif',
            'fontSize': 13
        },
        style_cell={
            'padding': '10px 12px',
            'whiteSpace': 'nowrap',
            'borderBottom': '1px solid #f1f5f9',
            'fontFamily': 'Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif',
            'fontSize': 13,
            'textAlign': 'left'
        },
        style_data_conditional=[
            # Positive balance changes in green
            {'if': {'filter_query': '{balance_change} > 0', 'column_id': 'balance_change'}, 
             'color': '#0f9d58'},
            {'if': {'filter_query': '{growth} > 0', 'column_id': 'growth'}, 
             'color': '#0f9d58'},
            {'if': {'filter_query': '{profitability} > 0', 'column_id': 'profitability'}, 
             'color': '#0f9d58'},
            
            # Negative changes in red
            {'if': {'filter_query': '{balance_change} < 0', 'column_id': 'balance_change'}, 
             'color': '#d93025'},
            {'if': {'filter_query': '{growth} < 0', 'column_id': 'growth'}, 
             'color': '#d93025'},
            {'if': {'filter_query': '{profitability} < 0', 'column_id': 'profitability'}, 
             'color': '#d93025'},
            
            # High risk ratings (>12) in red
            {'if': {'filter_query': '{obligor_rating} > 12', 'column_id': 'obligor_rating'}, 
             'color': '#d93025'},
            
            # Default ratings (17) in red with bold
            {'if': {'filter_query': '{obligor_rating} = 17', 'column_id': 'obligor_rating'}, 
             'color': '#d93025', 'fontWeight': 'bold'},
        ],
        filter_action='native',
        sort_action='native',
        style_as_list_view=True,
    )
    
    return table