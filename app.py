#!/usr/bin/env python3
"""
Portfolio Performance Dashboard

A comprehensive portfolio performance dashboard for Corporate Banking and Commercial Real Estate 
portfolios built with Dash and Python. Features custom metrics, user profiles, and interactive 
visualizations for portfolio analysis.

Author: Portfolio Management Team
Version: 1.0
Dependencies: dash, pandas, numpy, plotly
"""

import dash
from dash import dcc, html, Input, Output, callback, State, no_update, callback_context, MATCH
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')
from dash import dash_table
from dash.dependencies import ALL
import math
import re
import json
import os
from threading import Timer
from sqlalchemy import create_engine
from datatidy import DataTidy
import yaml
import config
from modules.auth import user_management
from modules.layout.components import create_layout, create_role_based_navigation, get_tab_button_classes, get_app_index_string
from modules.data.loader import auto_save_data, load_facilities_data
from modules.portfolio.management import get_current_user_portfolios, create_portfolio_sidebar, save_portfolio_data, delete_portfolio_data
from modules.portfolio_summary.components import create_main_content, create_positions_panel
from modules.holdings.components import create_holdings_sidebar, create_holdings_filters, create_holdings_content, create_holdings_table, create_time_series_table
from modules.vintage.components import create_vintage_analysis_sidebar, create_vintage_analysis_content, create_quarterly_cohort_chart
from modules.portfolio_trend.components import create_portfolio_trend_sidebar, get_portfolio_metrics, create_portfolio_trend_content, create_portfolio_trends_charts
from modules.sir_analysis.components import create_sir_analysis_sidebar, create_sir_analysis_content
from modules.location_analysis.components import create_location_analysis_sidebar, create_location_analysis_content
from modules.financial_projection.components import create_financial_projection_sidebar, create_financial_projection_content
from modules.model_backtesting.components import create_model_backtesting_sidebar, create_model_backtesting_content
from modules.financial_trend.components import create_financial_trend_sidebar, create_financial_trend_content, create_financial_trend_details_table

# ================================================================================================
# GLOBAL VARIABLES
# ================================================================================================

# Store custom metric formulas defined by users
custom_metrics = {}

# ================================================================================================
# UTILITY FUNCTIONS
# ================================================================================================

def get_filtered_data(portfolio_name, portfolios, latest_facilities):
    """
    Filter facility data based on portfolio criteria.
    
    This is the core data filtering function that applies portfolio-specific
    criteria to the facilities dataset. Supports filtering by:
    - Line of Business (LOB): Corporate Banking or CRE
    - Industry (for Corporate Banking portfolios)
    - Property Type (for CRE portfolios)
    - Specific obligors/borrowers
    
    Args:
        portfolio_name (str): Name of the portfolio to filter for
        portfolios (dict): Dictionary containing portfolio definitions and criteria
        latest_facilities (pd.DataFrame): DataFrame with latest facility data
        
    Returns:
        pd.DataFrame: Filtered facility data matching portfolio criteria
    """
    print(f"DEBUG get_filtered_data: called for portfolio '{portfolio_name}'")
    print(f"DEBUG get_filtered_data: available portfolios: {list(portfolios.keys())}")
    
    if portfolio_name not in portfolios:
        print(f"DEBUG get_filtered_data: portfolio '{portfolio_name}' not found in portfolios")
        return pd.DataFrame()
    
    portfolio_criteria = portfolios[portfolio_name]
    print(f"DEBUG get_filtered_data: portfolio criteria: {portfolio_criteria}")
    
    filtered_data = latest_facilities.copy()
    print(f"DEBUG get_filtered_data: starting with {len(filtered_data)} facilities")
    
    # Filter by LOB
    if portfolio_criteria['lob']:
        before_count = len(filtered_data)
        filtered_data = filtered_data[filtered_data['lob'] == portfolio_criteria['lob']]
        print(f"DEBUG get_filtered_data: after LOB filter '{portfolio_criteria['lob']}': {len(filtered_data)} facilities (was {before_count})")
    
    # Filter by industry (for Corporate Banking)
    if portfolio_criteria['lob'] == 'Corporate Banking' and portfolio_criteria['industry']:
        if isinstance(portfolio_criteria['industry'], list):
            industry_series = pd.Series(filtered_data['industry'])
            filtered_data = filtered_data[industry_series.astype(str).isin([str(i) for i in portfolio_criteria['industry']])]
        else:
            filtered_data = filtered_data[filtered_data['industry'] == portfolio_criteria['industry']]
    
    # Filter by property type (for CRE)
    if portfolio_criteria['lob'] == 'CRE' and portfolio_criteria['property_type']:
        if isinstance(portfolio_criteria['property_type'], list):
            property_series = pd.Series(filtered_data['cre_property_type'])
            filtered_data = filtered_data[property_series.astype(str).isin([str(i) for i in portfolio_criteria['property_type']])]
        else:
            filtered_data = filtered_data[filtered_data['cre_property_type'] == portfolio_criteria['property_type']]
    
    # Filter by obligors (alternative to industry/property type)
    if portfolio_criteria.get('obligors'):
        if isinstance(portfolio_criteria['obligors'], list):
            obligor_series = pd.Series(filtered_data['obligor_name'])
            filtered_data = filtered_data[obligor_series.astype(str).isin([str(i) for i in portfolio_criteria['obligors']])]
        else:
            filtered_data = filtered_data[filtered_data['obligor_name'] == portfolio_criteria['obligors']]
    
    print(f"DEBUG get_filtered_data: final result: {len(filtered_data)} facilities")
    return filtered_data


# ================================================================================================
# DATA INITIALIZATION
# ================================================================================================

# Initialize user profiles and start auto-save timer for data persistence
user_profiles = user_management.load_profiles()
auto_save_data(custom_metrics)  # Start 15-second auto-save timer

# Load data using integrated DataTidy pipeline
try:
    print("=== Bank Risk Dashboard - Integrated DataTidy Processing ===")
    
    # Load facilities data directly with integrated processing
    facilities_df = load_facilities_data()
    
    # Get latest data for each facility (most recent reporting date)
    latest_facilities = facilities_df.sort_values('reporting_date').groupby('facility_id').tail(1)
    
    # Store portfolios in session (use default portfolios constant)
    portfolios = config.DEFAULT_PORTFOLIOS.copy()
    available_portfolios = list(portfolios.keys())
    default_portfolio = available_portfolios[0] if len(available_portfolios) > 0 else 'Corporate Banking Portfolio'
    
    print(f"✓ Loaded {len(facilities_df)} facility records")
    print(f"✓ Integrated pipeline: Database -> DataTidy -> DataFrame -> Dashboard")
    
except Exception as e:
    print(f"✗ Data loading failed: {e}")
    print("Please run db_data_generator.py to create database and DataTidy config.")
    # Create dummy data for testing
    facilities_df = pd.DataFrame({
        'facility_id': ['F001', 'F002', 'F003'],
        'obligor_name': ['Test Company 1', 'Test Company 2', 'Test Company 3'],
        'obligor_rating': [5, 8, 12],
        'balance': [1000000, 2000000, 3000000],
        'lob': ['Corporate Banking', 'CRE', 'Corporate Banking'],
        'industry': ['Technology', None, 'Healthcare'],
        'cre_property_type': [None, 'Office', None],
        'reporting_date': ['2024-01-01', '2024-01-01', '2024-01-01']
    })
    latest_facilities = facilities_df
    portfolios = {'Corporate Banking': {'lob': 'Corporate Banking', 'industry': None, 'property_type': None}}
    available_portfolios = list(portfolios.keys())
    default_portfolio = 'Corporate Banking'

# ================================================================================================
# DASH APP INITIALIZATION
# ================================================================================================

# Initialize Dash app with modern styling and asset support
app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder='assets')
server = app.server  # Flask server reference for deployment

# Apply custom HTML template with Tailwind CSS and dark mode support
app.index_string = get_app_index_string()


# ================================================================================================
# TAB NAVIGATION CALLBACKS
# ================================================================================================

@callback(
    [Output('tab-content-container', 'children'),
     Output('tab-portfolio-summary', 'className'),
     Output('tab-holdings', 'className'),
     Output('tab-financial-trends', 'className'),
     Output('tab-financial-trend-details', 'className'),
     Output('tab-vintage-analysis', 'className'),
     Output('tab-sir-analysis', 'className'),
     Output('tab-location-analysis', 'className'),
     Output('tab-financial-projection', 'className'),
     Output('tab-model-backtesting', 'className')],
    [Input('tab-portfolio-summary', 'n_clicks'),
     Input('tab-holdings', 'n_clicks'),
     Input('tab-financial-trends', 'n_clicks'),
     Input('tab-financial-trend-details', 'n_clicks'),
     Input('tab-vintage-analysis', 'n_clicks'),
     Input('tab-sir-analysis', 'n_clicks'),
     Input('tab-location-analysis', 'n_clicks'),
     Input('tab-financial-projection', 'n_clicks'),
     Input('tab-model-backtesting', 'n_clicks')],
    prevent_initial_call=False
)
def update_tab_content(summary_clicks, holdings_clicks, trends_clicks, details_clicks, vintage_clicks, sir_clicks, location_clicks, projection_clicks, backtesting_clicks):
    """
    Handle main tab navigation and content switching.
    
    This is the primary navigation callback that manages switching between
    different analysis views (Portfolio Summary, Holdings, Financial Trends, etc.)
    and updates both the content area and visual state of tab buttons.
    
    Returns:
        tuple: (content_div, tab_button_classes...) for each tab
    """
    ctx = callback_context
    if not ctx.triggered:
        active_tab = 'portfolio-summary'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        active_tab = button_id.replace('tab-', '')
    
    # Define button classes
    active_class = "px-3 py-1.5 rounded bg-ink-900 text-white"
    inactive_class = "px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700"
    
    # Set classes for all buttons
    summary_class = active_class if active_tab == 'portfolio-summary' else inactive_class
    holdings_class = active_class if active_tab == 'holdings' else inactive_class
    trends_class = active_class if active_tab == 'financial-trends' else inactive_class
    details_class = active_class if active_tab == 'financial-trend-details' else inactive_class
    vintage_class = active_class if active_tab == 'vintage-analysis' else inactive_class
    sir_class = active_class if active_tab == 'sir-analysis' else inactive_class
    location_class = active_class if active_tab == 'location-analysis' else inactive_class
    projection_class = active_class if active_tab == 'financial-projection' else inactive_class
    backtesting_class = active_class if active_tab == 'model-backtesting' else inactive_class
    
    selected_portfolio = default_portfolio
        
    if active_tab == 'portfolio-summary':
        content = html.Div([
            create_portfolio_sidebar(selected_portfolio, available_portfolios),
            html.Div(id='main-content-container', children=create_main_content(selected_portfolio, lambda p: get_filtered_data(p, portfolios, latest_facilities), facilities_df, portfolios)),
            html.Div(id='positions-panel-container', children=create_positions_panel(selected_portfolio, facilities_df, portfolios, lambda p: get_filtered_data(p, portfolios, latest_facilities)))
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)_340px] gap-4")
    elif active_tab == 'holdings':
        content = html.Div([
            create_holdings_sidebar(selected_portfolio, available_portfolios, portfolios, lambda p: get_filtered_data(p, portfolios, latest_facilities)),
            create_holdings_content(selected_portfolio, lambda p: get_filtered_data(p, portfolios, latest_facilities))
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'financial-trends':
        content = html.Div([
            create_portfolio_trend_sidebar(selected_portfolio, available_portfolios),
            create_portfolio_trend_content(selected_portfolio, custom_metrics, portfolios, facilities_df, lambda p: get_filtered_data(p, portfolios, latest_facilities))
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'financial-trend-details':
        content = html.Div([
            create_financial_trend_sidebar(selected_portfolio),
            create_financial_trend_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'vintage-analysis':
        content = html.Div([
            create_vintage_analysis_sidebar(selected_portfolio, facilities_df, portfolios, default_portfolio),
            create_vintage_analysis_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'sir-analysis':
        content = html.Div([
            create_sir_analysis_sidebar(selected_portfolio, portfolios),
            create_sir_analysis_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'location-analysis':
        content = html.Div([
            create_location_analysis_sidebar(selected_portfolio, portfolios),
            create_location_analysis_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'financial-projection':
        content = html.Div([
            create_financial_projection_sidebar(selected_portfolio, portfolios),
            create_financial_projection_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'model-backtesting':
        content = html.Div([
            create_model_backtesting_sidebar(selected_portfolio, portfolios),
            create_model_backtesting_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    else:
        content = html.Div([
            create_portfolio_sidebar(selected_portfolio, available_portfolios),
            html.Div(id='main-content-container', children=create_main_content(selected_portfolio, lambda p: get_filtered_data(p, portfolios, latest_facilities), facilities_df))
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    
    return content, summary_class, holdings_class, trends_class, details_class, vintage_class, sir_class, location_class, projection_class, backtesting_class

# ================================================================================================
# NAVIGATION AND USER INTERFACE CALLBACKS
# ================================================================================================

@callback(
    Output('navigation-tabs-container', 'children'),
    Input('current-user-store', 'data'),
    prevent_initial_call=True
)
def update_navigation_tabs(stored_user):
    """Update navigation tabs based on user role from store"""
    # Update the current user to match the stored value
    if stored_user:
        user_management.set_current_user(stored_user)
    
    print(f"DEBUG: Navigation update triggered - stored_user: {stored_user}, user_management.get_current_user(): {user_management.get_current_user()}")
    return create_role_based_navigation()

@callback(
    Output('positions-panel-container', 'children'),
    Input('portfolio-dropdown', 'value')
)
def update_positions_panel(selected_portfolio):
    """Update positions panel when portfolio selection changes"""
    print(f"DEBUG: update_positions_panel called with: {selected_portfolio}")
    if selected_portfolio is None:
        selected_portfolio = default_portfolio
    try:
        result = create_positions_panel(selected_portfolio, facilities_df, portfolios, lambda p: get_filtered_data(p, portfolios, latest_facilities))
        print(f"DEBUG: positions panel created successfully for {selected_portfolio}")
        return result
    except Exception as e:
        print(f"ERROR: Failed to create positions panel: {e}")
        return html.Div(f"Error creating positions panel: {str(e)}", className="p-4 text-red-500")
@callback(
    Output('industry-dropdown', 'options'),
    Input('lob-dropdown', 'value'),
    prevent_initial_call=True
)
def update_industry_options(lob_value):
    """Update industry options based on available data"""
    if lob_value == 'Corporate Banking':
        industries = sorted(latest_facilities[latest_facilities['lob'] == 'Corporate Banking']['industry'].unique())
        return [{'label': industry, 'value': industry} for industry in industries if pd.notna(industry)]
    return []

@callback(
    Output('property-type-dropdown', 'options'),
    Input('lob-dropdown', 'value'),
    prevent_initial_call=True
)
def update_property_type_options(lob_value):
    """Update property type options based on available data"""
    if lob_value == 'CRE':
        property_types = sorted(latest_facilities[latest_facilities['lob'] == 'CRE']['cre_property_type'].unique())
        return [{'label': pt, 'value': pt} for pt in property_types if pd.notna(pt)]
    return []

@callback(
    Output('obligor-dropdown', 'options'),
    Input('portfolio-dropdown', 'value')
)
def update_obligor_options(selected_portfolio):
    """Update obligor options with obligors from selected portfolio - same as Holdings"""
    if not selected_portfolio or selected_portfolio not in portfolios:
        # Return empty list if no portfolio selected
        return []
    
    portfolio_data = get_filtered_data(selected_portfolio, portfolios, latest_facilities)
    if len(portfolio_data) == 0:
        return []
        
    obligor_options = sorted(portfolio_data['obligor_name'].unique())
    return [{'label': obligor, 'value': obligor} for obligor in obligor_options if pd.notna(obligor)]

@callback(
    Output('industry-group', 'style'),
    Output('property-type-group', 'style'),
    Input('lob-dropdown', 'value'),
    prevent_initial_call=True
)
def update_form_visibility(lob_value):
    """Show/hide form groups based on LOB selection"""
    if lob_value == 'Corporate Banking':
        return {'display': 'block'}, {'display': 'none'}
    elif lob_value == 'CRE':
        return {'display': 'none'}, {'display': 'block'}
    else:
        return {'display': 'none'}, {'display': 'none'}

@callback(
    Output('portfolio-dropdown', 'options', allow_duplicate=True),
    Output('portfolio-dropdown', 'value', allow_duplicate=True),
    Output('delete-portfolio-dropdown', 'options', allow_duplicate=True),
    Input('save-portfolio-btn', 'n_clicks'),
    State('portfolio-name-input', 'value'),
    State('lob-dropdown', 'value'),
    State('industry-dropdown', 'value'),
    State('property-type-dropdown', 'value'),
    State('obligor-dropdown', 'value'),
    prevent_initial_call=True
)
def save_portfolio(n_clicks, portfolio_name, lob_value, industry_value, property_type_value, obligor_value):
    """Save new portfolio and update dropdown"""
    global portfolios, available_portfolios
    
    if n_clicks and portfolio_name and (lob_value or obligor_value):
        # Add new portfolio
        portfolios[portfolio_name] = {
            'lob': lob_value,
            'industry': industry_value,
            'property_type': property_type_value,
            'obligors': obligor_value
        }
        
        # Update global portfolios
        portfolios = portfolios
        available_portfolios = list(portfolios.keys())
        
        # Update dropdown options
        portfolio_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios]
        delete_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios if portfolio not in ['Corporate Banking', 'CRE']]
        
        return portfolio_options, portfolio_name, delete_options
    
    # Return current options if no save action
    portfolio_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios]
    delete_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios if portfolio not in ['Corporate Banking', 'CRE']]
    return portfolio_options, no_update, delete_options

@callback(
    Output('portfolio-dropdown', 'options', allow_duplicate=True),
    Output('portfolio-dropdown', 'value', allow_duplicate=True),
    Output('delete-portfolio-dropdown', 'options', allow_duplicate=True),
    Input('delete-portfolio-btn', 'n_clicks'),
    State('delete-portfolio-dropdown', 'value'),
    prevent_initial_call=True
)
def delete_portfolio(n_clicks, portfolio_to_delete):
    """Delete portfolio and update dropdowns"""
    global portfolios, available_portfolios
    
    if n_clicks and portfolio_to_delete and portfolios and portfolio_to_delete in portfolios:
        # Prevent deletion of default portfolios
        if portfolio_to_delete in ['Corporate Banking', 'CRE']:
            # Return current options without changes
            portfolio_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios]
            delete_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios if portfolio not in ['Corporate Banking', 'CRE']]
            return portfolio_options, no_update, delete_options
        
        # Remove portfolio
        del portfolios[portfolio_to_delete]
        
        # Update global portfolios
        portfolios = portfolios
        available_portfolios = list(portfolios.keys())
        
        # Update dropdown options
        portfolio_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios]
        delete_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios if portfolio not in ['Corporate Banking', 'CRE']]
        
        # If deleted portfolio was selected, switch to first available
        new_selection = available_portfolios[0] if available_portfolios else None
        
        return portfolio_options, new_selection, delete_options
    
    # Return current options if no delete action
    portfolio_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios]
    delete_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios if portfolio not in ['Corporate Banking', 'CRE']]
    return portfolio_options, no_update, delete_options

# ================================================================================================
# PORTFOLIO SUMMARY TAB CALLBACKS
# ================================================================================================

@callback(
    Output('main-content-container', 'children'),
    Input('portfolio-dropdown', 'value'),
    prevent_initial_call=True
)
def update_main_content(selected_portfolio):
    if selected_portfolio is None:
        selected_portfolio = default_portfolio
    return create_main_content(selected_portfolio, lambda p: get_filtered_data(p, portfolios, latest_facilities), facilities_df)

# ================================================================================================
# FINANCIAL TRENDS TAB CALLBACKS
# ================================================================================================

@callback(
    Output('financial-trends-chart-1', 'figure'),
    Output('financial-trends-chart-2', 'figure'),
    Output('financial-trends-chart-3', 'figure'),
    Input('portfolio-dropdown', 'value'),
    Input('financial-trends-benchmark-dropdown', 'value'),
    Input('financial-trends-metric-dropdown-1', 'value'),
    Input('financial-trends-metric-dropdown-2', 'value'),
    Input('financial-trends-metric-dropdown-3', 'value'),
    Input('financial-trends-agg-dropdown-1', 'value'),
    Input('financial-trends-agg-dropdown-2', 'value'),
    Input('financial-trends-agg-dropdown-3', 'value')
)
def update_financial_trends_charts(selected_portfolio, benchmark_portfolio, metric1, metric2, metric3, agg1, agg2, agg3):
    """Wrapper function to call the new modular charts"""
    return create_portfolio_trends_charts(facilities_df, portfolios, selected_portfolio, benchmark_portfolio, metric1, metric2, metric3, agg1, agg2, agg3)
    # Helper to get time series for a portfolio and metric
    def get_timeseries(portfolio_name, metric, agg_method='avg'):
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
    # Build chart for a metric
    def build_chart(metric, chart_id, agg_method='avg'):
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
            
        ts_main = get_timeseries(selected_portfolio, metric, agg_method)
        ts_bench = get_timeseries(benchmark_portfolio, metric, agg_method) if benchmark_portfolio else None
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
            height=350,  # Reduced height to fit container properly
            margin=dict(l=40, r=20, t=20, b=100),  # Adjusted margins for better fit
            font=dict(size=12, color='#1f2937'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            autosize=True,  # Enable autosize for responsiveness
            xaxis=dict(
                rangeslider=dict(
                    visible=True,
                    thickness=0.15,  # Increased thickness for better visibility
                    bgcolor='#f8fafc',  # Light background color
                    bordercolor='#e5e7eb',  # Border color
                    borderwidth=1
                ),
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1Y", step="year", stepmode="backward"),
                        dict(count=2, label="2Y", step="year", stepmode="backward"),
                        dict(count=5, label="5Y", step="year", stepmode="backward"),
                        dict(step="all", label="All")
                    ]),
                    bgcolor='#ffffff',
                    bordercolor='#e5e7eb',
                    borderwidth=1,
                    font=dict(color='#374151', size=10)
                ),
                type='date'
            )
        )
        fig.update_yaxes(title_text=metric.upper() if metric else "")
        if not ts_main.empty or (ts_bench is not None and not ts_bench.empty):
            return fig
        # If no data, show placeholder
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    return (build_chart(metric1, 'financial-trends-chart-1', agg1 or 'avg'), 
            build_chart(metric2, 'financial-trends-chart-2', agg2 or 'avg'), 
            build_chart(metric3, 'financial-trends-chart-3', agg3 or 'avg'))

# Callback to update metric dropdowns based on portfolio selection
@callback(
    Output('financial-trends-metric-dropdown-1', 'options'),
    Output('financial-trends-metric-dropdown-2', 'options'),
    Output('financial-trends-metric-dropdown-3', 'options'),
    Output('financial-trends-metric-dropdown-1', 'value'),
    Output('financial-trends-metric-dropdown-2', 'value'),
    Output('financial-trends-metric-dropdown-3', 'value'),
    Input('portfolio-dropdown', 'value'),
    prevent_initial_call=True
)
def update_metric_options(selected_portfolio):
    """Update metric options based on selected portfolio type"""
    metrics_options = get_portfolio_metrics(selected_portfolio, custom_metrics, portfolios, facilities_df)
    default_metric_1 = metrics_options[0]['value'] if metrics_options else 'balance'
    default_metric_2 = metrics_options[1]['value'] if len(metrics_options) > 1 else 'balance'
    default_metric_3 = metrics_options[2]['value'] if len(metrics_options) > 2 else 'balance'
    
    return metrics_options, metrics_options, metrics_options, default_metric_1, default_metric_2, default_metric_3

# Financial Trend Details callbacks
@callback(
    Output('financial-trend-details-table', 'children'),
    [Input('ft-details-view-dropdown', 'value'),
     Input('ft-details-primary-period', 'value'),
     Input('ft-details-comparison-period', 'value'),
     Input('ft-details-financial-type', 'value')],
    prevent_initial_call=True
)
def update_financial_trend_details_table(view_type, primary_period, comparison_period, financial_type):
    """Update the Financial Trend Details table based on filters using actual dataset"""
    return create_financial_trend_details_table(facilities_df, view_type, primary_period, comparison_period, financial_type)

# Holdings tab callbacks
@callback(
    Output({"type": "expanded-content", "index": MATCH}, "children"),
    Output({"type": "expanded-content", "index": MATCH}, "style"),
    Output({"type": "expand-btn", "index": MATCH}, "children"),
    Input({"type": "expand-btn", "index": MATCH}, "n_clicks"),
    State({"type": "expanded-content", "index": MATCH}, "style"),
    State("portfolio-dropdown", "value"),
    prevent_initial_call=True
)
def toggle_facility_expansion(n_clicks, current_style, selected_portfolio):
    """Toggle facility expansion and create time series table"""
    if n_clicks is None:
        return [], {"display": "none"}, "▼"
    
    # Get facility ID from callback context
    facility_id = callback_context.triggered[0]["prop_id"].split('"index":"')[1].split('"')[0]
    
    # Toggle display
    if current_style and current_style.get("display") == "block":
        return [], {"display": "none"}, "▼"
    
    # Get ALL facility data (not just latest) for time series
    if selected_portfolio and selected_portfolio in portfolios:
        portfolio_criteria = portfolios[selected_portfolio]
        facility_data = facilities_df.copy()
        
        # Apply portfolio filters
        if portfolio_criteria['lob']:
            facility_data = facility_data[facility_data['lob'] == portfolio_criteria['lob']]
        if portfolio_criteria['lob'] == 'Corporate Banking' and portfolio_criteria['industry']:
            if isinstance(portfolio_criteria['industry'], list):
                facility_data = facility_data[facility_data['industry'].astype(str).isin([str(i) for i in portfolio_criteria['industry']])]
            else:
                facility_data = facility_data[facility_data['industry'] == portfolio_criteria['industry']]
        if portfolio_criteria['lob'] == 'CRE' and portfolio_criteria['property_type']:
            if isinstance(portfolio_criteria['property_type'], list):
                facility_data = facility_data[facility_data['cre_property_type'].astype(str).isin([str(i) for i in portfolio_criteria['property_type']])]
            else:
                facility_data = facility_data[facility_data['cre_property_type'] == portfolio_criteria['property_type']]
        
        # Filter for specific facility and sort by date
        facility_data = facility_data[facility_data['facility_id'] == facility_id].sort_values('reporting_date')
    else:
        facility_data = facilities_df[facilities_df['facility_id'] == facility_id].sort_values('reporting_date')
    
    if len(facility_data) == 0:
        return [html.Div("No data available")], {"display": "block"}, "▲"
    
    # Get available metrics for this portfolio
    metrics = get_portfolio_metrics(selected_portfolio, custom_metrics, portfolios, facilities_df)
    
    # Create time series table using the modular function
    time_series_table = create_time_series_table(facility_data.iloc[0], facilities_df)
    
    return [html.Div([
        html.H5(f"Time Series for {facility_id}", style={"marginBottom": "10px"}),
        time_series_table
    ], style={"padding": "10px", "backgroundColor": "#f8f9fa", "border": "1px solid #dee2e6", "position": "relative"})], {"display": "block"}, "▲"

# Holdings filters update callback
@callback(
    Output('holdings-filters-container', 'children'),
    Input('portfolio-dropdown', 'value'),
    prevent_initial_call=True
)
def update_holdings_filters(selected_portfolio):
    """Update Holdings filters when portfolio selection changes"""
    if selected_portfolio is None:
        selected_portfolio = default_portfolio
    return create_holdings_filters(selected_portfolio, portfolios, lambda p: get_filtered_data(p, portfolios, latest_facilities))

# Holdings table update callback with filters
@callback(
    Output('holdings-table-container', 'children'),
    Input('portfolio-dropdown', 'value'),
    Input('holdings-rating-filter', 'value'),
    Input('holdings-obligor-filter', 'value'),
    Input('holdings-balance-filter', 'value'),
    prevent_initial_call=True
)
def update_holdings_table_main(selected_portfolio, rating_filter, obligor_filter, balance_filter):
    """Update Holdings table when main filters change"""
    if selected_portfolio is None:
        selected_portfolio = default_portfolio
    
    return create_holdings_table(
        get_filtered_data(selected_portfolio, portfolios, latest_facilities), 
        rating_filter, 
        obligor_filter, 
        None,  # industry_filter
        None,  # property_filter
        None,  # msa_filter
        balance_filter
    )

# Additional callbacks for portfolio-specific filters
@callback(
    Output('holdings-table-container', 'children', allow_duplicate=True),
    Input('holdings-industry-filter', 'value'),
    State('portfolio-dropdown', 'value'),
    State('holdings-rating-filter', 'value'),
    State('holdings-obligor-filter', 'value'),
    State('holdings-balance-filter', 'value'),
    prevent_initial_call=True
)
def update_holdings_table_industry(industry_filter, selected_portfolio, rating_filter, obligor_filter, balance_filter):
    """Update Holdings table when industry filter changes"""
    if selected_portfolio is None:
        selected_portfolio = default_portfolio
    
    return create_holdings_table(
        get_filtered_data(selected_portfolio, portfolios, latest_facilities), 
        rating_filter, 
        obligor_filter, 
        industry_filter,
        None,  # property_filter
        None,  # msa_filter
        balance_filter
    )

@callback(
    Output('holdings-table-container', 'children', allow_duplicate=True),
    Input('holdings-property-filter', 'value'),
    Input('holdings-msa-filter', 'value'),
    State('portfolio-dropdown', 'value'),
    State('holdings-rating-filter', 'value'),
    State('holdings-obligor-filter', 'value'),
    State('holdings-balance-filter', 'value'),
    prevent_initial_call=True
)
def update_holdings_table_cre(property_filter, msa_filter, selected_portfolio, rating_filter, obligor_filter, balance_filter):
    """Update Holdings table when CRE-specific filters change"""
    if selected_portfolio is None:
        selected_portfolio = default_portfolio
    
    return create_holdings_table(
        get_filtered_data(selected_portfolio, portfolios, latest_facilities), 
        rating_filter, 
        obligor_filter, 
        None,  # industry_filter
        property_filter,
        msa_filter,
        balance_filter
    )

# Custom metric creation callback
@callback(
    Output('metric-creation-alert', 'children'),
    Output('financial-trends-metric-dropdown-1', 'options', allow_duplicate=True),
    Output('financial-trends-metric-dropdown-2', 'options', allow_duplicate=True),
    Output('financial-trends-metric-dropdown-3', 'options', allow_duplicate=True),
    Output('custom-metric-formula', 'value'),
    Output('custom-metric-name', 'value'),
    Input('create-metric-btn', 'n_clicks'),
    State('custom-metric-formula', 'value'),
    State('custom-metric-name', 'value'),
    State('portfolio-dropdown', 'value'),
    prevent_initial_call=True
)
def create_custom_metric(n_clicks, formula, metric_name, selected_portfolio):
    global custom_metrics, facilities_df
    
    if n_clicks and formula and metric_name:
        try:
            # Parse and validate the formula - create completely fresh scope
            original_formula = formula  # Keep original for debugging
            formula_cleaned = formula.lower().strip()
            
            # Get available columns for validation
            exclude_cols = ['facility_id', 'obligor_name', 'origination_date', 'maturity_date', 'reporting_date', 'lob', 'industry', 'cre_property_type', 'msa']
            available_cols = [col for col in facilities_df.columns if col not in exclude_cols]
            
            # Enhanced validation - handle backtick syntax for multi-word variables
            import re
            
            # Check for common syntax errors first
            if ' = ' in formula_cleaned and ' == ' not in formula_cleaned:
                alert = html.Div([
                    html.P("⚠️ Error: Use '==' for equality comparison, not '='. Example: (obligor_rating == 14) * 1", 
                           style={"color": "#ef4444", "margin": "0"})
                ], className="alert alert-warning")
                return alert, no_update, no_update, no_update, no_update, no_update
            
            # Extract variables with backticks (e.g., `free cash flow`) - fresh for each call
            backtick_vars = re.findall(r'`([^`]+)`', formula_cleaned)
            
            # Convert backtick variables to underscore format for database lookup - fresh mapping
            backtick_mapping = {}
            if backtick_vars:  # Only process if there are backtick variables
                for var in backtick_vars:
                    underscore_var = var.replace(' ', '_').lower()
                    backtick_mapping[var] = underscore_var
                    # Replace in formula for processing
                    formula_cleaned = formula_cleaned.replace(f'`{var}`', underscore_var)
            
            # Extract regular variable names (letters and underscores), but not within comparison operators
            # First clean up comparison operators and parentheses to avoid false matches
            temp_formula = re.sub(r'[<>=!()]+', ' ', formula_cleaned)
            temp_formula = re.sub(r'[+\-*/]', ' ', temp_formula)  # Remove math operators
            regular_vars = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', temp_formula)
            
            # Combine all variables for validation (only include underscore versions from backticks)
            all_vars = list(backtick_mapping.values()) + [var for var in regular_vars if var not in backtick_mapping.values()]
            
            missing_vars = []
            reserved_words = [
                'and', 'or', 'not', 'if', 'else', 'abs', 'max', 'min', 'sum', 'avg', 'mean',
                'true', 'false', 'int', 'float', 'bool', 'astype'
            ]
            for var in set(all_vars):  # Use set to remove duplicates
                # Skip mathematical operators, Python functions, and comparison results
                if var not in reserved_words and var not in available_cols:
                    missing_vars.append(var)
            
            if missing_vars:
                alert = html.Div([
                    html.P(f"⚠️ Warning: Variables not found in dataset: {', '.join(missing_vars)}", 
                           style={"color": "#ef4444", "margin": "0"})
                ], className="alert alert-warning")
                return alert, no_update, no_update, no_update, no_update, no_update
            
            # Test the formula with sample data using same approach as final calculation
            test_data = facilities_df[available_cols].iloc[0:1].copy()
            
            # Create test formula - use the exact same substitution pattern as final calculation
            test_formula = formula_cleaned
            for col in available_cols:
                if col in test_formula:
                    # Use exact same pattern as bulk calculation
                    test_val = test_data[col].iloc[0] if not test_data[col].empty else 0
                    test_formula = test_formula.replace(col, str(test_val))
            
            # Try to evaluate the formula
            try:
                result = eval(test_formula)
                # Handle different types of results
                if hasattr(result, 'iloc'):  # pandas Series
                    result = result.iloc[0] if len(result) > 0 else 0
                if isinstance(result, (bool, np.bool_)):
                    result = int(result)
                # Check if result is numeric
                if not isinstance(result, (int, float, bool, np.number)) or pd.isna(result):
                    raise ValueError("Formula does not produce a valid numeric result")
            except Exception as e:
                alert = html.Div([
                    html.P(f"⚠️ Error: Invalid formula - {str(e)}", 
                           style={"color": "#ef4444", "margin": "0"})
                ], className="alert alert-warning")
                return alert, no_update, no_update, no_update, no_update, no_update
            
            # Save the custom metric with original formula (not the modified one)
            custom_metrics[metric_name] = formula_cleaned
            
            # Calculate custom metric values for the entire dataset
            # Create a copy for bulk calculation to avoid modifying the stored formula
            bulk_formula = formula_cleaned
            for col in available_cols:
                if col in bulk_formula:
                    bulk_formula = bulk_formula.replace(col, f"facilities_df['{col}']")
            
            try:
                result = eval(bulk_formula)
                # Convert boolean results to integers
                if hasattr(result, 'dtype') and result.dtype == bool:
                    result = result.astype(int)
                facilities_df[metric_name] = result
            except:
                # If bulk calculation fails, calculate row by row
                def calculate_custom_metric(row):
                    # Start with the original formula and apply backtick conversion
                    formula_eval = formula.lower().strip()
                    
                    # Create fresh backtick mapping for this row calculation
                    import re
                    row_backtick_vars = re.findall(r'`([^`]+)`', formula_eval)
                    row_backtick_mapping = {}
                    for var in row_backtick_vars:
                        underscore_var = var.replace(' ', '_').lower()
                        row_backtick_mapping[var] = underscore_var
                    
                    # Handle backtick variables first
                    for original_var, underscore_var in row_backtick_mapping.items():
                        formula_eval = formula_eval.replace(f'`{original_var}`', underscore_var)
                    
                    # Replace column names with actual values
                    for col in available_cols:
                        if col in formula_eval:
                            formula_eval = formula_eval.replace(col, str(row[col]) if pd.notna(row[col]) else '0')
                    try:
                        result = eval(formula_eval)
                        # Convert boolean to int
                        if isinstance(result, bool):
                            return int(result)
                        return result
                    except:
                        return 0
                
                facilities_df[metric_name] = facilities_df.apply(calculate_custom_metric, axis=1)
            
            # Update metric options
            updated_options = get_portfolio_metrics(selected_portfolio, custom_metrics, portfolios, facilities_df)
            
            alert = html.Div([
                html.P(f"✅ Custom metric '{metric_name}' created successfully!", 
                       style={"color": "#10b981", "margin": "0"})
            ], className="alert alert-success")
            
            return alert, updated_options, updated_options, updated_options, '', ''
            
        except Exception as e:
            alert = html.Div([
                html.P(f"⚠️ Error creating metric: {str(e)}", 
                       style={"color": "#ef4444", "margin": "0"})
            ], className="alert alert-warning")
            return alert, no_update, no_update, no_update, no_update, no_update
    
    return no_update, no_update, no_update, no_update, no_update, no_update

# Vintage Analysis callbacks
@callback(
    [Output('vintage-metric-selector', 'style'),
     Output('vintage-metric-dropdown', 'options'),
     Output('vintage-metric-dropdown', 'value')],
    [Input('vintage-analysis-type', 'value'),
     Input('vintage-portfolio-dropdown', 'value')]
)
def update_vintage_metric_selector(analysis_type, portfolio):
    """Show/hide metric selector and populate options based on analysis type"""
    if analysis_type == 'metric_trend':
        # Get metrics from the same function used in financial trends
        metrics_options = get_portfolio_metrics(portfolio, custom_metrics, portfolios, facilities_df)
        default_metric = metrics_options[0]['value'] if metrics_options else None
        return {'display': 'block'}, metrics_options, default_metric
    else:
        return {'display': 'none'}, [], None

@callback(
    Output('vintage-analysis-chart', 'figure'),
    Input('vintage-portfolio-dropdown', 'value'),
    Input('vintage-vintage-quarters', 'value'),
    Input('vintage-analysis-type', 'value'),
    Input('vintage-metric-dropdown', 'value')
)
def update_vintage_analysis_chart(portfolio, selected_quarters, analysis_type, selected_metric):
    """Update vintage analysis chart using Financial Trends pattern"""
    
    def build_vintage_chart():
        if not portfolio or not selected_quarters or not analysis_type:
            # Return empty chart if no parameters specified
            fig = go.Figure()
            fig.update_layout(
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                height=350,
                margin=dict(l=40, r=20, t=20, b=100),
                font=dict(size=12, color='#1f2937'),
                autosize=True
            )
            fig.add_annotation(text="Select quarterly cohorts to view analysis", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Check if metric is required but missing
        if analysis_type == 'metric_trend' and not selected_metric:
            fig = go.Figure()
            fig.update_layout(
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                height=350,
                margin=dict(l=40, r=20, t=20, b=100),
                font=dict(size=12, color='#1f2937'),
                autosize=True
            )
            fig.add_annotation(text="Select a metric to view metric trends", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Get filtered data - use full historical data for vintage analysis
        if portfolio not in portfolios:
            portfolio_data = pd.DataFrame()
        else:
            portfolio_criteria = portfolios[portfolio]
            portfolio_data = facilities_df.copy()  # Use full historical data
            
            # Filter by LOB
            if portfolio_criteria['lob']:
                portfolio_data = portfolio_data[portfolio_data['lob'] == portfolio_criteria['lob']]
            
            # Filter by industry (for Corporate Banking)
            if portfolio_criteria['lob'] == 'Corporate Banking' and portfolio_criteria['industry']:
                if isinstance(portfolio_criteria['industry'], list):
                    industry_series = pd.Series(portfolio_data['industry'])
                    portfolio_data = portfolio_data[industry_series.astype(str).isin([str(i) for i in portfolio_criteria['industry']])]
                else:
                    portfolio_data = portfolio_data[portfolio_data['industry'] == portfolio_criteria['industry']]
            
            # Filter by property type (for CRE)
            if portfolio_criteria['lob'] == 'CRE' and portfolio_criteria['property_type']:
                if isinstance(portfolio_criteria['property_type'], list):
                    portfolio_data = portfolio_data[portfolio_data['cre_property_type'].isin(portfolio_criteria['property_type'])]
                else:
                    portfolio_data = portfolio_data[portfolio_data['cre_property_type'] == portfolio_criteria['property_type']]
            
            # Ensure date columns are datetime
            portfolio_data['origination_date'] = pd.to_datetime(portfolio_data['origination_date'])
            portfolio_data['reporting_date'] = pd.to_datetime(portfolio_data['reporting_date'])
        
        if len(portfolio_data) == 0:
            fig = go.Figure()
            fig.update_layout(
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                height=350,
                margin=dict(l=40, r=20, t=20, b=100),
                font=dict(size=12, color='#1f2937'),
                autosize=True
            )
            fig.add_annotation(text="No data available for this portfolio", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Create the chart based on analysis type
        if analysis_type == 'default_rates':
            fig = create_quarterly_cohort_chart(portfolio_data, selected_quarters, 'default_rates')
        elif analysis_type == 'metric_trend':
            fig = create_quarterly_cohort_chart(portfolio_data, selected_quarters, 'metric_trend', selected_metric)
        else:
            fig = go.Figure()
            fig.update_layout(
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                height=350,
                margin=dict(l=40, r=20, t=20, b=100),
                font=dict(size=12, color='#1f2937'),
                autosize=True
            )
            fig.add_annotation(text="Unknown analysis type", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        return fig
    
    return build_vintage_chart()

def create_quarterly_cohort_chart(data, selected_quarters, analysis_type='default_rates', metric=None):
    """Create quarterly cohort chart for default rates or metric trends"""
    fig = go.Figure()
    colors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
    
    # Convert dates to datetime
    data = data.copy()
    data['origination_date'] = pd.to_datetime(data['origination_date'])
    data['reporting_date'] = pd.to_datetime(data['reporting_date'])
    
    if analysis_type == 'metric_trend':
        return create_metric_trend_chart(fig, data, selected_quarters, metric, colors)
    else:
        return create_default_rates_chart(fig, data, selected_quarters, colors)

def create_metric_trend_chart(fig, data, selected_quarters, metric, colors):
    """Create metric trend chart for quarterly cohorts"""
    
    # Track the actual maximum quarters we'll have data for across all selected cohorts
    actual_max_quarters = 0
    
    for i, quarter in enumerate(selected_quarters):
        # Parse quarter (e.g., "2022Q1")
        year = int(quarter[:4])
        q = int(quarter[5:])
        
        # Define quarter end date
        if q == 4:
            quarter_end = pd.Timestamp(year=year+1, month=1, day=1) - pd.Timedelta(days=1)
        else:
            quarter_end = pd.Timestamp(year=year, month=q*3+1, day=1) - pd.Timedelta(days=1)
        
        # Calculate available quarters for this specific cohort
        max_reporting_date = data['reporting_date'].max()
        cohort_max_quarters = ((max_reporting_date.year - year) * 4 + 
                              (max_reporting_date.quarter - q)) + 1
        cohort_max_quarters = max(1, min(cohort_max_quarters, 20))  # Cap at reasonable limit
        actual_max_quarters = max(actual_max_quarters, cohort_max_quarters)
        
        # Define trailing 4 quarters start date
        trailing_start_year = year
        trailing_start_q = q - 3
        
        # Handle year rollover
        while trailing_start_q <= 0:
            trailing_start_q += 4
            trailing_start_year -= 1
        
        trailing_start = pd.Timestamp(year=trailing_start_year, month=(trailing_start_q-1)*3+1, day=1)
        
        # Get cohort: obligors originated in trailing 4 quarters (including current) with rating < 17
        cohort_data = data[
            (data['origination_date'] >= trailing_start) & 
            (data['origination_date'] <= quarter_end)
        ]
        
        if len(cohort_data) == 0:
            continue
            
        # Get unique non-defaulted obligors at origination (rating < 17)
        cohort_obligors = cohort_data[cohort_data['obligor_rating'] < 17]['obligor_name'].unique()
        cohort_size = len(cohort_obligors)
        
        if cohort_size == 0:
            continue
        
        # Calculate metric averages by quarter since cohort quarter  
        # Use the maximum available quarters for this specific cohort
        cohort_quarters = min(cohort_max_quarters, actual_max_quarters)
        quarters_since_orig = list(range(cohort_quarters))
        metric_values = []
        
        for q_idx in range(cohort_quarters):
            # Calculate target reporting quarter
            target_year = year
            target_q = q + q_idx
            
            # Handle year rollover
            while target_q > 4:
                target_q -= 4
                target_year += 1
            
            # Get data for this reporting quarter
            if target_q == 1:
                quarter_start = pd.Timestamp(year=target_year, month=1, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=3, day=31)
            elif target_q == 2:
                quarter_start = pd.Timestamp(year=target_year, month=4, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=6, day=30)
            elif target_q == 3:
                quarter_start = pd.Timestamp(year=target_year, month=7, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=9, day=30)
            else:  # target_q == 4
                quarter_start = pd.Timestamp(year=target_year, month=10, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=12, day=31)
            
            # Get metric data for cohort obligors in this quarter, excluding defaults (rating 17)
            quarter_data = data[
                (data['obligor_name'].isin(cohort_obligors)) &
                (data['reporting_date'] >= quarter_start) &
                (data['reporting_date'] <= quarter_end_target) &
                (data['obligor_rating'] < 17)  # Exclude defaulted obligors
            ]
            
            if len(quarter_data) > 0 and metric in quarter_data.columns:
                # Calculate average metric for remaining non-default population
                metric_avg = quarter_data[metric].mean()
                metric_values.append(metric_avg)
            else:
                metric_values.append(None)
        
        # Include all quarters for this cohort, replacing None with NaN for proper plotting
        plot_quarters = list(range(cohort_quarters))
        plot_values = [value if value is not None else None for value in metric_values]
        
        # Only plot if we have at least one valid data point
        if any(v is not None for v in plot_values):
            # Add trace to chart
            fig.add_trace(go.Scatter(
                x=plot_quarters,
                y=plot_values,
                mode='lines+markers',
                name=f'{quarter} (n={cohort_size})',
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(color=colors[i % len(colors)], size=6),
                hovertemplate=f'<b>{quarter}</b><br>' +
                            'Quarters Since Cohort: %{x}<br>' +
                            f'{metric.replace("_", " ").title()}: %{{y:.2f}}<br>' +
                            f'Cohort Size: {cohort_size}<extra></extra>'
            ))
    
    # Update layout for metric trend
    fig.update_layout(
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        height=350,
        margin=dict(l=40, r=20, t=20, b=100),
        font=dict(size=12, color='#1f2937'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        autosize=True,
        hovermode='x unified',
        xaxis=dict(
            title="Quarters Since Cohort Quarter",
            tickmode='linear',
            tick0=0,
            dtick=1,
            range=[0, max(1, actual_max_quarters-1)],
            showgrid=False,
            color='#374151'
        ),
        yaxis=dict(
            title=f"Average {metric.replace('_', ' ').title()}",
            showgrid=False,
            color='#374151'
        )
    )
    
    return fig

def create_default_rates_chart(fig, data, selected_quarters, colors):
    """Create default rates chart for quarterly cohorts"""
    
    # Track the actual maximum quarters we'll have data for across all selected cohorts
    actual_max_quarters = 0
    
    for i, quarter in enumerate(selected_quarters):
        # Parse quarter (e.g., "2022Q1")
        year = int(quarter[:4])
        q = int(quarter[5:])
        
        # Define quarter end date
        if q == 4:
            quarter_end = pd.Timestamp(year=year+1, month=1, day=1) - pd.Timedelta(days=1)
        else:
            quarter_end = pd.Timestamp(year=year, month=q*3+1, day=1) - pd.Timedelta(days=1)
        
        # Calculate available quarters for this specific cohort
        max_reporting_date = data['reporting_date'].max()
        cohort_max_quarters = ((max_reporting_date.year - year) * 4 + 
                              (max_reporting_date.quarter - q)) + 1
        cohort_max_quarters = max(1, min(cohort_max_quarters, 20))  # Cap at reasonable limit
        actual_max_quarters = max(actual_max_quarters, cohort_max_quarters)
        
        # Define trailing 4 quarters start date
        # Go back 3 quarters from current quarter to get 4 quarters total
        trailing_start_year = year
        trailing_start_q = q - 3
        
        # Handle year rollover
        while trailing_start_q <= 0:
            trailing_start_q += 4
            trailing_start_year -= 1
        
        trailing_start = pd.Timestamp(year=trailing_start_year, month=(trailing_start_q-1)*3+1, day=1)
        
        # Get cohort: unique obligors originated in trailing 4 quarters (including current) with rating < 17
        cohort_data = data[
            (data['origination_date'] >= trailing_start) & 
            (data['origination_date'] <= quarter_end)
        ]
        
        # Get unique non-defaulted obligors at origination (rating < 17)
        initial_obligors = cohort_data[cohort_data['obligor_rating'] < 17]['obligor_name'].unique()
        cohort_size = len(initial_obligors)
        
        if cohort_size == 0:
            continue
            
        # Calculate default rates by quarter since cohort quarter
        # Use the maximum available quarters for this specific cohort
        cohort_quarters = min(cohort_max_quarters, actual_max_quarters)
        quarters_since_orig = list(range(cohort_quarters))
        default_counts = [0] * cohort_quarters  # Count of defaults by quarter
        
        # Track defaults for each obligor
        defaults_by_quarter = {}  # quarter_index -> set of defaulted obligors
        
        for obligor in initial_obligors:
            obligor_data = data[data['obligor_name'] == obligor].sort_values('reporting_date')
            
            # Find first default (rating turns to 17)
            default_reports = obligor_data[obligor_data['obligor_rating'] >= 17]
            if len(default_reports) > 0:
                first_default_date = default_reports['reporting_date'].min()
                # Calculate quarters since cohort quarter
                quarters_diff = ((first_default_date.year - year) * 4 + 
                               (first_default_date.quarter - q))
                
                # Only track if within our dynamic quarter window and not negative
                if 0 <= quarters_diff < cohort_quarters:
                    # Add this obligor to defaults for this quarter and all subsequent quarters
                    for q_idx in range(quarters_diff, cohort_quarters):
                        if q_idx not in defaults_by_quarter:
                            defaults_by_quarter[q_idx] = set()
                        defaults_by_quarter[q_idx].add(obligor)
        
        # Convert to cumulative default counts
        for q_idx in range(cohort_quarters):
            if q_idx in defaults_by_quarter:
                default_counts[q_idx] = len(defaults_by_quarter[q_idx])
        
        # Convert to percentages
        default_rates = [(count / cohort_size) * 100 if cohort_size > 0 else 0 for count in default_counts]
        
        # Add trace to chart with Financial Trends styling
        fig.add_trace(go.Scatter(
            x=quarters_since_orig,
            y=default_rates,
            mode='lines+markers',
            name=f'{quarter} (n={cohort_size})',
            line=dict(color=colors[i % len(colors)], width=3),
            marker=dict(color=colors[i % len(colors)], size=6),
            hovertemplate=f'<b>{quarter}</b><br>' +
                        'Quarters Since Cohort: %{x}<br>' +
                        'Cumulative Default Rate: %{y:.2f}%<br>' +
                        f'Cohort Size: {cohort_size}<extra></extra>'
        ))
    
    fig.update_layout(
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        height=350,  # Revert to original height
        margin=dict(l=40, r=20, t=20, b=100),
        font=dict(size=12, color='#1f2937'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        autosize=True,
        hovermode='x unified',
        xaxis=dict(
            title="Quarters Since Cohort Quarter",
            tickmode='linear',
            tick0=0,
            dtick=1,
            range=[0, max(1, actual_max_quarters-1)],
            showgrid=False,  # Remove gridlines
            color='#374151'
        ),
        yaxis=dict(
            title="Cumulative Default Rate (%)",
            tickformat='.1f',
            showgrid=False,  # Remove gridlines
            color='#374151'
        )
    )
    
    return fig

# Profile Management Callbacks
@callback(
    [Output('login-modal', 'style'),
     Output('profile-avatar-btn', 'children'),
     Output('delete-profile-dropdown', 'options')],
    [Input('login-btn', 'n_clicks'),
     Input('login-submit', 'n_clicks'),
     Input('register-submit', 'n_clicks'),
     Input('delete-profile-btn', 'n_clicks'),
     Input('login-cancel', 'n_clicks')],
    [State('username-input', 'value'),
     State('role-dropdown', 'value'),
     State('delete-profile-dropdown', 'value')],
    prevent_initial_call=False
)
def handle_login_modal(login_btn_clicks, login_clicks, register_clicks, delete_clicks, cancel_clicks, 
                      username, role, delete_profile_selection):
    """Handle login modal and profile switching"""
    global portfolios, custom_metrics
    
    ctx = callback_context
    def get_user_initials(username):
        """Get user initials for avatar display"""
        if not username or username == 'Guest':
            return 'G'
        # Take first letter of each word, max 2 letters
        words = username.split()
        if len(words) >= 2:
            return (words[0][0] + words[1][0]).upper()
        else:
            return username[0].upper()
    
    if not ctx.triggered:
        # Initial call - return default state
        profiles = user_management.load_profiles()
        delete_options = [{'label': name, 'value': name} for name in profiles.keys() if name != 'Guest']
        hidden_modal_style = {
            "position": "fixed", "top": "0", "left": "0", "width": "100%", 
            "height": "100%", "backgroundColor": "rgba(0, 0, 0, 0.5)", 
            "zIndex": "1000", "display": "none"
        }
        return hidden_modal_style, get_user_initials(user_management.get_current_user()), delete_options
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Load current profiles
    profiles = user_management.load_profiles()
    delete_options = [{'label': name, 'value': name} for name in profiles.keys() if name != 'Guest']
    
    # Default modal style (hidden)
    hidden_modal_style = {
        "position": "fixed", "top": "0", "left": "0", "width": "100%", 
        "height": "100%", "backgroundColor": "rgba(0, 0, 0, 0.5)", 
        "zIndex": "1000", "display": "none"
    }
    
    if trigger_id == 'login-btn':
        # Show modal
        show_modal_style = {
            "position": "fixed", "top": "0", "left": "0", "width": "100%", 
            "height": "100%", "backgroundColor": "rgba(0, 0, 0, 0.5)", 
            "zIndex": "1000", "display": "block"
        }
        return show_modal_style, get_user_initials(user_management.get_current_user()), delete_options
    
    elif trigger_id == 'delete-profile-btn' and delete_profile_selection:
        # Delete profile using dropdown selection
        profiles = user_management.load_profiles()
        if delete_profile_selection in profiles and delete_profile_selection != 'Guest':
            del profiles[delete_profile_selection]
            user_management.save_profiles(profiles)
            
            # Switch back to Guest if deleting current user
            if user_management.get_current_user() == delete_profile_selection:
                user_management.set_current_user('Guest')
                portfolios.clear()
                portfolios.update(config.DEFAULT_PORTFOLIOS.copy())
                custom_metrics.clear()
            
            # Update profile options and hide modal
            updated_delete_options = [{'label': name, 'value': name} for name in profiles.keys() if name != 'Guest']
            
            return hidden_modal_style, get_user_initials(user_management.get_current_user()), updated_delete_options
        else:
            # Cannot delete Guest or non-existent profile
            return hidden_modal_style, get_user_initials(user_management.get_current_user()), delete_options
    
    elif trigger_id == 'login-cancel':
        # Hide modal
        return hidden_modal_style, get_user_initials(user_management.get_current_user()), delete_options
    
    elif trigger_id in ['login-submit', 'register-submit'] and username:
        # Handle login/register
        if trigger_id == 'register-submit' or username not in profiles:
            # Register new user or auto-register
            profiles[username] = {
                'portfolios': {}, 
                'custom_metrics': {}, 
                'role': role or 'BA',  # Default to 'BA' if no role selected
                'created': datetime.now().isoformat()
            }
            user_management.save_profiles(profiles)
        
        # Switch to user
        user_management.set_current_user(username)
        
        # Get user data and only use their custom portfolios if they have any
        user_data = user_management.get_user_data(username)
        user_portfolios = user_data.get('portfolios', {})
        
        # Clear current portfolios and custom metrics
        portfolios.clear()
        custom_metrics.clear()
        
        # Only add user's custom portfolios if they have any, otherwise use defaults
        if user_portfolios:
            portfolios.update(user_portfolios)
        else:
            portfolios.update(config.DEFAULT_PORTFOLIOS.copy())
        
        custom_metrics.update(user_data.get('custom_metrics', {}))
        
        # Hide modal and update profile options
        updated_delete_options = [{'label': name, 'value': name} for name in profiles.keys() if name != 'Guest']
        
        return hidden_modal_style, get_user_initials(user_management.get_current_user()), updated_delete_options
    
    return hidden_modal_style, get_user_initials(user_management.get_current_user()), delete_options

# Profile switching dialog callbacks
@callback(
    [Output('profile-switch-modal', 'style'),
     Output('profile-switch-dropdown', 'options'),
     Output('profile-switch-dropdown', 'value')],
    [Input('profile-avatar-btn', 'n_clicks'),
     Input('profile-switch-confirm', 'n_clicks'),
     Input('profile-switch-cancel', 'n_clicks')],
    [State('profile-switch-dropdown', 'value')],
    prevent_initial_call=True
)
def handle_profile_switch_modal(avatar_clicks, confirm_clicks, cancel_clicks, selected_profile):
    """Handle profile switching dialog"""
    global portfolios, custom_metrics
    
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Load profiles for dropdown options
    profiles = user_management.load_profiles()
    profile_options = [{'label': 'Guest', 'value': 'Guest'}]
    profile_options.extend([{'label': name, 'value': name} for name in profiles.keys()])
    
    # Default modal style (hidden)
    hidden_modal_style = {
        "position": "fixed", "top": "0", "left": "0", "width": "100%", 
        "height": "100%", "backgroundColor": "rgba(0, 0, 0, 0.5)", 
        "zIndex": "1000", "display": "none"
    }
    
    if trigger_id == 'profile-avatar-btn':
        # Show profile switch modal
        show_modal_style = {
            "position": "fixed", "top": "0", "left": "0", "width": "100%", 
            "height": "100%", "backgroundColor": "rgba(0, 0, 0, 0.5)", 
            "zIndex": "1000", "display": "block"
        }
        return show_modal_style, profile_options, user_management.get_current_user()
    
    elif trigger_id == 'profile-switch-confirm' and selected_profile:
        # Switch to selected profile
        user_management.set_current_user(selected_profile)
        
        # Get profile-specific portfolios
        if user_management.get_current_user() == 'Guest':
            portfolios.clear()
            portfolios.update(config.DEFAULT_PORTFOLIOS.copy())
            custom_metrics.clear()
        else:
            user_data = user_management.get_user_data(user_management.get_current_user())
            portfolios.clear()
            user_portfolios = user_data.get('portfolios', {})
            if user_portfolios:
                portfolios.update(user_portfolios)
            else:
                portfolios.update(config.DEFAULT_PORTFOLIOS.copy())
            custom_metrics.clear()
            custom_metrics.update(user_data.get('custom_metrics', {}))
        
        # Hide modal
        return hidden_modal_style, profile_options, selected_profile
    
    elif trigger_id == 'profile-switch-cancel':
        # Hide modal without changes
        return hidden_modal_style, profile_options, user_management.get_current_user()
    
    return hidden_modal_style, profile_options, user_management.get_current_user()

# Contact modal callback
@callback(
    Output('contact-modal', 'style'),
    [Input('contact-btn', 'n_clicks'),
     Input('contact-close', 'n_clicks')],
    prevent_initial_call=True
)
def handle_contact_modal(contact_clicks, close_clicks):
    """Handle contact modal display"""
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Default modal style (hidden)
    hidden_modal_style = {
        "position": "fixed",
        "top": "0",
        "left": "0",
        "width": "100%",
        "height": "100%",
        "backgroundColor": "rgba(0, 0, 0, 0.5)",
        "zIndex": "1000",
        "display": "none"
    }
    
    if trigger_id == 'contact-btn':
        # Show contact modal
        show_modal_style = {
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100%",
            "height": "100%",
            "backgroundColor": "rgba(0, 0, 0, 0.5)",
            "zIndex": "1000",
            "display": "block"
        }
        return show_modal_style
    
    elif trigger_id == 'contact-close':
        # Hide contact modal
        return hidden_modal_style
    
    return hidden_modal_style

# Update user store when profile is switched
@callback(
    Output('current-user-store', 'data'),
    [Input('login-submit', 'n_clicks'),
     Input('register-submit', 'n_clicks'),
     Input('profile-switch-confirm', 'n_clicks')],
    [State('username-input', 'value'),
     State('role-dropdown', 'value'),
     State('profile-switch-dropdown', 'value')],
    prevent_initial_call=True
)
def update_current_user_store(login_clicks, register_clicks, switch_clicks, username, role, selected_profile):
    """Update the current user store when user changes"""
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id in ['login-submit', 'register-submit'] and username:
        user_management.set_current_user(username)
        return username
    elif trigger_id == 'profile-switch-confirm' and selected_profile:
        user_management.set_current_user(selected_profile)
        return selected_profile
    
    return no_update

@callback(
    Output('profile-avatar-btn', 'children', allow_duplicate=True),
    Input('profile-switch-confirm', 'n_clicks'),
    State('profile-switch-dropdown', 'value'),
    prevent_initial_call=True
)
def update_avatar_on_profile_switch(confirm_clicks, selected_profile):
    """Update avatar initials when profile is switched"""
    if confirm_clicks and selected_profile:
        def get_user_initials(username):
            if not username or username == 'Guest':
                return 'G'
            words = username.split()
            if len(words) >= 2:
                return (words[0][0] + words[1][0]).upper()
            else:
                return username[0].upper()
        return get_user_initials(selected_profile)
    return no_update

@callback(
    [Output('portfolio-dropdown', 'options', allow_duplicate=True),
     Output('portfolio-dropdown', 'value', allow_duplicate=True)],
    Input('profile-switch-confirm', 'n_clicks'),
    State('profile-switch-dropdown', 'value'),
    prevent_initial_call=True
)
def update_portfolio_dropdowns_on_profile_change(confirm_clicks, selected_profile):
    """Update main portfolio dropdowns when profile changes"""
    global portfolios, custom_metrics
    
    if not confirm_clicks or not selected_profile:
        return no_update, no_update
    
    if selected_profile:
        user_management.set_current_user(selected_profile)
        
        # Get profile-specific portfolios
        if user_management.get_current_user() == 'Guest':
            portfolios.clear()
            portfolios.update(config.DEFAULT_PORTFOLIOS.copy())
            custom_metrics.clear()
            
            # Remove any custom metric columns from dataframe
            custom_metric_cols = [col for col in facilities_df.columns if col not in ['facility_id', 'obligor_name', 'balance', 'interest_rate', 'lob', 'industry', 'cre_property_type', 'obligor_rating', 'msa', 'origination_date', 'maturity_date', 'reporting_date', 'ltv', 'dscr', 'tier_1_capital_ratio', 'free_cash_flow', 'current_ratio', 'debt_to_equity', 'sir']]
            for col in custom_metric_cols:
                if col in facilities_df.columns:
                    facilities_df.drop(columns=[col], inplace=True)
        else:
            user_data = user_management.get_user_data(user_management.get_current_user())
            portfolios.clear()
            user_portfolios = user_data.get('portfolios', {})
            if user_portfolios:
                portfolios.update(user_portfolios)
            else:
                portfolios.update(config.DEFAULT_PORTFOLIOS.copy())
            custom_metrics.clear()
            custom_metrics.update(user_data.get('custom_metrics', {}))
            
            # Recalculate custom metrics for the dataframe
            for metric_name, formula in custom_metrics.items():
                try:
                    # Get available columns for calculation
                    exclude_cols = ['facility_id', 'obligor_name', 'origination_date', 'maturity_date', 'reporting_date', 'lob', 'industry', 'cre_property_type', 'msa']
                    available_cols = [col for col in facilities_df.columns if col not in exclude_cols]
                    
                    # Create bulk formula for calculation
                    bulk_formula = formula
                    for col in available_cols:
                        if col in bulk_formula:
                            bulk_formula = bulk_formula.replace(col, f"facilities_df['{col}']")
                    
                    # Calculate and add to dataframe
                    result = eval(bulk_formula)
                    if hasattr(result, 'dtype') and result.dtype == bool:
                        result = result.astype(int)
                    facilities_df[metric_name] = result
                except:
                    # If bulk calculation fails, skip this metric
                    pass
        
        # Create portfolio options
        portfolio_options = [{'label': name, 'value': name} for name in portfolios.keys()]
        default_portfolio = list(portfolios.keys())[0] if portfolios else None
        
        return portfolio_options, default_portfolio
    
    return no_update, no_update

@callback(
    [Output('auto-save-notification', 'style'),
     Output('save-message', 'children'),
     Output('hide-notification-interval', 'disabled')],
    Input('auto-save-interval', 'n_intervals'),
    prevent_initial_call=True
)
def show_auto_save_notification(n_intervals):
    """Show auto-save notification"""
    if user_management.get_current_user() != 'Guest' and n_intervals > 0:
        # Only save custom portfolios, not defaults
        user_data = user_management.get_user_data(user_management.get_current_user())
        user_custom_portfolios = user_data.get('portfolios', {})
        
        # Only save portfolios if the user actually has custom ones
        portfolios_to_save = user_custom_portfolios
        user_management.save_user_data(user_management.get_current_user(), portfolios_to_save, custom_metrics)
        
        # Show notification and enable hide timer
        return ({
            "position": "fixed", "bottom": "20px", "right": "20px", 
            "zIndex": "1000", "opacity": "1", "transition": "opacity 0.3s ease",
            "display": "block"
        }, f"Profile '{user_management.get_current_user()}' auto-saved", False)
    
    # Hide notification and disable timer
    return ({
        "position": "fixed", "bottom": "20px", "right": "20px", 
        "zIndex": "1000", "opacity": "0", "transition": "opacity 0.3s ease",
        "display": "none"
    }, "Data auto-saved", True)

# Auto-hide notification after 3 seconds
@callback(
    [Output('auto-save-notification', 'style', allow_duplicate=True),
     Output('hide-notification-interval', 'disabled', allow_duplicate=True)],
    Input('hide-notification-interval', 'n_intervals'),
    prevent_initial_call=True
)
def hide_notification_after_delay(n_intervals):
    """Hide notification after 3 seconds"""
    if n_intervals > 0:
        return ({
            "position": "fixed", "bottom": "20px", "right": "20px", 
            "zIndex": "1000", "opacity": "0", "transition": "opacity 0.3s ease",
            "display": "none"
        }, True)  # Hide notification and disable timer
    return no_update, no_update

# Update vintage analysis dropdown when portfolio dropdown changes
@callback(
    [Output('vintage-portfolio-dropdown', 'options', allow_duplicate=True),
     Output('vintage-portfolio-dropdown', 'value', allow_duplicate=True)],
    Input('portfolio-dropdown', 'value'),
    prevent_initial_call=True
)
def update_vintage_dropdown_from_main(selected_portfolio):
    """Update vintage portfolio dropdown when main portfolio changes"""
    portfolio_options = [{'label': name, 'value': name} for name in portfolios.keys()]
    return portfolio_options, selected_portfolio

# Download callbacks for Portfolio Trends charts
@callback(
    Output('download-data-1', 'data'),
    Input('download-btn-1', 'n_clicks'),
    State('portfolio-dropdown', 'value'),
    State('financial-trends-benchmark-dropdown', 'value'),
    State('financial-trends-metric-dropdown-1', 'value'),
    State('financial-trends-agg-dropdown-1', 'value'),
    prevent_initial_call=True
)
def download_chart_1_data(n_clicks, selected_portfolio, benchmark_portfolio, metric, agg_method):
    if n_clicks and metric and selected_portfolio:
        # Get the same data used in the chart
        def get_download_data(portfolio_name, metric, agg_method='avg'):
            df = facilities_df.copy()
            if portfolio_name not in portfolios:
                return pd.DataFrame()
            
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
            if 'obligor_name' in df.columns and criteria.get('obligors'):
                if isinstance(criteria['obligors'], list):
                    df = df[df['obligor_name'].astype(str).isin([str(i) for i in criteria['obligors']])]
                else:
                    df = df[df['obligor_name'] == criteria['obligors']]
            
            if metric not in df.columns or 'reporting_date' not in df.columns:
                return pd.DataFrame()
            
            df['reporting_date'] = pd.to_datetime(df['reporting_date'])
            group = df.groupby('reporting_date')
            
            if agg_method == 'sum':
                ts = group[metric].sum()
            else:
                ts = group[metric].mean()
            
            return pd.DataFrame({'Date': ts.index, metric: ts.values})
        
        main_data = get_download_data(selected_portfolio, metric, agg_method or 'avg')
        
        if benchmark_portfolio:
            bench_data = get_download_data(benchmark_portfolio, metric, agg_method or 'avg')
            if not bench_data.empty:
                main_data = main_data.merge(bench_data, on='Date', suffixes=('_Selected', '_Benchmark'), how='outer')
        
        return dcc.send_data_frame(main_data.to_csv, f"portfolio_trends_chart1_{metric}_{agg_method or 'avg'}.csv", index=False)
    
    return no_update

@callback(
    Output('download-data-2', 'data'),
    Input('download-btn-2', 'n_clicks'),
    State('portfolio-dropdown', 'value'),
    State('financial-trends-benchmark-dropdown', 'value'),
    State('financial-trends-metric-dropdown-2', 'value'),
    State('financial-trends-agg-dropdown-2', 'value'),
    prevent_initial_call=True
)
def download_chart_2_data(n_clicks, selected_portfolio, benchmark_portfolio, metric, agg_method):
    if n_clicks and metric and selected_portfolio:
        # Reuse the same logic as chart 1
        def get_download_data(portfolio_name, metric, agg_method='avg'):
            df = facilities_df.copy()
            if portfolio_name not in portfolios:
                return pd.DataFrame()
            
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
            if 'obligor_name' in df.columns and criteria.get('obligors'):
                if isinstance(criteria['obligors'], list):
                    df = df[df['obligor_name'].astype(str).isin([str(i) for i in criteria['obligors']])]
                else:
                    df = df[df['obligor_name'] == criteria['obligors']]
            
            if metric not in df.columns or 'reporting_date' not in df.columns:
                return pd.DataFrame()
            
            df['reporting_date'] = pd.to_datetime(df['reporting_date'])
            group = df.groupby('reporting_date')
            
            if agg_method == 'sum':
                ts = group[metric].sum()
            else:
                ts = group[metric].mean()
            
            return pd.DataFrame({'Date': ts.index, metric: ts.values})
        
        main_data = get_download_data(selected_portfolio, metric, agg_method or 'avg')
        
        if benchmark_portfolio:
            bench_data = get_download_data(benchmark_portfolio, metric, agg_method or 'avg')
            if not bench_data.empty:
                main_data = main_data.merge(bench_data, on='Date', suffixes=('_Selected', '_Benchmark'), how='outer')
        
        return dcc.send_data_frame(main_data.to_csv, f"portfolio_trends_chart2_{metric}_{agg_method or 'avg'}.csv", index=False)
    
    return no_update

@callback(
    Output('download-data-3', 'data'),
    Input('download-btn-3', 'n_clicks'),
    State('portfolio-dropdown', 'value'),
    State('financial-trends-benchmark-dropdown', 'value'),
    State('financial-trends-metric-dropdown-3', 'value'),
    State('financial-trends-agg-dropdown-3', 'value'),
    prevent_initial_call=True
)
def download_chart_3_data(n_clicks, selected_portfolio, benchmark_portfolio, metric, agg_method):
    if n_clicks and metric and selected_portfolio:
        # Reuse the same logic as chart 1
        def get_download_data(portfolio_name, metric, agg_method='avg'):
            df = facilities_df.copy()
            if portfolio_name not in portfolios:
                return pd.DataFrame()
            
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
            if 'obligor_name' in df.columns and criteria.get('obligors'):
                if isinstance(criteria['obligors'], list):
                    df = df[df['obligor_name'].astype(str).isin([str(i) for i in criteria['obligors']])]
                else:
                    df = df[df['obligor_name'] == criteria['obligors']]
            
            if metric not in df.columns or 'reporting_date' not in df.columns:
                return pd.DataFrame()
            
            df['reporting_date'] = pd.to_datetime(df['reporting_date'])
            group = df.groupby('reporting_date')
            
            if agg_method == 'sum':
                ts = group[metric].sum()
            else:
                ts = group[metric].mean()
            
            return pd.DataFrame({'Date': ts.index, metric: ts.values})
        
        main_data = get_download_data(selected_portfolio, metric, agg_method or 'avg')
        
        if benchmark_portfolio:
            bench_data = get_download_data(benchmark_portfolio, metric, agg_method or 'avg')
            if not bench_data.empty:
                main_data = main_data.merge(bench_data, on='Date', suffixes=('_Selected', '_Benchmark'), how='outer')
        
        return dcc.send_data_frame(main_data.to_csv, f"portfolio_trends_chart3_{metric}_{agg_method or 'avg'}.csv", index=False)
    
    return no_update

# Set main app layout
app.layout = create_layout(default_portfolio, app.index_string)

# ================================================================================================
# CLIENT-SIDE CALLBACKS AND APP STARTUP
# ================================================================================================

# Dark mode toggle functionality (runs in browser)
app.clientside_callback(
    """
    function(n_clicks){
      const root = document.documentElement;
      if (!window._themeInit){
        const s = localStorage.getItem('theme');
        if (s === 'dark') root.classList.add('dark');
        window._themeInit = true;
      }
      if (n_clicks && n_clicks > 0){
        const isDark = root.classList.toggle('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
      }
      return '';
    }
    """,
    Output("theme-toggle", "title"),  # throwaway output
    Input("theme-toggle", "n_clicks"),
)
# ================================================================================================
# APPLICATION ENTRY POINT
# ================================================================================================

if __name__ == '__main__':
    """
    Start the Portfolio Performance Dashboard application.
    
    The app runs in debug mode for development with hot reloading enabled.
    In production, this should be deployed using a WSGI server like Gunicorn.
    """
    print("Starting Portfolio Performance Dashboard...")
    print("Dashboard available at: http://127.0.0.1:8050/")
    print("Press Ctrl+C to stop the server")
    
    # Start the Dash development server
    app.run(
        debug=config.DEBUG_MODE,
        host=config.HOST,
        port=config.PORT
    )
