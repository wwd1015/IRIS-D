"""
Financial Trend tab – period-over-period comparison tables.

Shows facility-level and grouped financial data comparing metrics
across reporting quarters with customizable lookback periods.
"""

from __future__ import annotations

import logging

from dash import html, dcc
import pandas as pd

from ..tabs.registry import BaseTab, TabContext, register_tab

logger = logging.getLogger(__name__)


class FinancialTrendTab(BaseTab):
    id = "financial-trend"
    label = "Financial Trend"
    order = 40

    # ── Sidebar ─────────────────────────────────────────────────────────────

    def render_sidebar(self, ctx: TabContext):
        return _create_financial_trend_sidebar(
            ctx.selected_portfolio,
            ctx.available_portfolios,
            ctx.portfolios,
            ctx.get_filtered_data,
            ctx.facilities_df,
        )

    # ── Content ─────────────────────────────────────────────────────────────

    def render_content(self, ctx: TabContext):
        return _create_financial_trend_content()

    # ── Callbacks ────────────────────────────────────────────────────────────

    def register_callbacks(self, app):
        # Import the singleton here to avoid circular imports during auto-discovery.
        from ..app_state import app_state
        from dash import Input, Output, callback, no_update

        @callback(
            Output("financial-trend-details-table", "children"),
            [Input("universal-portfolio-dropdown", "value"),
             Input("ft-view-dropdown", "value"),
             Input("ft-primary-period", "value"),
             Input("ft-comparison-period", "value"),
             Input("ft-custom-lookback", "value")],
            prevent_initial_call=True,
        )
        def update_details_table(
            portfolio, view_fields, primary_period, comparison_period, custom_lookback
        ):
            if not portfolio:
                return no_update
            return create_financial_trend_details_table(
                app_state.facilities_df,
                portfolio,
                app_state.portfolios,
                view_fields=view_fields,
                primary_period=primary_period,
                comparison_period=comparison_period,
                custom_lookback=custom_lookback or 1,
            )

        @callback(
            Output("ft-custom-lookback-container", "style"),
            Input("ft-comparison-period", "value"),
            prevent_initial_call=True,
        )
        def toggle_custom_lookback(comparison_period):
            return {"display": "block"} if comparison_period == "customized" else {"display": "none"}

        @callback(
            [Output("ft-view-dropdown", "options"),
             Output("ft-primary-period", "options"),
             Output("ft-primary-period", "value")],
            Input("universal-portfolio-dropdown", "value"),
            prevent_initial_call=True,
        )
        def update_sidebar_dropdowns(portfolio):
            if not portfolio:
                return no_update, no_update, no_update
            view_opts = _get_view_options(
                portfolio, app_state.portfolios, app_state.get_filtered_data
            )
            quarter_opts = _get_available_quarters(
                app_state.facilities_df, portfolio, app_state.portfolios
            )
            latest_q = quarter_opts[0]["value"] if quarter_opts else None
            return view_opts, quarter_opts, latest_q


register_tab(FinancialTrendTab())


# =============================================================================
# Private rendering helpers
# =============================================================================


def _create_financial_trend_sidebar(selected_portfolio, available_portfolios, portfolios, get_filtered_data, facilities_df):
    """Create redesigned sidebar for Financial Trend tab with portfolio-based dynamic filters"""
    return html.Section([
        html.Header([
            html.H2("Financial Trend", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700 flex items-center justify-between"),
        html.Div([
            # Portfolio dropdown moved to title bar - keeping this hidden for callback compatibility
            html.Div([
                dcc.Dropdown(
                    id='portfolio-dropdown',
                    options=[{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios],
                    value=selected_portfolio,
                    placeholder="Select portfolio...",
                    className="text-xs",
                    style={"fontSize": "12px", "display": "none"}
                )
            ], style={"display": "none"}),
            
            # View dropdown based on portfolio type
            html.Div([
                html.Label("View:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='ft-view-dropdown',
                    options=_get_view_options(selected_portfolio, portfolios, get_filtered_data),
                    value=[],
                    placeholder="Select view fields...",
                    className="text-xs",
                    style={"fontSize": "12px"},
                    multi=True
                )
            ], className="mb-4"),
            
            # Dynamic filters based on portfolio and view selection
            html.Div(id='financial-trend-dynamic-filters', children=_create_financial_trend_dynamic_filters(selected_portfolio, portfolios, get_filtered_data)),
            
            html.Hr(className="border-slate-200 dark:border-ink-700 mb-4"),
            
            # Primary period dropdown for report quarter selection
            html.Div([
                html.Label("Primary Period:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='ft-primary-period',
                    options=_get_available_quarters(facilities_df, selected_portfolio, portfolios),
                    value=_get_latest_quarter(facilities_df, selected_portfolio, portfolios),
                    placeholder="Select report quarter...",
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-4"),
            
            # Comparison period with prior quarter/year/customized options
            html.Div([
                html.Label("Comparison Period:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='ft-comparison-period',
                    options=[
                        {'label': 'Prior Quarter', 'value': 'prior_quarter'},
                        {'label': 'Prior Year', 'value': 'prior_year'},
                        {'label': 'Customized', 'value': 'customized'}
                    ],
                    value='prior_quarter',
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-4"),
            
            # Custom lookback period slider (1-12 quarters) - shown when customized is selected
            html.Div([
                html.Label("Custom Lookback (Quarters):", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Slider(
                    id='ft-custom-lookback',
                    min=1,
                    max=12,
                    step=1,
                    value=1,
                    marks={i: str(i) for i in [1, 4, 8, 12]},
                    tooltip={"placement": "bottom", "always_visible": True},
                    className="mb-2"
                ),
                html.Div("1 = Prior Quarter, 4 = Prior Year", className="text-xs text-ink-500 dark:text-slate-400")
            ], className="mb-4", id='ft-custom-lookback-container', style={'display': 'none'})
            
        ], className="p-4 flex-1 overflow-auto")
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden flex flex-col min-h-[640px]")


def _create_financial_trend_dynamic_filters(selected_portfolio, portfolios, get_filtered_data):
    """Create dynamic filters based on portfolio type"""
    if not selected_portfolio or selected_portfolio not in portfolios:
        return []
    # Return empty for now - the main filtering will be done through the View dropdown
    return []


def _get_view_options(selected_portfolio, portfolios, get_filtered_data):
    """Get view field types based on portfolio and data availability"""
    if not selected_portfolio or selected_portfolio not in portfolios:
        return []
    
    portfolio_data = get_filtered_data(selected_portfolio)
    if len(portfolio_data) == 0:
        return []
    
    view_options = []
    
    fields_to_check = [
        ('industry', 'Industry'),
        ('cre_property_type', 'Property Type'), 
        ('msa', 'MSA'),
        ('rating_buckets', 'Rating Buckets')
    ]
    
    for field_name, field_label in fields_to_check:
        if field_name == 'rating_buckets':
            if 'obligor_rating' in portfolio_data.columns:
                field_data = portfolio_data['obligor_rating'].dropna()
                if len(field_data) > 0:
                    view_options.append({'label': field_label, 'value': field_name})
        elif field_name in portfolio_data.columns:
            field_data = portfolio_data[field_name].dropna()
            if field_name in ['industry', 'cre_property_type', 'msa']:
                field_data = field_data[field_data.astype(str).str.strip() != '']
            if len(field_data) > 0:
                view_options.append({'label': field_label, 'value': field_name})
    
    return view_options


def _create_rating_buckets(rating_values):
    """Create meaningful rating buckets based on available rating values"""
    if not rating_values or len(rating_values) == 0:
        return {}
    
    min_rating = min(rating_values)
    max_rating = max(rating_values)
    
    buckets = {}
    if min_rating <= 13:
        buckets['Pass Rated (1-13)'] = (1, 13)
    if any(r == 14 for r in rating_values):
        buckets['Watch (14)'] = (14, 14)
    if any(15 <= r <= 16 for r in rating_values):
        buckets['Criticized (15-16)'] = (15, 16)
    if any(r == 17 for r in rating_values):
        buckets['Defaulted (17)'] = (17, 17)
    
    return buckets


def _get_rating_bucket(rating):
    """Convert a rating value to its bucket category (1-17 scale)"""
    if pd.isna(rating):
        return "Unknown"
    
    rating = int(rating)
    if rating <= 13:
        return "Pass Rated (1-13)"
    elif rating == 14:
        return "Watch (14)"
    elif 15 <= rating <= 16:
        return "Criticized (15-16)"
    elif rating == 17:
        return "Defaulted (17)"
    else:
        return "Unknown"


def _get_available_quarters(facilities_df, selected_portfolio, portfolios):
    """Get available quarters for the primary period dropdown"""
    if not selected_portfolio or selected_portfolio not in portfolios:
        return []
    
    df = facilities_df.copy()
    portfolio_criteria = portfolios[selected_portfolio]
    
    if portfolio_criteria.get('lob'):
        df = df[df['lob'] == portfolio_criteria['lob']]
    
    if portfolio_criteria.get('lob') == 'Corporate Banking' and portfolio_criteria.get('industry'):
        if isinstance(portfolio_criteria['industry'], list):
            df = df[df['industry'].astype(str).isin([str(i) for i in portfolio_criteria['industry']])]
        else:
            df = df[df['industry'] == portfolio_criteria['industry']]
    
    if portfolio_criteria.get('lob') == 'CRE' and portfolio_criteria.get('property_type'):
        if isinstance(portfolio_criteria['property_type'], list):
            df = df[df['cre_property_type'].astype(str).isin([str(i) for i in portfolio_criteria['property_type']])]
        else:
            df = df[df['cre_property_type'] == portfolio_criteria['property_type']]
    
    df['reporting_date'] = pd.to_datetime(df['reporting_date'])
    today = pd.Timestamp.now()
    df = df[df['reporting_date'] <= today]
    df['quarter'] = df['reporting_date'].dt.to_period('Q')
    
    unique_quarters = sorted(df['quarter'].dropna().unique(), reverse=True)
    
    quarter_options = []
    for quarter in unique_quarters:
        quarter_str = str(quarter)
        quarter_options.append({'label': quarter_str, 'value': quarter_str})
    
    return quarter_options


def _get_latest_quarter(facilities_df, selected_portfolio, portfolios):
    """Get the latest quarter from available quarters for default selection"""
    quarter_options = _get_available_quarters(facilities_df, selected_portfolio, portfolios)
    if quarter_options:
        return quarter_options[0]['value']
    return None


def _create_financial_trend_content():
    """Create dynamic Financial Trend content with real table"""
    return html.Div([
        html.Div([
            html.Div(id='financial-trend-details-table', children="Select portfolio and periods to view data")
        ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden")
    ], className="main-content")


def create_financial_trend_details_table(facilities_df, selected_portfolio, portfolios, view_fields=None, primary_period=None, comparison_period=None, custom_lookback=1):
    """Create dynamic Financial Trend Details table based on selections.
    
    Note: This is called from app.py callbacks, so it keeps its public name.
    """
    
    if not selected_portfolio or selected_portfolio not in portfolios:
        return html.Div("Please select a portfolio to view data.", className="p-4 text-center text-ink-500")
    
    if not primary_period:
        return html.Div("Please select a primary period to view data.", className="p-4 text-center text-ink-500")
    
    portfolio_criteria = portfolios[selected_portfolio]
    df = facilities_df.copy()
    
    if portfolio_criteria.get('lob'):
        df = df[df['lob'] == portfolio_criteria['lob']]
    
    if portfolio_criteria.get('lob') == 'Corporate Banking' and portfolio_criteria.get('industry'):
        if isinstance(portfolio_criteria['industry'], list):
            df = df[df['industry'].astype(str).isin([str(i) for i in portfolio_criteria['industry']])]
        else:
            df = df[df['industry'] == portfolio_criteria['industry']]
    
    if portfolio_criteria.get('lob') == 'CRE' and portfolio_criteria.get('property_type'):
        if isinstance(portfolio_criteria['property_type'], list):
            df = df[df['cre_property_type'].astype(str).isin([str(i) for i in portfolio_criteria['property_type']])]
        else:
            df = df[df['cre_property_type'] == portfolio_criteria['property_type']]
    
    if len(df) == 0:
        return html.Div("No data available for selected portfolio.", className="p-4 text-center text-ink-500")
    
    comparison_quarter = _calculate_comparison_period(primary_period, comparison_period, custom_lookback)
    
    primary_data = _get_period_data(df, primary_period)
    comparison_data = _get_period_data(df, comparison_quarter) if comparison_quarter else pd.DataFrame()
    
    if not view_fields or len(view_fields) == 0:
        return _build_facility_level_table(primary_data, comparison_data, primary_period, comparison_quarter, portfolio_criteria['lob'])
    else:
        return _build_grouped_table(primary_data, comparison_data, view_fields, primary_period, comparison_quarter, portfolio_criteria['lob'])


def _calculate_comparison_period(primary_period, comparison_period, custom_lookback):
    """Calculate the comparison period quarter based on selection"""
    if not primary_period or not comparison_period:
        return None
    
    try:
        primary_quarter = pd.Period(primary_period)
        
        if comparison_period == 'prior_quarter':
            return str(primary_quarter - 1)
        elif comparison_period == 'prior_year':
            return str(primary_quarter - 4)
        elif comparison_period == 'customized':
            lookback = custom_lookback if custom_lookback is not None else 1
            return str(primary_quarter - lookback)
        
    except Exception as e:
        logger.warning("Error calculating comparison period: %s", e)
    
    return None


def _get_period_data(df, period_str):
    """Get data for a specific period"""
    if not period_str:
        return pd.DataFrame()
    
    try:
        df = df.copy()
        df['reporting_date'] = pd.to_datetime(df['reporting_date'])
        df['quarter'] = df['reporting_date'].dt.to_period('Q')
        
        period_data = df[df['quarter'] == pd.Period(period_str)]
        return period_data.reset_index(drop=True)
    
    except Exception as e:
        logger.warning("Error getting period data: %s", e)
        return pd.DataFrame()


def _build_facility_level_table(primary_data, comparison_data, primary_period, comparison_period, lob):
    """Build facility-level table when no view is selected"""
    
    if len(primary_data) == 0:
        return html.Div("No data available for selected period.", className="p-4 text-center text-ink-500")
    
    common_cols = ['facility_id', 'obligor_name', 'lob', 'obligor_rating']
    
    if lob == 'Corporate Banking':
        lob_cols = ['industry']
        metric_cols = ['balance', 'free_cash_flow', 'fixed_charge_coverage', 'cash_flow_leverage', 'liquidity', 'profitability', 'growth']
    elif lob == 'CRE':
        lob_cols = ['cre_property_type', 'msa']
        metric_cols = ['balance', 'noi', 'property_value', 'dscr', 'ltv']
    else:
        lob_cols = ['industry', 'cre_property_type', 'msa']
        metric_cols = ['balance', 'free_cash_flow', 'fixed_charge_coverage', 'cash_flow_leverage', 'liquidity', 'profitability', 'growth', 'noi', 'property_value', 'dscr', 'ltv']
    
    available_metrics = [col for col in metric_cols if col in primary_data.columns]
    
    table_rows = []
    
    for _, facility in primary_data.iterrows():
        row_data = {}
        
        for col in common_cols:
            if col in facility:
                row_data[col] = facility[col]
        
        for col in lob_cols:
            if col in facility:
                row_data[col] = facility[col]
        
        for metric in available_metrics:
            primary_val = facility.get(metric, None)
            row_data[f"{metric}_{primary_period}"] = primary_val
            
            if len(comparison_data) > 0 and comparison_period:
                comp_facility = comparison_data[comparison_data['facility_id'] == facility['facility_id']]
                if len(comp_facility) > 0:
                    comp_val = comp_facility.iloc[0].get(metric, None)
                    row_data[f"{metric}_{comparison_period}"] = comp_val
                    
                    if pd.notna(primary_val) and pd.notna(comp_val) and comp_val != 0:
                        change_pct = ((primary_val - comp_val) / comp_val) * 100
                        row_data[f"{metric}_change_pct"] = change_pct
                    else:
                        row_data[f"{metric}_change_pct"] = None
                else:
                    row_data[f"{metric}_{comparison_period}"] = None
                    row_data[f"{metric}_change_pct"] = None
        
        table_rows.append(row_data)
    
    if table_rows:
        return _create_html_table(table_rows, primary_period, comparison_period, is_grouped=False)
    else:
        return html.Div("No data to display.", className="p-4 text-center text-ink-500")


def _build_grouped_table(primary_data, comparison_data, view_fields, primary_period, comparison_period, lob):
    """Build grouped table when view fields are selected"""
    
    if len(primary_data) == 0:
        return html.Div("No data available for selected period.", className="p-4 text-center text-ink-500")
    
    try:
        data_for_grouping = primary_data.copy()
        actual_grouping_fields = []
        
        for field in view_fields:
            if field == 'rating_buckets':
                if 'obligor_rating' in data_for_grouping.columns:
                    data_for_grouping['rating_buckets'] = data_for_grouping['obligor_rating'].apply(_get_rating_bucket)
                    actual_grouping_fields.append('rating_buckets')
            elif field in data_for_grouping.columns:
                actual_grouping_fields.append(field)
        
        if not actual_grouping_fields:
            return html.Div("Selected view fields not available in data.", className="p-4 text-center text-ink-500")
        
        grouped = data_for_grouping.groupby(actual_grouping_fields)
        
        table_rows = []
        
        for group_key, group_data in grouped:
            if len(actual_grouping_fields) == 1:
                field_name = actual_grouping_fields[0]
                display_name = 'Rating Buckets' if field_name == 'rating_buckets' else field_name.replace('_', ' ').title()
                group_title = f"{display_name}: {group_key}"
            else:
                group_parts = []
                for field, val in zip(actual_grouping_fields, group_key):
                    display_name = 'Rating Buckets' if field == 'rating_buckets' else field.replace('_', ' ').title()
                    group_parts.append(f"{display_name}: {val}")
                group_title = " | ".join(group_parts)
            
            header_row = {'group_header': True, 'group_title': group_title}
            table_rows.append(header_row)
            
            for _, facility in group_data.iterrows():
                facility_row = _build_facility_row(facility, comparison_data, primary_period, comparison_period, lob, is_grouped=True)
                table_rows.append(facility_row)
        
        return _create_html_table(table_rows, primary_period, comparison_period, is_grouped=True)
        
    except Exception as e:
        logger.warning("Error building grouped table: %s", e)
        return html.Div("Error creating grouped view.", className="p-4 text-center text-ink-500")


def _build_facility_row(facility, comparison_data, primary_period, comparison_period, lob, is_grouped=False):
    """Build a single facility row"""
    row_data = {'is_facility': True, 'is_grouped': is_grouped}
    
    row_data['facility_id'] = facility.get('facility_id', '')
    row_data['obligor_name'] = facility.get('obligor_name', '')
    row_data['obligor_rating'] = facility.get('obligor_rating', '')
    
    if lob == 'Corporate Banking':
        row_data['industry'] = facility.get('industry', '')
        metric_cols = ['balance', 'free_cash_flow', 'fixed_charge_coverage', 'cash_flow_leverage', 'liquidity', 'profitability', 'growth']
    elif lob == 'CRE':
        row_data['cre_property_type'] = facility.get('cre_property_type', '')
        row_data['msa'] = facility.get('msa', '')
        metric_cols = ['balance', 'noi', 'property_value', 'dscr', 'ltv']
    else:
        metric_cols = ['balance', 'free_cash_flow', 'fixed_charge_coverage', 'cash_flow_leverage', 'liquidity', 'profitability', 'growth', 'noi', 'property_value', 'dscr', 'ltv']
    
    for metric in metric_cols:
        if metric in facility:
            primary_val = facility.get(metric, None)
            row_data[f"{metric}_{primary_period}"] = primary_val
            
            if len(comparison_data) > 0 and comparison_period:
                comp_facility = comparison_data[comparison_data['facility_id'] == facility['facility_id']]
                if len(comp_facility) > 0:
                    comp_val = comp_facility.iloc[0].get(metric, None)
                    row_data[f"{metric}_{comparison_period}"] = comp_val
                    
                    if pd.notna(primary_val) and pd.notna(comp_val) and comp_val != 0:
                        change_pct = ((primary_val - comp_val) / comp_val) * 100
                        row_data[f"{metric}_change_pct"] = change_pct
    
    return row_data


def _create_html_table(table_rows, primary_period, comparison_period, is_grouped=False):
    """Create unified HTML table for both grouped and non-grouped data with frozen headers"""
    
    if not table_rows:
        return html.Div("No data available.", className="p-4 text-center text-ink-500")
    
    sample_facility = None
    for row in table_rows:
        if is_grouped and row.get('is_facility'):
            sample_facility = row
            break
        elif not is_grouped:
            sample_facility = row
            break
    
    if not sample_facility:
        return html.Div("No facility data available.", className="p-4 text-center text-ink-500")
    
    header_columns = ['Facility ID', 'Obligor Name', 'Rating']
    
    if 'industry' in sample_facility:
        header_columns.append('Industry')
    if 'cre_property_type' in sample_facility:
        header_columns.append('Property Type')
    if 'msa' in sample_facility:
        header_columns.append('MSA')
    
    metric_headers = []
    excluded_keys = ['is_facility', 'is_grouped', 'facility_id', 'obligor_name', 'obligor_rating', 'industry', 'cre_property_type', 'msa', 'lob']
    
    for key in sample_facility.keys():
        if key not in excluded_keys:
            if key.endswith('_change_pct'):
                metric_name = key.replace('_change_pct', '').replace('_', ' ').title()
                metric_headers.append(f"{metric_name} Change %")
            elif '_' in key and not key.endswith('_change_pct'):
                parts = key.split('_')
                if len(parts) >= 2:
                    metric_name = '_'.join(parts[:-1]).replace('_', ' ').title()
                    period = parts[-1]
                    metric_headers.append(f"{metric_name} ({period})")
    
    header_columns.extend(metric_headers)
    
    header_row = html.Tr([
        html.Th(col, style={
            'backgroundColor': '#f8fafc',
            'borderBottom': '1px solid #e6ebf2',
            'fontWeight': '600',
            'textAlign': 'left',
            'padding': '10px 12px',
            'color': '#475569',
            'fontFamily': 'Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif',
            'fontSize': '13px',
            'position': 'sticky',
            'top': 0,
            'zIndex': 10,
            'boxShadow': '0 2px 2px -1px rgba(0,0,0,0.1)'
        }) for col in header_columns
    ])
    
    body_rows = []
    
    for row in table_rows:
        if is_grouped and row.get('group_header'):
            body_rows.append(
                html.Tr([
                    html.Td(
                        row['group_title'], 
                        colSpan=len(header_columns),
                        style={
                            'backgroundColor': '#f3f4f6',
                            'fontWeight': 'bold',
                            'padding': '12px',
                            'borderBottom': '2px solid #d1d5db',
                            'fontSize': '14px',
                            'fontFamily': 'Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif',
                        }
                    )
                ], style={'backgroundColor': '#f3f4f6'})
            )
        else:
            cells = []
            
            facility_style = {
                'padding': '10px 12px', 
                'fontSize': '13px',
                'fontFamily': 'Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif',
                'borderBottom': '1px solid #f1f5f9'
            }
            
            if is_grouped and (row.get('is_grouped') or row.get('is_facility')):
                facility_style['paddingLeft'] = '24px'
            
            cells.append(html.Td(row.get('facility_id', ''), style=facility_style))
            
            cell_style = {
                'padding': '10px 12px', 
                'fontSize': '13px',
                'fontFamily': 'Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif',
                'borderBottom': '1px solid #f1f5f9'
            }
            
            cells.append(html.Td(row.get('obligor_name', ''), style=cell_style))
            cells.append(html.Td(row.get('obligor_rating', ''), style=cell_style))
            
            if 'industry' in sample_facility:
                cells.append(html.Td(row.get('industry', ''), style=cell_style))
            if 'cre_property_type' in sample_facility:
                cells.append(html.Td(row.get('cre_property_type', ''), style=cell_style))
            if 'msa' in sample_facility:
                cells.append(html.Td(row.get('msa', ''), style=cell_style))
            
            for key in sample_facility.keys():
                if key not in excluded_keys:
                    value = row.get(key, '')
                    metric_cell_style = cell_style.copy()
                    
                    if isinstance(value, (int, float)) and pd.notna(value):
                        if 'change_pct' in key:
                            formatted_value = f"{value:+.1f}%"
                            metric_cell_style['color'] = '#0f9d58' if value > 0 else '#d93025' if value < 0 else '#6b7280'
                        else:
                            formatted_value = f"{value:,.2f}" if 'balance' not in key and 'value' not in key else f"{value:,.0f}"
                            metric_cell_style['color'] = '#374151'
                    else:
                        formatted_value = str(value) if value else ""
                        metric_cell_style['color'] = '#374151'
                    
                    cells.append(html.Td(formatted_value, style=metric_cell_style))
            
            body_rows.append(html.Tr(cells))
    
    table = html.Table([
        html.Thead([header_row]),
        html.Tbody(body_rows)
    ], style={
        'borderCollapse': 'collapse',
        'width': '100%',
        'minWidth': '1200px'
    })
    
    return html.Div([
        table
    ], style={
        'overflowX': 'auto',
        'overflowY': 'auto',
        'maxHeight': '70vh',
        'position': 'relative'
    })
