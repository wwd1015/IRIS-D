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

# Global Variables
custom_metrics = {}  # Store custom metric formulas

# Default portfolios (constant)
DEFAULT_PORTFOLIOS = {
    'Corporate Banking': {'lob': 'Corporate Banking', 'industry': None, 'property_type': None},
    'CRE': {'lob': 'CRE', 'industry': None, 'property_type': None}
}

# Profile Management System
PROFILES_FILE = 'data/user_profiles.json'
current_user = 'Guest'  # Default user

def get_current_user_role():
    """Get the current user's role"""
    if current_user == 'Guest':
        return 'Guest'
    
    user_data = get_user_data(current_user)
    return user_data.get('role', 'BA')  # Default to BA if role not found

def create_role_based_navigation():
    """Create navigation tabs based on user role - all tabs present but visibility controlled"""
    user_role = get_current_user_role()
    print(f"DEBUG: Creating navigation for user '{current_user}' with role '{user_role}'")
    
    # Base tabs available to all users
    base_tabs = [
        html.Button("Portfolio Summary", id="tab-portfolio-summary", n_clicks=0, 
                   className="px-3 py-1.5 rounded bg-ink-900 text-white"),
        html.Button("Portfolio Trend", id="tab-financial-trends", n_clicks=0,
                   className="px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700"),
        html.Button("Holdings", id="tab-holdings", n_clicks=0,
                   className="px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700"),
        html.Button("Financial Trend", id="tab-financial-trend-details", n_clicks=0,
                   className="px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700"),
        html.Button("Vintage Analysis", id="tab-vintage-analysis", n_clicks=0,
                   className="px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700")
    ]
    
    # All role-specific tabs - always present but hidden based on role
    role_specific_tabs = [
        html.Button("SIR Analysis", id="tab-sir-analysis", n_clicks=0,
                   className="px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700",
                   style={"display": "inline-block" if user_role == 'SAG' else "none"}),
        html.Button("Location Analysis", id="tab-location-analysis", n_clicks=0,
                   className="px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700",
                   style={"display": "inline-block" if user_role == 'CRE SCO' else "none"}),
        html.Button("Financial Projection", id="tab-financial-projection", n_clicks=0,
                   className="px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700",
                   style={"display": "inline-block" if user_role == 'Corp SCO' else "none"}),
        html.Button("Model Backtesting", id="tab-model-backtesting", n_clicks=0,
                   className="px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700",
                   style={"display": "inline-block" if user_role == 'BA' else "none"})
    ]
    
    return base_tabs + role_specific_tabs
auto_save_timer = None

def load_profiles():
    """Load user profiles from file"""
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_profiles(profiles_data):
    """Save user profiles to file"""
    os.makedirs(os.path.dirname(PROFILES_FILE), exist_ok=True)
    with open(PROFILES_FILE, 'w') as f:
        json.dump(profiles_data, f, indent=2)

def get_user_data(username):
    """Get user-specific data (portfolios and custom metrics)"""
    profiles = load_profiles()
    if username in profiles:
        return profiles[username]
    return {'portfolios': {}, 'custom_metrics': {}}

def save_user_data(username, portfolios_data, custom_metrics_data):
    """Save user-specific data while preserving existing fields like role"""
    profiles = load_profiles()
    if username in profiles:
        # Preserve existing data like role, created date
        profiles[username].update({
            'portfolios': portfolios_data,
            'custom_metrics': custom_metrics_data,
            'last_saved': datetime.now().isoformat()
        })
    else:
        # New user
        profiles[username] = {
            'portfolios': portfolios_data,
            'custom_metrics': custom_metrics_data,
            'last_saved': datetime.now().isoformat()
        }
    save_profiles(profiles)

def get_current_user_portfolios():
    """Get portfolios for current user"""
    if current_user == 'Guest':
        return DEFAULT_PORTFOLIOS.copy()
    else:
        user_data = get_user_data(current_user)
        user_portfolios = user_data.get('portfolios', {})
        if not user_portfolios:
            # Initialize with default portfolios for new users
            return DEFAULT_PORTFOLIOS.copy()
        return user_portfolios

def auto_save_data():
    """Auto-save current user data every 15 seconds"""
    global auto_save_timer
    if current_user != 'Guest':
        # Only save if user has custom portfolios (not defaults)
        user_data = get_user_data(current_user)
        user_custom_portfolios = user_data.get('portfolios', {})
        
        # Only save portfolios if the user actually has custom ones
        portfolios_to_save = user_custom_portfolios
        save_user_data(current_user, portfolios_to_save, custom_metrics)
    # Schedule next auto-save
    auto_save_timer = Timer(15.0, auto_save_data)
    auto_save_timer.start()

# Data Loading Functions - Integrated directly into app
def load_facilities_data():
    """
    Load facilities data using DataTidy transformations with fallback
    Returns: pd.DataFrame: Processed facilities data
    """
    db_path = 'data/bank_risk.db'
    config_path = 'data/datatidy_config.yaml'
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}. Please run db_data_generator.py first.")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"DataTidy config not found: {config_path}. Please run db_data_generator.py first.")
    
    try:
        print("Loading facilities data from database via DataTidy...")
        
        # Load DataTidy config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Process with DataTidy
        dt = DataTidy()
        dt.load_config(config)
        df = dt.process_data()
        
        print(f"✓ Loaded {len(df)} facility records from database via DataTidy")
        derived_fields = [col for col in df.columns if col in ['balance_millions', 'risk_category']]
        if derived_fields:
            print(f"✓ DataFrame includes derived fields: {derived_fields}")
        return df
        
    except Exception as e:
        print(f"DataTidy processing failed: {e}")
        print("Falling back to direct database query...")
        
        try:
            # Direct database fallback
            engine = create_engine(f'sqlite:///{db_path}')
            df = pd.read_sql('SELECT * FROM raw_facilities ORDER BY facility_id, reporting_date', engine)
            print(f"✓ Loaded {len(df)} facility records from database (direct query)")
            return df
        except Exception as e2:
            raise Exception(f"Both DataTidy and direct database query failed. DataTidy error: {e}. Database error: {e2}")

# Initialize profiles and start auto-save
user_profiles = load_profiles()
auto_save_data()  # Start auto-save timer

# Load data using integrated DataTidy pipeline
try:
    print("=== Bank Risk Dashboard - Integrated DataTidy Processing ===")
    
    # Load facilities data directly with integrated processing
    facilities_df = load_facilities_data()
    
    # Get latest data for each facility (most recent reporting date)
    latest_facilities = facilities_df.sort_values('reporting_date').groupby('facility_id').tail(1)
    
    # Store portfolios in session (use default portfolios constant)
    portfolios = DEFAULT_PORTFOLIOS.copy()
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

# Initialize the Dash app with modern styling
app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder='assets')
server = app.server  # Flask server for custom routes

# Custom HTML template with Tailwind CSS and dark mode support
app.index_string = '''
<!DOCTYPE html>
<html lang="en" class="no-js">
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Bank Risk Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
      tailwind.config = {
        darkMode: 'class',
        theme: { extend: {
          colors: {
            ink: { 900:'#0f172a',800:'#1e293b',700:'#334155',600:'#475569',500:'#64748b',100:'#e2e8f0',50:'#f1f5f9' },
            brand: {500:'#8b5cf6',400:'#a855f7',300:'#c4b5fd'}
          },
          boxShadow: { soft: '0 2px 10px rgba(15,23,42,.06)'}
        }}
      };
      // theme bootstrap (before paint)
      (function(){
        const s = localStorage.getItem('theme');
        if (s === 'dark' || (!s && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
          document.documentElement.classList.add('dark');
        }
      })();
    </script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    {%metas%}
    {%favicon%}
    {%css%}
  </head>
  <body class="bg-ink-50 text-ink-800 dark:bg-ink-900 dark:text-slate-200 font-[Inter,system-ui]">
    <div id="root">{%app_entry%}</div>
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>
  </body>
</html>
'''

def get_filtered_data(portfolio_name):
    """Get filtered data based on portfolio criteria"""
    if portfolio_name not in portfolios:
        return pd.DataFrame()
    
    portfolio_criteria = portfolios[portfolio_name]
    filtered_data = latest_facilities.copy()
    
    # Filter by LOB
    if portfolio_criteria['lob']:
        filtered_data = filtered_data[filtered_data['lob'] == portfolio_criteria['lob']]
    
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
    
    return filtered_data

def create_portfolio_sidebar(selected_portfolio):
    """Create the portfolio selection sidebar with modern Tailwind styling"""
    return html.Section([
        html.Header([
            html.H2("Portfolios", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700 flex items-center justify-between"),
        html.Div([
            dcc.Dropdown(
                id='portfolio-dropdown',
                options=[{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios],
                value=selected_portfolio,
                placeholder="Select portfolio...",
                className="text-xs",
                style={"marginBottom": "16px", "fontSize": "12px"}
            ),
            
            # Portfolio Creator & Manager Section
            html.Div([
                html.H3("Create New Portfolio", className="text-sm font-semibold mb-3 text-brand-500"),
                html.Div([
                    html.Label("Line of Business", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                    dcc.Dropdown(
                        id='lob-dropdown',
                        options=[
                            {'label': 'Corporate Banking', 'value': 'Corporate Banking'},
                            {'label': 'CRE', 'value': 'CRE'}
                        ],
                        placeholder="Select LOB...",
                        className="text-xs mb-3"
                    )
                ], className="mb-3"),
                html.Div([
                    html.Label("Industry", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                    dcc.Dropdown(
                        id='industry-dropdown',
                        options=[],
                        placeholder="Select Industry...",
                        className="text-xs",
                        multi=True
                    )
                ], className="mb-3", id='industry-group', style={'display': 'none'}),
                html.Div([
                    html.Label("Property Type", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                    dcc.Dropdown(
                        id='property-type-dropdown',
                        options=[],
                        placeholder="Select Property Type...",
                        className="text-xs",
                        multi=True
                    )
                ], className="mb-3", id='property-type-group', style={'display': 'none'}),
                html.Div([
                    html.Label("OR Select Obligors Directly", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                    dcc.Dropdown(
                        id='obligor-dropdown',
                        options=[],
                        placeholder="Select obligors...",
                        className="text-xs",
                        multi=True
                    )
                ], className="mb-3", id='obligor-group'),
                html.Div([
                    html.Label("Portfolio Name", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                    dcc.Input(
                        id='portfolio-name-input',
                        type='text',
                        placeholder="Enter portfolio name...",
                        className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-ink-600 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                    )
                ], className="mb-3"),
                html.Button("Save Portfolio", id='save-portfolio-btn', 
                           className="w-full mb-4 px-3 py-2 text-xs bg-brand-500 text-white rounded-md hover:bg-brand-400 transition-colors"),
                
                # Separator
                html.Hr(className="border-slate-200 dark:border-ink-700 mb-4"),
                
                # Delete Portfolio Section
                html.H3("Delete Portfolio", className="text-sm font-semibold mb-3 text-red-600"),
                html.Div([
                    html.Label("Select Portfolio to Delete", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                    dcc.Dropdown(
                        id='delete-portfolio-dropdown',
                        options=[{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios if portfolio not in ['Corporate Banking', 'CRE']],
                        placeholder="Select portfolio to delete...",
                        className="text-xs"
                    )
                ], className="mb-3"),
                html.Button("Delete Portfolio", id='delete-portfolio-btn', 
                           className="w-full px-3 py-2 text-xs border border-red-300 text-red-600 rounded-md hover:bg-red-50 dark:hover:bg-red-900 transition-colors")
            ], className="space-y-3 mt-4")
        ], className="p-4 flex-1 overflow-auto")
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden flex flex-col min-h-[640px]")

def create_charts(selected_portfolio):
    """Create charts for the selected portfolio with dark theme and purple styling"""
    portfolio_data = get_filtered_data(selected_portfolio)
    
    if len(portfolio_data) == 0:
        # Return empty charts if no data
        empty_bar = go.Figure()
        empty_bar.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        empty_bar.update_layout(plot_bgcolor='#ffffff', paper_bgcolor='#ffffff', title="Top 10 Holdings by Borrower", autosize=True)
        
        empty_pie = go.Figure()
        empty_pie.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        empty_pie.update_layout(plot_bgcolor='#ffffff', paper_bgcolor='#ffffff', title="Holdings by Industry", autosize=True)
        
        return empty_bar, empty_pie
    
    # Top 10 holdings by borrower
    borrower_totals = portfolio_data.groupby('obligor_name')['balance'].sum().sort_values(ascending=False).head(10)
    
    borrower_names = borrower_totals.index.tolist()
    balances_m = [f"(${balance/1e6:.1f}M)" for balance in borrower_totals.values.tolist()]
    labels = [f"{name}  {bal}" for name, bal in zip(borrower_names, balances_m)]
    
    bar_fig = go.Figure(data=[
        go.Bar(
            x=borrower_totals.values.tolist(),
            y=list(range(len(borrower_totals))),
            orientation='h',
            marker_color='#8b5cf6',
            text=labels,
            texttemplate="%{text}",
            insidetextanchor='middle',
            textfont=dict(size=12, color='#ffffff'),
            textposition='inside',
        )
    ])
    
    bar_fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(size=12, color='#1f2937'),
        autosize=True,
        showlegend=False,
        xaxis=dict(
            title="Balance ($)",
            showgrid=True,
            gridcolor="#e5e7eb",
            color='#374151'
        ),
        yaxis=dict(
            title="",
            showticklabels=False,
            color='#374151',
            range=[len(borrower_totals)-1, -1]
        )
    )
    
    # Holdings by industry/property type
    if 'Corporate Banking' in portfolio_data['lob'].values:
        # For Corporate Banking, use industry
        industry_data = portfolio_data[portfolio_data['lob'] == 'Corporate Banking']['industry'].value_counts()
        pie_labels = industry_data.index.tolist()
        pie_values = industry_data.values.tolist()
        pie_title = "Holdings by Industry"
    else:
        # For CRE, use property type
        property_data = portfolio_data[portfolio_data['lob'] == 'CRE']['cre_property_type'].value_counts()
        pie_labels = property_data.index.tolist()
        pie_values = property_data.values.tolist()
        pie_title = "Holdings by Property Type"
    
    pie_fig = go.Figure(data=[
        go.Pie(
            labels=pie_labels,
            values=pie_values,
            hole=0.4,
            marker_colors=['#8b5cf6', '#7c3aed', '#6d28d9', '#5b21b6']
        )
    ])
    
    pie_fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        font=dict(size=12, color='#1f2937'),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        autosize=True
    )
    
    return bar_fig, pie_fig

def create_watchlist_table(selected_portfolio):
    """Create risk table for the selected portfolio with modern styling and new logic"""
    portfolio_data = get_filtered_data(selected_portfolio)
    facilities_full = facilities_df.copy()
    
    if len(portfolio_data) == 0:
        return html.Div("No data available for this portfolio.", className="p-4")

    # Get latest and previous quarter for each facility
    portfolio_data = portfolio_data.copy()
    portfolio_data['reporting_date'] = pd.to_datetime(portfolio_data['reporting_date'])
    facilities_full['reporting_date'] = pd.to_datetime(facilities_full['reporting_date'])
    
    watchlist_rows = []
    for idx, row in portfolio_data.iterrows():
        fac_id = row['facility_id']
        obligor = row['obligor_name']
        current_rating = row['obligor_rating']
        current_date = row['reporting_date']
        balance = row['balance']
        # Get previous quarter for this facility
        fac_hist = facilities_full[facilities_full['facility_id'] == fac_id].sort_values('reporting_date')
        prev_rows = fac_hist[fac_hist['reporting_date'] < current_date]
        if not prev_rows.empty:
            prev_row = prev_rows.iloc[-1]
            prev_rating = prev_row['obligor_rating']
            rating_change = current_rating - prev_rating
        else:
            prev_rating = None
            rating_change = 0
        # Downgrade if rating increased (worse) or current rating >= 14
        if (prev_rating is not None and rating_change > 0) or (current_rating >= 14):
            # Color for risk rating
            if current_rating <= 6:
                rating_class = "status-success"
            elif current_rating <= 12:
                rating_class = "status-warning"
            else:
                rating_class = "status-error"
            # Color for rating change
            if rating_change > 0:
                change_class = "status-error"
            elif rating_change < 0:
                change_class = "status-success"
            else:
                change_class = "status-info"
            watchlist_rows.append({
                'obligor_name': obligor,
                'facility_id': fac_id,
                'balance_m': f"${balance/1e6:.2f}M",
                'current_rating': current_rating,
                'rating_change': f"{rating_change:+d}",
                'rating_class': rating_class,
                'change_class': change_class
            })
    if not watchlist_rows:
        return html.Div("No watchlist records for this portfolio.", className="p-4")
    
    # Build table
    table_header = html.Thead(html.Tr([
        html.Th("Obligor Name"),
        html.Th("Facility ID"),
        html.Th("Balance (M)"),
        html.Th("Risk Rating"),
        html.Th("Rating Change")
    ]))
    table_body = html.Tbody([
        html.Tr([
            html.Td(row['obligor_name']),
            html.Td(row['facility_id']),
            html.Td(row['balance_m']),
            html.Td(html.Span(row['current_rating'], className=f"status-badge {row['rating_class']}")),
            html.Td(html.Span(row['rating_change'], className=f"status-badge {row['change_class']}")),
        ]) for row in watchlist_rows
    ])
    return html.Div([
        html.Div([
            html.Table([
                table_header,
                table_body
            ], className="table")
        ], style={"overflowX": "auto", "width": "100%", "maxHeight": "350px", "overflowY": "auto"})
    ], className="table-container")

def create_positions_panel(selected_portfolio):
    """Create portfolio positions panel with modern Tailwind styling"""
    # Get current quarter end data only
    current_quarter_end = facilities_df['reporting_date'].max()
    
    # Filter to current quarter snapshot
    portfolio_data = get_filtered_data(selected_portfolio)
    if len(portfolio_data) == 0:
        return html.Div("No data available for this portfolio.", className="p-4 positions-panel")
    
    # Only filter by reporting_date if the column exists and has data
    if 'reporting_date' in portfolio_data.columns and len(portfolio_data) > 0:
        portfolio_data = portfolio_data[portfolio_data['reporting_date'] == current_quarter_end]
    
    # Get all data for comparison, with safe filtering
    all_portfolios_data = []
    for pname in portfolios.keys():
        pdata = get_filtered_data(pname)
        if len(pdata) > 0 and 'reporting_date' in pdata.columns:
            pdata = pdata[pdata['reporting_date'] == current_quarter_end]
            all_portfolios_data.append(pdata)
    
    if all_portfolios_data:
        all_data = pd.concat(all_portfolios_data).drop_duplicates()
    else:
        all_data = pd.DataFrame()

    if len(portfolio_data) == 0:
        return html.Div("No data available for this portfolio.", className="p-4 positions-panel")

    # Portfolio name and % of total
    total_balance_all = all_data['balance'].sum() if len(all_data) > 0 and 'balance' in all_data.columns else 0
    total_balance = portfolio_data['balance'].sum() if 'balance' in portfolio_data.columns else 0
    pct_of_total = (total_balance / total_balance_all * 100) if total_balance_all > 0 else 0

    # Portfolio totals
    avg_rating = portfolio_data['obligor_rating'].mean() if 'obligor_rating' in portfolio_data else None
    today = pd.Timestamp.today()
    portfolio_data['maturity_date'] = pd.to_datetime(portfolio_data['maturity_date'])
    avg_maturity_yrs = (portfolio_data['maturity_date'] - today).dt.days.mean() / 365.25

    # Maturity buckets (as %)
    maturity_years = (portfolio_data['maturity_date'] - today).dt.days / 365.25
    buckets = [(1,3), (3,5), (5,100)]
    bucket_labels = ["1-3 Yrs", "3-5 Yrs", ">5 Yrs"]
    maturity_percents = [((maturity_years >= b[0]) & (maturity_years < b[1])).sum() / len(portfolio_data) * 100 if len(portfolio_data) > 0 else 0 for b in buckets]
    na_percent = 100 - sum(maturity_percents)

    # Rating composition (by individual ratings 1-16)
    rating_rows = []
    for rating in range(1, 18):  # Ratings 1-17
        mask = portfolio_data['obligor_rating'] == rating
        rating_balance = portfolio_data.loc[mask, 'balance'].sum()
        percent = (rating_balance / total_balance * 100) if total_balance > 0 else 0
        
        # Only show ratings that have data
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
    ], className="chart-card positions-panel")

def create_main_content(selected_portfolio):
    """Create the main content area with dark theme and purple styling"""
    bar_fig, pie_fig = create_charts(selected_portfolio)
    
    # Determine dynamic title based on portfolio type
    portfolio_data = get_filtered_data(selected_portfolio)
    if len(portfolio_data) > 0 and 'Corporate Banking' in portfolio_data['lob'].values:
        pie_chart_title = "Holdings by Industry"
    else:
        pie_chart_title = "Holdings by Property Type"
    
    return html.Section([
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Top 10 Holdings by Borrowers", className="text-sm font-semibold"),
                    html.Div("Asset Type = Corporate Banking", className="text-xs text-ink-500 dark:text-slate-400")
                ], className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-ink-700"),
                dcc.Graph(
                    figure=bar_fig, 
                    config={'displayModeBar': False}
                )
            ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 p-4"),
            html.Div([
                html.Div([
                    html.H3(pie_chart_title, className="text-sm font-semibold"),
                    html.Div("Portfolio Distribution", className="text-xs text-ink-500 dark:text-slate-400")
                ], className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-ink-700"),
                dcc.Graph(
                    figure=pie_fig, 
                    config={'displayModeBar': False}
                )
            ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 p-4")
        ], className="grid grid-cols-1 xl:grid-cols-2 gap-4"),
        html.Div([
            html.Div([
                html.H3("Credit Watchlist", className="text-sm font-semibold"),
                html.Div("High Risk Facilities", className="text-xs text-ink-500 dark:text-slate-400")
            ], className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-ink-700 mb-4"),
            create_watchlist_table(selected_portfolio)
        ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 p-4 mt-4")
    ])

def create_holdings_sidebar(selected_portfolio):
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
            html.Div(id='holdings-filters-container', children=create_holdings_filters(selected_portfolio))
        ], className="p-4 flex-1 overflow-auto")
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden flex flex-col min-h-[640px]")

def create_holdings_filters(selected_portfolio):
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
    min_balance = portfolio_data['balance'].min()
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

def create_holdings_table(selected_portfolio, rating_filter=None, obligor_filter=None, industry_filter=None, property_filter=None, msa_filter=None, balance_filter=None):
    """Create collapsible table for Holdings tab with optional filters"""
    portfolio_data = get_filtered_data(selected_portfolio)
    
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

def create_holdings_content(selected_portfolio):
    """Create the Holdings tab content"""
    return html.Div([
        html.Div(id='holdings-table-container', children=create_holdings_table(selected_portfolio)),
    ], className="main-content")

def create_vintage_analysis_sidebar(selected_portfolio):
    """Create the vintage analysis sidebar with quarterly cohort controls"""
    
    # Generate quarterly options from facilities data
    facilities_df['origination_date'] = pd.to_datetime(facilities_df['origination_date'])
    
    # Get unique year-quarter combinations from origination dates
    quarterly_options = []
    unique_dates = facilities_df['origination_date'].dropna().unique()
    
    for date in sorted(unique_dates):
        date_ts = pd.Timestamp(date)
        quarter_label = f"{date_ts.year}Q{date_ts.quarter}"
        if quarter_label not in [opt['label'] for opt in quarterly_options]:
            quarterly_options.append({'label': quarter_label, 'value': quarter_label})
    
    # Default to last 3 quarters
    default_quarters = [opt['value'] for opt in quarterly_options[-3:]] if len(quarterly_options) >= 3 else [opt['value'] for opt in quarterly_options]
    
    return html.Section([
        html.Header([
            html.H2("Vintage Analysis", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700 flex items-center justify-between"),
        html.Div([
            # Portfolio Selection
            html.Div([
                html.Label("Portfolio:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='vintage-portfolio-dropdown',
                    options=[{'label': portfolio, 'value': portfolio} for portfolio in portfolios.keys()],
                    value=selected_portfolio or default_portfolio,
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-3"),
            
            # Analysis Type Selection
            html.Div([
                html.Label("Analysis Type:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='vintage-analysis-type',
                    options=[
                        {'label': 'Default Rates', 'value': 'default_rates'},
                        {'label': 'Metric Trend', 'value': 'metric_trend'}
                    ],
                    value='default_rates',
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-3"),
            
            # Metric Selection (conditional)
            html.Div([
                html.Label("Metric:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='vintage-metric-dropdown',
                    options=[],
                    value=None,
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-3", id='vintage-metric-selector', style={'display': 'none'}),
            
            # Quarterly Cohort Selection
            html.Div([
                html.Label("Select Quarterly Cohorts:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='vintage-vintage-quarters',
                    options=quarterly_options,
                    value=default_quarters,
                    multi=True,
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-3")
            
        ], className="p-4 flex-1 overflow-auto")
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden flex flex-col min-h-[640px]")

def create_vintage_analysis_content(selected_portfolio):
    """Create the vintage analysis chart content area using Financial Trends structure"""
    return html.Div([
        # Default Rate Chart
        html.Div([
            dcc.Graph(id='vintage-analysis-chart', config={'displayModeBar': False})
        ], className="chart-card", style={"marginBottom": "20px"}),
    ], className="main-content")

def create_financial_trends_sidebar(selected_portfolio):
    """Create simplified sidebar for Financial Trends tab with consistent styling"""
    return html.Section([
        html.Header([
            html.H2("Financial Trends", className="text-sm font-semibold")
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
                html.P("Supports conditions & backticks. Use == for equality. Examples: (obligor_rating == 14) * 1, `free cash flow` / liquidity", 
                       className="text-xs text-ink-500 dark:text-slate-400 mb-2"),
                dcc.Input(
                    id='custom-metric-formula',
                    type='text',
                    placeholder="e.g., (obligor_rating == 14) * 1",
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

def get_portfolio_metrics(selected_portfolio):
    """Get appropriate metrics based on portfolio type and available data columns"""
    global custom_metrics
    
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

def create_financial_trends_content(selected_portfolio):
    """Create the Financial Trends tab content"""
    metrics_options = get_portfolio_metrics(selected_portfolio)
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
            min_date = unique_dates[0] if unique_dates else '2022-01-01'
            max_date = unique_dates[-1] if unique_dates else '2025-12-31'
        else:
            min_date = '2022-01-01'
            max_date = '2025-12-31'
    else:
        min_date = '2022-01-01'
        max_date = '2025-12-31'
    
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

def create_financial_trend_details_sidebar(selected_portfolio):
    """Create sidebar for Financial Trend Details tab with test.py styling"""
    return html.Div([
        html.Div([
            html.H2("Financial Trend Details", className="text-sm font-semibold")
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

def create_financial_trend_details_content(selected_portfolio):
    """Create Financial Trend Details content with test.py table styling"""
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

def create_sir_analysis_sidebar(selected_portfolio):
    """Create simplified sidebar for SIR Analysis tab"""
    return html.Div([
        html.Div([
            html.H2("SIR Analysis", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700"),
        html.Div([
            # Portfolio filter
            html.Div([
                html.Label("Portfolio", className="text-xs font-medium text-ink-600 dark:text-slate-400 mb-1 block"),
                dcc.Dropdown(
                    id='sir-portfolio-dropdown',
                    options=[{'label': name, 'value': name} for name in portfolios.keys()],
                    value=selected_portfolio,
                    className="text-xs",
                    style={"fontSize": "11px"}
                )
            ], className="mb-4"),
        ], className="p-4 space-y-4")
    ], className="w-64 bg-white dark:bg-ink-800 border-r border-slate-200 dark:border-ink-700")

def create_sir_analysis_content(selected_portfolio):
    """Create SIR Analysis content - placeholder for now"""
    return html.Div([
        html.Div([
            html.Div([
                html.H3("SIR Analysis", className="text-sm font-semibold text-ink-700 dark:text-slate-300"),
                html.Div("Special Interest Rate Analysis - Coming Soon", className="text-xs text-ink-500 dark:text-slate-400")
            ], className="flex-1"),
        ], className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-ink-700"),
        
        html.Div([
            html.Div([
                html.H4("Feature Under Development", className="text-lg font-medium text-ink-600 dark:text-slate-300 mb-4"),
                html.P("This analysis module is currently being developed and will be available soon.", 
                      className="text-ink-500 dark:text-slate-400")
            ], className="text-center py-20")
        ], className="p-6")
        
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden main-content")

def create_location_analysis_sidebar(selected_portfolio):
    """Create simplified sidebar for Location Analysis tab"""
    return html.Div([
        html.Div([
            html.H2("Location Analysis", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700"),
        html.Div([
            # Portfolio filter
            html.Div([
                html.Label("Portfolio", className="text-xs font-medium text-ink-600 dark:text-slate-400 mb-1 block"),
                dcc.Dropdown(
                    id='location-portfolio-dropdown',
                    options=[{'label': name, 'value': name} for name in portfolios.keys()],
                    value=selected_portfolio,
                    className="text-xs",
                    style={"fontSize": "11px"}
                )
            ], className="mb-4"),
        ], className="p-4 space-y-4")
    ], className="w-64 bg-white dark:bg-ink-800 border-r border-slate-200 dark:border-ink-700")

def create_location_analysis_content(selected_portfolio):
    """Create Location Analysis content - placeholder for now"""
    return html.Div([
        html.Div([
            html.Div([
                html.H3("Location Analysis", className="text-sm font-semibold text-ink-700 dark:text-slate-300"),
                html.Div("Geographic and Location-based Analysis - Coming Soon", className="text-xs text-ink-500 dark:text-slate-400")
            ], className="flex-1"),
        ], className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-ink-700"),
        
        html.Div([
            html.Div([
                html.H4("Feature Under Development", className="text-lg font-medium text-ink-600 dark:text-slate-300 mb-4"),
                html.P("This analysis module is currently being developed and will be available soon.", 
                      className="text-ink-500 dark:text-slate-400")
            ], className="text-center py-20")
        ], className="p-6")
        
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden main-content")

def create_financial_projection_sidebar(selected_portfolio):
    """Create simplified sidebar for Financial Projection tab"""
    return html.Div([
        html.Div([
            html.H2("Financial Projection", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700"),
        html.Div([
            # Portfolio filter
            html.Div([
                html.Label("Portfolio", className="text-xs font-medium text-ink-600 dark:text-slate-400 mb-1 block"),
                dcc.Dropdown(
                    id='financial-projection-portfolio-dropdown',
                    options=[{'label': name, 'value': name} for name in portfolios.keys()],
                    value=selected_portfolio,
                    className="text-xs",
                    style={"fontSize": "11px"}
                )
            ], className="mb-4"),
        ], className="p-4 space-y-4")
    ], className="w-64 bg-white dark:bg-ink-800 border-r border-slate-200 dark:border-ink-700")

def create_financial_projection_content(selected_portfolio):
    """Create Financial Projection content - placeholder for now"""
    return html.Div([
        html.Div([
            html.Div([
                html.H3("Financial Projection", className="text-sm font-semibold text-ink-700 dark:text-slate-300"),
                html.Div("Financial Forecasting and Projection Analysis - Coming Soon", className="text-xs text-ink-500 dark:text-slate-400")
            ], className="flex-1"),
        ], className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-ink-700"),
        
        html.Div([
            html.Div([
                html.H4("Feature Under Development", className="text-lg font-medium text-ink-600 dark:text-slate-300 mb-4"),
                html.P("This analysis module is currently being developed and will be available soon.", 
                      className="text-ink-500 dark:text-slate-400")
            ], className="text-center py-20")
        ], className="p-6")
        
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden main-content")

def create_model_backtesting_sidebar(selected_portfolio):
    """Create simplified sidebar for Model Backtesting tab"""
    return html.Div([
        html.Div([
            html.H2("Model Backtesting", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700"),
        html.Div([
            # Portfolio filter
            html.Div([
                html.Label("Portfolio", className="text-xs font-medium text-ink-600 dark:text-slate-400 mb-1 block"),
                dcc.Dropdown(
                    id='model-backtesting-portfolio-dropdown',
                    options=[{'label': name, 'value': name} for name in portfolios.keys()],
                    value=selected_portfolio,
                    className="text-xs",
                    style={"fontSize": "11px"}
                )
            ], className="mb-4"),
        ], className="p-4 space-y-4")
    ], className="w-64 bg-white dark:bg-ink-800 border-r border-slate-200 dark:border-ink-700")

def create_model_backtesting_content(selected_portfolio):
    """Create Model Backtesting content - placeholder for now"""
    return html.Div([
        html.Div([
            html.Div([
                html.H3("Model Backtesting", className="text-sm font-semibold text-ink-700 dark:text-slate-300"),
                html.Div("Model Validation and Backtesting Analysis - Coming Soon", className="text-xs text-ink-500 dark:text-slate-400")
            ], className="flex-1"),
        ], className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-ink-700"),
        
        html.Div([
            html.Div([
                html.H4("Feature Under Development", className="text-lg font-medium text-ink-600 dark:text-slate-300 mb-4"),
                html.P("This analysis module is currently being developed and will be available soon.", 
                      className="text-ink-500 dark:text-slate-400")
            ], className="text-center py-20")
        ], className="p-6")
        
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden main-content")

def create_layout(selected_portfolio=None):
    """Create the main layout with modern Tailwind styling"""
    if selected_portfolio is None:
        selected_portfolio = default_portfolio
    return html.Div(className="min-h-screen", children=[
        # Modern Header with Tailwind styling
        html.Header([
            html.Div([
                html.Div([
                    html.Div(className="h-6 w-6 rounded bg-brand-500"),
                    html.Div("Portfolio Performance Dashboard", className="text-sm text-ink-600 dark:text-slate-300"),
                    html.Span("Dev", className="text-[10px] font-semibold text-black bg-yellow-400 rounded px-1.5 py-0.5")
                ], className="flex items-center gap-3"),
                html.Div([
                    html.Button("Login/Register", id="login-btn", n_clicks=0,
                                className="px-2 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-ink-600 hover:bg-slate-100 dark:hover:bg-ink-700"),
                    html.Button(
                        id="profile-avatar-btn",
                        children="G",
                        n_clicks=0,
                        className="ml-2 h-8 w-8 rounded-full bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 flex items-center justify-center cursor-pointer",
                        title="Switch Profile"
                    ),
                    html.Button("Dark", id="theme-toggle", n_clicks=0,
                                className="ml-2 px-2 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-ink-600 hover:bg-slate-100 dark:hover:bg-ink-700"),
                    html.Button("Contact", id="contact-btn", n_clicks=0,
                                className="ml-2 px-2 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-ink-600 hover:bg-slate-100 dark:hover:bg-ink-700")
                ], className="flex items-center gap-2 text-ink-600 text-sm")
            ], className="flex h-14 items-center justify-between gap-3"),
            # Navigation tabs row - dynamically updated based on user role
            html.Nav(id="navigation-tabs-container", children=create_role_based_navigation(), 
                    className="flex items-center gap-2 overflow-x-auto py-2 text-sm text-ink-600 dark:text-slate-300")
        ], className="sticky top-0 z-40 bg-white/90 dark:bg-ink-800/80 backdrop-blur border-b border-slate-200 dark:border-ink-700 mx-auto max-w-[1600px] px-5"),
        
        # Main content with 3-column grid layout
        html.Main([
            html.Div(id='tab-content-container')
        ], className="mx-auto max-w-[1600px] px-5 py-4"),
        
        # Login/Register Modal
        html.Div([
            html.Div([
                html.H3("Login / Register", style={"marginBottom": "20px", "color": "#333", "textAlign": "center"}),
                dcc.Input(
                    id="username-input",
                    type="text",
                    placeholder="Enter username",
                    style={"width": "100%", "padding": "12px", "marginBottom": "15px", "border": "1px solid #ddd", "borderRadius": "4px", "fontSize": "16px"}
                ),
                html.Div([
                    html.Label("Select Role:", style={"fontSize": "14px", "fontWeight": "500", "marginBottom": "5px", "display": "block", "color": "#374151"}),
                    dcc.Dropdown(
                        id="role-dropdown",
                        options=[
                            {'label': 'Corp SCO', 'value': 'Corp SCO'},
                            {'label': 'CRE SCO', 'value': 'CRE SCO'},
                            {'label': 'SAG', 'value': 'SAG'},
                            {'label': 'BA', 'value': 'BA'}
                        ],
                        placeholder="Choose your role...",
                        style={"marginBottom": "20px"},
                        className="form-select"
                    )
                ]),
                html.Div([
                    html.Button("Login", id="login-submit", className="btn btn-primary", style={"marginRight": "10px", "padding": "10px 20px"}),
                    html.Button("Register", id="register-submit", className="btn btn-secondary", style={"marginRight": "10px", "padding": "10px 20px"}),
                    html.Button("Cancel", id="login-cancel", className="btn btn-outline", style={"padding": "10px 20px"})
                ], style={"textAlign": "center", "marginBottom": "30px"}),
                
                # Separator line
                html.Hr(style={"margin": "20px 0", "border": "1px solid #eee"}),
                
                # Delete Profile Section
                html.Div([
                    html.H4("Delete Profile", style={"marginBottom": "15px", "color": "#ef4444", "textAlign": "center", "fontSize": "18px"}),
                    dcc.Dropdown(
                        id="delete-profile-dropdown",
                        placeholder="Select profile to delete...",
                        style={"marginBottom": "15px"},
                        className="form-select"
                    ),
                    html.Div([
                        html.Button("Delete Profile", id="delete-profile-btn", className="btn btn-danger", style={"padding": "8px 16px"})
                    ], style={"textAlign": "center"})
                ], style={"marginTop": "20px"})
            ], style={
                "backgroundColor": "white",
                "padding": "40px",
                "borderRadius": "8px",
                "width": "400px",
                "maxWidth": "90vw",
                "position": "absolute",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",
                "boxShadow": "0 10px 25px rgba(0, 0, 0, 0.2)",
                "zIndex": "1001"
            })
        ], id="login-modal", style={
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100%",
            "height": "100%",
            "backgroundColor": "rgba(0, 0, 0, 0.5)",
            "zIndex": "1000",
            "display": "none"
        }),
        
        # Profile Switching Dialog
        html.Div([
            html.Div([
                html.H3("Switch Profile", style={"marginBottom": "20px", "color": "#333", "textAlign": "center"}),
                html.Div([
                    html.Label("Select Profile:", style={"fontSize": "14px", "fontWeight": "500", "marginBottom": "10px", "display": "block"}),
                    dcc.Dropdown(
                        id="profile-switch-dropdown",
                        placeholder="Choose a profile...",
                        style={"marginBottom": "20px"},
                        className="form-select"
                    )
                ]),
                html.Div([
                    html.Button("Switch", id="profile-switch-confirm", className="btn btn-primary", style={"marginRight": "10px", "padding": "10px 20px"}),
                    html.Button("Cancel", id="profile-switch-cancel", className="btn btn-outline", style={"padding": "10px 20px"})
                ], style={"textAlign": "center"})
            ], style={
                "backgroundColor": "white",
                "padding": "30px",
                "borderRadius": "8px",
                "width": "350px",
                "maxWidth": "90vw",
                "position": "absolute",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",
                "boxShadow": "0 10px 25px rgba(0, 0, 0, 0.2)",
                "zIndex": "1001"
            })
        ], id="profile-switch-modal", style={
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100%",
            "height": "100%",
            "backgroundColor": "rgba(0, 0, 0, 0.5)",
            "zIndex": "1000",
            "display": "none"
        }),
        
        # Contact Modal
        html.Div([
            html.Div([
                html.H3("Contact & Support", style={"marginBottom": "20px", "color": "#333", "textAlign": "center"}),
                
                # Contact Information Section
                html.Div([
                    html.H4("📧 Contact Information", style={"fontSize": "16px", "fontWeight": "600", "color": "#374151", "marginBottom": "15px"}),
                    html.P("For technical support and inquiries:", style={"marginBottom": "10px", "color": "#6B7280"}),
                    html.Div([
                        html.Strong("Email: "),
                        html.A("support@portfolio-dashboard.com", href="mailto:support@portfolio-dashboard.com", 
                              style={"color": "#2563EB", "textDecoration": "none"})
                    ], style={"marginBottom": "10px"}),
                    html.Div([
                        html.Strong("Phone: "),
                        html.Span("+1 (555) 123-4567")
                    ], style={"marginBottom": "20px"})
                ]),
                
                # Bug Report Section  
                html.Div([
                    html.H4("🐛 Report Issues", style={"fontSize": "16px", "fontWeight": "600", "color": "#374151", "marginBottom": "15px"}),
                    html.P("Found a bug or have feedback? Let us know!", style={"marginBottom": "15px", "color": "#6B7280"}),
                    html.A("Submit Bug Report", 
                          href="https://github.com/your-repo/issues/new", 
                          target="_blank",
                          className="inline-block px-4 py-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 transition-colors",
                          style={"textDecoration": "none", "marginBottom": "20px"})
                ]),
                
                # Feedback Section
                html.Div([
                    html.H4("💭 Feedback", style={"fontSize": "16px", "fontWeight": "600", "color": "#374151", "marginBottom": "15px"}),
                    html.P("Help us improve by sharing your thoughts:", style={"marginBottom": "15px", "color": "#6B7280"}),
                    html.A("Provide Feedback", 
                          href="https://forms.google.com/feedback-form", 
                          target="_blank",
                          className="inline-block px-4 py-2 bg-green-500 text-white text-sm rounded hover:bg-green-600 transition-colors",
                          style={"textDecoration": "none", "marginBottom": "20px"})
                ]),
                
                html.Div([
                    html.Button("Close", id="contact-close", className="btn btn-outline", style={"padding": "10px 20px"})
                ], style={"textAlign": "center"})
            ], style={
                "backgroundColor": "white",
                "padding": "30px",
                "borderRadius": "8px",
                "width": "400px",
                "maxWidth": "90vw",
                "position": "absolute",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",
                "boxShadow": "0 10px 25px rgba(0, 0, 0, 0.2)",
                "zIndex": "1001"
            })
        ], id="contact-modal", style={
            "position": "fixed",
            "top": "0",
            "left": "0",
            "width": "100%",
            "height": "100%",
            "backgroundColor": "rgba(0, 0, 0, 0.5)",
            "zIndex": "1000",
            "display": "none"
        }),
        
        # Auto-save Notification
        html.Div([
            html.Div([
                html.Span("💾", style={"marginRight": "8px", "fontSize": "16px"}),
                html.Span("Data auto-saved", id="save-message")
            ], style={
                "backgroundColor": "#10b981",
                "color": "white",
                "padding": "10px 20px",
                "borderRadius": "6px",
                "boxShadow": "0 2px 4px rgba(0, 0, 0, 0.1)",
                "fontSize": "14px",
                "fontWeight": "500"
            })
        ], id="save-notification", style={
            "position": "fixed",
            "bottom": "20px",
            "right": "20px",
            "zIndex": "1000",
            "opacity": "0",
            "transition": "opacity 0.3s ease"
        }),
        
        # Interval component for auto-save notifications
        dcc.Interval(
            id='auto-save-interval',
            interval=30*1000,  # 30 seconds
            n_intervals=0
        ),
        
        # Interval component for hiding notifications
        dcc.Interval(
            id='hide-notification-interval',
            interval=1*1000,  # 1 second
            n_intervals=0,
            disabled=True
        ),
        
        # Store component to track current user for navigation updates
        dcc.Store(id='current-user-store', data='Guest')
    ])

# Tab navigation callbacks
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
    """Update tab content based on button clicks"""
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
            create_portfolio_sidebar(selected_portfolio),
            html.Div(id='main-content-container', children=create_main_content(selected_portfolio)),
            html.Div(id='positions-panel-container', children=create_positions_panel(selected_portfolio))
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)_340px] gap-4")
    elif active_tab == 'holdings':
        content = html.Div([
            create_holdings_sidebar(selected_portfolio),
            create_holdings_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'financial-trends':
        content = html.Div([
            create_financial_trends_sidebar(selected_portfolio),
            create_financial_trends_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'financial-trend-details':
        content = html.Div([
            create_financial_trend_details_sidebar(selected_portfolio),
            create_financial_trend_details_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'vintage-analysis':
        content = html.Div([
            create_vintage_analysis_sidebar(selected_portfolio),
            create_vintage_analysis_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'sir-analysis':
        content = html.Div([
            create_sir_analysis_sidebar(selected_portfolio),
            create_sir_analysis_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'location-analysis':
        content = html.Div([
            create_location_analysis_sidebar(selected_portfolio),
            create_location_analysis_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'financial-projection':
        content = html.Div([
            create_financial_projection_sidebar(selected_portfolio),
            create_financial_projection_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    elif active_tab == 'model-backtesting':
        content = html.Div([
            create_model_backtesting_sidebar(selected_portfolio),
            create_model_backtesting_content(selected_portfolio)
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4")
    else:
        content = html.Div([
            create_portfolio_sidebar(selected_portfolio),
            html.Div(id='main-content-container', children=create_main_content(selected_portfolio)),
            html.Div(id='positions-panel-container', children=create_positions_panel(selected_portfolio))
        ], className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)_340px] gap-4")
    
    return content, summary_class, holdings_class, trends_class, details_class, vintage_class, sir_class, location_class, projection_class, backtesting_class

@callback(
    Output('navigation-tabs-container', 'children'),
    Input('current-user-store', 'data'),
    prevent_initial_call=True
)
def update_navigation_tabs(stored_user):
    """Update navigation tabs based on user role from store"""
    global current_user
    
    # Update the global current_user to match the stored value
    if stored_user:
        current_user = stored_user
    
    print(f"DEBUG: Navigation update triggered - stored_user: {stored_user}, current_user: {current_user}")
    return create_role_based_navigation()

@callback(
    Output('positions-panel-container', 'children'),
    Input('portfolio-dropdown', 'value'),
    prevent_initial_call=True
)
def update_positions_panel(selected_portfolio):
    """Update positions panel when portfolio selection changes"""
    if selected_portfolio is None:
        selected_portfolio = default_portfolio
    return create_positions_panel(selected_portfolio)


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
    
    portfolio_data = get_filtered_data(selected_portfolio)
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

# Only keep the original callbacks for Portfolio Summary, sidebar, and right column
@callback(
    Output('main-content-container', 'children'),
    Input('portfolio-dropdown', 'value'),
    prevent_initial_call=True
)
def update_main_content(selected_portfolio):
    if selected_portfolio is None:
        selected_portfolio = default_portfolio
    return create_main_content(selected_portfolio)

# Financial Trends callbacks
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
    metrics_options = get_portfolio_metrics(selected_portfolio)
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
    
    if not facilities_df.empty:
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
        
        # Create DataTable with test.py styling
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
    
    else:
        return html.Div("No data available", className="p-4 text-center text-ink-500")

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
    metrics = get_portfolio_metrics(selected_portfolio)
    
    # Create time series table
    time_series_content = []
    
    # Get unique reporting dates and format them
    reporting_dates = sorted(facility_data['reporting_date'].unique())
    formatted_dates = [pd.to_datetime(date).strftime('%Y-%m-%d') for date in reporting_dates]
    
    print(f"Debug: facility_id={facility_id}, reporting_dates={len(reporting_dates)}, dates={formatted_dates[:5]}")  # Debug line
    
    for metric in metrics:
        metric_value = metric['value']
        metric_label = metric['label']
        
        # Skip if metric doesn't have data
        if metric_value not in facility_data.columns:
            continue
            
        # Get metric values over time
        metric_data = []
        for date in reporting_dates:
            date_data = facility_data[facility_data['reporting_date'] == date]
            if len(date_data) > 0:
                value = date_data.iloc[0][metric_value]
                if pd.notna(value):
                    if isinstance(value, (int, float)):
                        if abs(value) >= 1000000:
                            metric_data.append(f"${value/1000000:.1f}M")
                        elif abs(value) >= 1000:
                            metric_data.append(f"${value/1000:.1f}K")
                        else:
                            metric_data.append(f"{value:.2f}")
                    else:
                        metric_data.append(str(value))
                else:
                    metric_data.append("N/A")
            else:
                metric_data.append("N/A")
        
        # Create row for this metric
        metric_row = html.Tr([
            html.Td(metric_label, 
                style={
                    "fontWeight": "bold", 
                    "backgroundColor": "#f8f9fa",
                    "position": "sticky",
                    "left": "0",
                    "minWidth": "150px",
                    "maxWidth": "150px"
                }
            ),
            *[html.Td(value, style={"textAlign": "center", "minWidth": "100px"}) for value in metric_data]
        ])
        
        time_series_content.append(metric_row)
    
    # Create table with dates as columns
    date_headers = [html.Th("Metric", style={
        "position": "sticky",
        "left": "0",
        "backgroundColor": "#8b5cf6",
        "zIndex": "10",
        "minWidth": "150px",
        "maxWidth": "150px"
    })] + [html.Th(date, style={"minWidth": "120px", "textAlign": "center"}) for date in formatted_dates]
    
    # Calculate table width based on number of columns
    table_width = 150 + (len(formatted_dates) * 120)  # 150px for metric column + 120px per date column
    
    time_series_table = html.Table([
        html.Thead([html.Tr(date_headers)]),
        html.Tbody(time_series_content)
    ], className="table time-series-table", style={
        "fontSize": "11px",
        "width": f"{table_width}px",
        "minWidth": f"{table_width}px",
        "tableLayout": "fixed"
    })
    
    return [html.Div([
        html.H5(f"Time Series for {facility_id} ({len(formatted_dates)} periods)", style={"marginBottom": "10px"}),
        html.Div([
            time_series_table
        ], style={
            "overflowX": "auto",
            "overflowY": "visible",
            "width": "100%",
            "maxWidth": "100%",
            "border": "1px solid #dee2e6",
            "borderRadius": "4px"
        })
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
    return create_holdings_filters(selected_portfolio)

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
        selected_portfolio, 
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
        selected_portfolio, 
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
        selected_portfolio, 
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
            updated_options = get_portfolio_metrics(selected_portfolio)
            
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
        metrics_options = get_portfolio_metrics(portfolio)
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
    global current_user, portfolios, custom_metrics
    
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
        profiles = load_profiles()
        delete_options = [{'label': name, 'value': name} for name in profiles.keys() if name != 'Guest']
        hidden_modal_style = {
            "position": "fixed", "top": "0", "left": "0", "width": "100%", 
            "height": "100%", "backgroundColor": "rgba(0, 0, 0, 0.5)", 
            "zIndex": "1000", "display": "none"
        }
        return hidden_modal_style, get_user_initials(current_user), delete_options
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Load current profiles
    profiles = load_profiles()
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
        return show_modal_style, get_user_initials(current_user), delete_options
    
    elif trigger_id == 'delete-profile-btn' and delete_profile_selection:
        # Delete profile using dropdown selection
        profiles = load_profiles()
        if delete_profile_selection in profiles and delete_profile_selection != 'Guest':
            del profiles[delete_profile_selection]
            save_profiles(profiles)
            
            # Switch back to Guest if deleting current user
            if current_user == delete_profile_selection:
                current_user = 'Guest'
                portfolios.clear()
                portfolios.update(DEFAULT_PORTFOLIOS.copy())
                custom_metrics.clear()
            
            # Update profile options and hide modal
            updated_delete_options = [{'label': name, 'value': name} for name in profiles.keys() if name != 'Guest']
            
            return hidden_modal_style, get_user_initials(current_user), updated_delete_options
        else:
            # Cannot delete Guest or non-existent profile
            return hidden_modal_style, get_user_initials(current_user), delete_options
    
    elif trigger_id == 'login-cancel':
        # Hide modal
        return hidden_modal_style, get_user_initials(current_user), delete_options
    
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
            save_profiles(profiles)
        
        # Switch to user
        current_user = username
        
        # Get user data and only use their custom portfolios if they have any
        user_data = get_user_data(username)
        user_portfolios = user_data.get('portfolios', {})
        
        # Clear current portfolios and custom metrics
        portfolios.clear()
        custom_metrics.clear()
        
        # Only add user's custom portfolios if they have any, otherwise use defaults
        if user_portfolios:
            portfolios.update(user_portfolios)
        else:
            portfolios.update(DEFAULT_PORTFOLIOS.copy())
        
        custom_metrics.update(user_data.get('custom_metrics', {}))
        
        # Hide modal and update profile options
        updated_delete_options = [{'label': name, 'value': name} for name in profiles.keys() if name != 'Guest']
        
        return hidden_modal_style, get_user_initials(current_user), updated_delete_options
    
    return hidden_modal_style, get_user_initials(current_user), delete_options

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
    global current_user, portfolios, custom_metrics
    
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Load profiles for dropdown options
    profiles = load_profiles()
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
        return show_modal_style, profile_options, current_user
    
    elif trigger_id == 'profile-switch-confirm' and selected_profile:
        # Switch to selected profile
        current_user = selected_profile
        
        # Get profile-specific portfolios
        if current_user == 'Guest':
            portfolios.clear()
            portfolios.update(DEFAULT_PORTFOLIOS.copy())
            custom_metrics.clear()
        else:
            user_data = get_user_data(current_user)
            portfolios.clear()
            user_portfolios = user_data.get('portfolios', {})
            if user_portfolios:
                portfolios.update(user_portfolios)
            else:
                portfolios.update(DEFAULT_PORTFOLIOS.copy())
            custom_metrics.clear()
            custom_metrics.update(user_data.get('custom_metrics', {}))
        
        # Hide modal
        return hidden_modal_style, profile_options, selected_profile
    
    elif trigger_id == 'profile-switch-cancel':
        # Hide modal without changes
        return hidden_modal_style, profile_options, current_user
    
    return hidden_modal_style, profile_options, current_user

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
        return username
    elif trigger_id == 'profile-switch-confirm' and selected_profile:
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
    global current_user, portfolios, custom_metrics
    
    if not confirm_clicks or not selected_profile:
        return no_update, no_update
    
    if selected_profile:
        current_user = selected_profile
        
        # Get profile-specific portfolios
        if current_user == 'Guest':
            portfolios.clear()
            portfolios.update(DEFAULT_PORTFOLIOS.copy())
            custom_metrics.clear()
            
            # Remove any custom metric columns from dataframe
            custom_metric_cols = [col for col in facilities_df.columns if col not in ['facility_id', 'obligor_name', 'balance', 'interest_rate', 'lob', 'industry', 'cre_property_type', 'obligor_rating', 'msa', 'origination_date', 'maturity_date', 'reporting_date', 'ltv', 'dscr', 'tier_1_capital_ratio', 'free_cash_flow', 'current_ratio', 'debt_to_equity', 'sir']]
            for col in custom_metric_cols:
                if col in facilities_df.columns:
                    facilities_df.drop(columns=[col], inplace=True)
        else:
            user_data = get_user_data(current_user)
            portfolios.clear()
            user_portfolios = user_data.get('portfolios', {})
            if user_portfolios:
                portfolios.update(user_portfolios)
            else:
                portfolios.update(DEFAULT_PORTFOLIOS.copy())
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
    [Output('save-notification', 'style'),
     Output('save-message', 'children'),
     Output('hide-notification-interval', 'disabled')],
    Input('auto-save-interval', 'n_intervals'),
    prevent_initial_call=True
)
def show_auto_save_notification(n_intervals):
    """Show auto-save notification"""
    if current_user != 'Guest' and n_intervals > 0:
        # Only save custom portfolios, not defaults
        user_data = get_user_data(current_user)
        user_custom_portfolios = user_data.get('portfolios', {})
        
        # Only save portfolios if the user actually has custom ones
        portfolios_to_save = user_custom_portfolios
        save_user_data(current_user, portfolios_to_save, custom_metrics)
        
        # Show notification and enable hide timer
        return ({
            "position": "fixed", "bottom": "20px", "right": "20px", 
            "zIndex": "1000", "opacity": "1", "transition": "opacity 0.3s ease",
            "display": "block"
        }, f"Profile '{current_user}' auto-saved", False)
    
    # Hide notification and disable timer
    return ({
        "position": "fixed", "bottom": "20px", "right": "20px", 
        "zIndex": "1000", "opacity": "0", "transition": "opacity 0.3s ease",
        "display": "none"
    }, "Data auto-saved", True)

# Auto-hide notification after 3 seconds
@callback(
    [Output('save-notification', 'style', allow_duplicate=True),
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

app.layout = create_layout()

# Dark mode toggle functionality
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


if __name__ == '__main__':
    print("Dash is running on http://127.0.0.1:8050/")
    app.run(debug=True, host='127.0.0.1', port=8050)
