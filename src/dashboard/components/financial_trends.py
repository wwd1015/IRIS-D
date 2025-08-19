from dash import html, dcc, dash_table
import pandas as pd


def create_financial_trend_sidebar(selected_portfolio, available_portfolios, portfolios, get_filtered_data, facilities_df):
    """Create redesigned sidebar for Financial Trend tab with portfolio-based dynamic filters"""
    return html.Section([
        html.Header([
            html.H2("Financial Trend", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700 flex items-center justify-between"),
        html.Div([
            # Portfolio dropdown - first item as requested
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
            
            # View dropdown based on portfolio type
            html.Div([
                html.Label("View:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='ft-view-dropdown',
                    options=get_view_options(selected_portfolio, portfolios, get_filtered_data),  # Populate with initial options
                    value=[],
                    placeholder="Select view fields...",
                    className="text-xs",
                    style={"fontSize": "12px"},
                    multi=True  # Enable multiple selection
                )
            ], className="mb-4"),
            
            # Dynamic filters based on portfolio and view selection
            html.Div(id='financial-trend-dynamic-filters', children=create_financial_trend_dynamic_filters(selected_portfolio, portfolios, get_filtered_data)),
            
            html.Hr(className="border-slate-200 dark:border-ink-700 mb-4"),
            
            # Primary period dropdown for report quarter selection
            html.Div([
                html.Label("Primary Period:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='ft-primary-period',
                    options=get_available_quarters(facilities_df, selected_portfolio, portfolios),  # Populate with initial options
                    value=get_latest_quarter(facilities_df, selected_portfolio, portfolios),  # Set default to latest quarter
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


def create_financial_trend_dynamic_filters(selected_portfolio, portfolios, get_filtered_data):
    """Create dynamic filters based on portfolio type - these are now for additional filtering beyond the main view"""
    if not selected_portfolio or selected_portfolio not in portfolios:
        return []
    
    # Return empty for now - the main filtering will be done through the View dropdown
    # Additional filters can be added here if needed for further refinement
    return []


def get_view_options(selected_portfolio, portfolios, get_filtered_data):
    """Get view field types based on portfolio and data availability"""
    if not selected_portfolio or selected_portfolio not in portfolios:
        return []
    
    portfolio_data = get_filtered_data(selected_portfolio)
    if len(portfolio_data) == 0:
        return []
    
    view_options = []
    
    # Check each potential field for data availability (non-empty, non-null values)
    fields_to_check = [
        ('industry', 'Industry'),
        ('cre_property_type', 'Property Type'), 
        ('msa', 'MSA'),
        ('rating_buckets', 'Rating Buckets')  # Special field for rating bucket grouping
    ]
    
    for field_name, field_label in fields_to_check:
        # Special handling for rating_buckets - check if obligor_rating exists instead
        if field_name == 'rating_buckets':
            if 'obligor_rating' in portfolio_data.columns:
                field_data = portfolio_data['obligor_rating'].dropna()
                if len(field_data) > 0:
                    view_options.append({
                        'label': field_label, 
                        'value': field_name
                    })
        elif field_name in portfolio_data.columns:
            # Check if field has populated data (non-null, non-empty values)
            field_data = portfolio_data[field_name].dropna()
            
            # Additional check for empty strings
            if field_name in ['industry', 'cre_property_type', 'msa']:
                field_data = field_data[field_data.astype(str).str.strip() != '']
            
            if len(field_data) > 0:
                # Only add the field type, not the specific values
                view_options.append({
                    'label': field_label, 
                    'value': field_name
                })
    
    return view_options


def create_rating_buckets(rating_values):
    """Create meaningful rating buckets based on available rating values"""
    if not rating_values or len(rating_values) == 0:
        return {}
    
    min_rating = min(rating_values)
    max_rating = max(rating_values)
    
    buckets = {}
    
    # Create buckets based on rating categorization (1-17 scale)
    if min_rating <= 13:
        buckets['Pass Rated (1-13)'] = (1, 13)
    if any(r == 14 for r in rating_values):
        buckets['Watch (14)'] = (14, 14)
    if any(15 <= r <= 16 for r in rating_values):
        buckets['Criticized (15-16)'] = (15, 16)
    if any(r == 17 for r in rating_values):
        buckets['Defaulted (17)'] = (17, 17)
    
    return buckets


def get_rating_bucket(rating):
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


def get_available_quarters(facilities_df, selected_portfolio, portfolios):
    """Get available quarters for the primary period dropdown"""
    if not selected_portfolio or selected_portfolio not in portfolios:
        return []
    
    # Filter data by portfolio
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
    
    # Get unique reporting dates and convert to quarters
    df['reporting_date'] = pd.to_datetime(df['reporting_date'])
    
    # Filter out future dates (only include dates up to today)
    today = pd.Timestamp.now()
    df = df[df['reporting_date'] <= today]
    
    df['quarter'] = df['reporting_date'].dt.to_period('Q')
    
    unique_quarters = sorted(df['quarter'].dropna().unique(), reverse=True)
    
    # Convert to options for dropdown
    quarter_options = []
    for quarter in unique_quarters:
        quarter_str = str(quarter)
        quarter_options.append({'label': quarter_str, 'value': quarter_str})
    
    return quarter_options


def get_latest_quarter(facilities_df, selected_portfolio, portfolios):
    """Get the latest quarter from available quarters for default selection"""
    quarter_options = get_available_quarters(facilities_df, selected_portfolio, portfolios)
    if quarter_options:
        # Return the first quarter (most recent due to reverse=True sorting)
        return quarter_options[0]['value']
    return None


def create_financial_trend_content():
    """Create dynamic Financial Trend content with real table"""
    return html.Div([
        # Dynamic table container with consistent background styling
        html.Div([
            html.Div(id='financial-trend-details-table', children="Select portfolio and periods to view data")
        ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden")
    ], className="main-content")


def create_financial_trend_details_table(facilities_df, selected_portfolio, portfolios, view_fields=None, primary_period=None, comparison_period=None, custom_lookback=1):
    """Create dynamic Financial Trend Details table based on selections"""
    
    if not selected_portfolio or selected_portfolio not in portfolios:
        return html.Div("Please select a portfolio to view data.", className="p-4 text-center text-ink-500")
    
    if not primary_period:
        return html.Div("Please select a primary period to view data.", className="p-4 text-center text-ink-500")
    
    # Get portfolio data
    portfolio_criteria = portfolios[selected_portfolio]
    df = facilities_df.copy()
    
    # Apply portfolio filters
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
    
    # Calculate comparison period
    comparison_quarter = calculate_comparison_period(primary_period, comparison_period, custom_lookback)
    
    # Get data for both periods
    primary_data = get_period_data(df, primary_period)
    comparison_data = get_period_data(df, comparison_quarter) if comparison_quarter else pd.DataFrame()
    
    # Build and return table directly
    if not view_fields or len(view_fields) == 0:
        return build_facility_level_table(primary_data, comparison_data, primary_period, comparison_quarter, portfolio_criteria['lob'])
    else:
        return build_grouped_table(primary_data, comparison_data, view_fields, primary_period, comparison_quarter, portfolio_criteria['lob'])




def calculate_comparison_period(primary_period, comparison_period, custom_lookback):
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
            # Ensure custom_lookback is a valid number
            lookback = custom_lookback if custom_lookback is not None else 1
            print(f"DEBUG: Custom lookback calculation - primary: {primary_period}, lookback: {lookback}")
            result = str(primary_quarter - lookback)
            print(f"DEBUG: Calculated comparison period: {result}")
            return result
        
    except Exception as e:
        print(f"Error calculating comparison period: {e}")
        print(f"DEBUG: primary_period={primary_period}, comparison_period={comparison_period}, custom_lookback={custom_lookback}")
    
    return None


def get_period_data(df, period_str):
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
        print(f"Error getting period data: {e}")
        return pd.DataFrame()


def build_facility_level_table(primary_data, comparison_data, primary_period, comparison_period, lob):
    """Build facility-level table when no view is selected"""
    
    if len(primary_data) == 0:
        return html.Div("No data available for selected period.", className="p-4 text-center text-ink-500")
    
    # Define columns based on LOB
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
    
    # Filter metrics to only those available in data
    available_metrics = [col for col in metric_cols if col in primary_data.columns]
    
    # Build table rows
    table_rows = []
    
    for _, facility in primary_data.iterrows():
        row_data = {}
        
        # Add common columns
        for col in common_cols:
            if col in facility:
                row_data[col] = facility[col]
        
        # Add LOB-specific columns
        for col in lob_cols:
            if col in facility:
                row_data[col] = facility[col]
        
        # Add metric columns with periods
        for metric in available_metrics:
            # Primary period value
            primary_val = facility.get(metric, None)
            row_data[f"{metric}_{primary_period}"] = primary_val
            
            # Comparison period value and change
            if len(comparison_data) > 0 and comparison_period:
                comp_facility = comparison_data[comparison_data['facility_id'] == facility['facility_id']]
                if len(comp_facility) > 0:
                    comp_val = comp_facility.iloc[0].get(metric, None)
                    row_data[f"{metric}_{comparison_period}"] = comp_val
                    
                    # Calculate change percentage
                    if pd.notna(primary_val) and pd.notna(comp_val) and comp_val != 0:
                        change_pct = ((primary_val - comp_val) / comp_val) * 100
                        row_data[f"{metric}_change_pct"] = change_pct
                    else:
                        row_data[f"{metric}_change_pct"] = None
                else:
                    row_data[f"{metric}_{comparison_period}"] = None
                    row_data[f"{metric}_change_pct"] = None
        
        table_rows.append(row_data)
    
    # Convert to HTML table for consistent styling
    if table_rows:
        return create_html_table(table_rows, primary_period, comparison_period, is_grouped=False)
    else:
        return html.Div("No data to display.", className="p-4 text-center text-ink-500")


def build_grouped_table(primary_data, comparison_data, view_fields, primary_period, comparison_period, lob):
    """Build grouped table when view fields are selected"""
    
    if len(primary_data) == 0:
        return html.Div("No data available for selected period.", className="p-4 text-center text-ink-500")
    
    # Group data by view fields
    try:
        # Handle special rating_buckets field and create grouping columns
        data_for_grouping = primary_data.copy()
        actual_grouping_fields = []
        
        for field in view_fields:
            if field == 'rating_buckets':
                # Create rating bucket column based on obligor_rating
                if 'obligor_rating' in data_for_grouping.columns:
                    data_for_grouping['rating_buckets'] = data_for_grouping['obligor_rating'].apply(get_rating_bucket)
                    actual_grouping_fields.append('rating_buckets')
            elif field in data_for_grouping.columns:
                actual_grouping_fields.append(field)
        
        if not actual_grouping_fields:
            return html.Div("Selected view fields not available in data.", className="p-4 text-center text-ink-500")
        
        # Group data
        grouped = data_for_grouping.groupby(actual_grouping_fields)
        
        table_rows = []
        
        for group_key, group_data in grouped:
            # Add group header row
            if len(actual_grouping_fields) == 1:
                field_name = actual_grouping_fields[0]
                # Special display name for rating_buckets
                if field_name == 'rating_buckets':
                    display_name = 'Rating Buckets'
                else:
                    display_name = field_name.replace('_', ' ').title()
                group_title = f"{display_name}: {group_key}"
            else:
                group_parts = []
                for field, val in zip(actual_grouping_fields, group_key):
                    if field == 'rating_buckets':
                        display_name = 'Rating Buckets'
                    else:
                        display_name = field.replace('_', ' ').title()
                    group_parts.append(f"{display_name}: {val}")
                group_title = " | ".join(group_parts)
            
            # Add group header
            header_row = {'group_header': True, 'group_title': group_title}
            table_rows.append(header_row)
            
            # Add facility rows for this group (indented)
            for _, facility in group_data.iterrows():
                facility_row = build_facility_row(facility, comparison_data, primary_period, comparison_period, lob, is_grouped=True)
                table_rows.append(facility_row)
        
        return create_html_table(table_rows, primary_period, comparison_period, is_grouped=True)
        
    except Exception as e:
        print(f"Error building grouped table: {e}")
        return html.Div("Error creating grouped view.", className="p-4 text-center text-ink-500")


def build_facility_row(facility, comparison_data, primary_period, comparison_period, lob, is_grouped=False):
    """Build a single facility row"""
    row_data = {'is_facility': True, 'is_grouped': is_grouped}
    
    # Basic facility info
    row_data['facility_id'] = facility.get('facility_id', '')
    row_data['obligor_name'] = facility.get('obligor_name', '')
    row_data['obligor_rating'] = facility.get('obligor_rating', '')
    
    # LOB-specific fields
    if lob == 'Corporate Banking':
        row_data['industry'] = facility.get('industry', '')
        metric_cols = ['balance', 'free_cash_flow', 'fixed_charge_coverage', 'cash_flow_leverage', 'liquidity', 'profitability', 'growth']
    elif lob == 'CRE':
        row_data['cre_property_type'] = facility.get('cre_property_type', '')
        row_data['msa'] = facility.get('msa', '')
        metric_cols = ['balance', 'noi', 'property_value', 'dscr', 'ltv']
    else:
        metric_cols = ['balance', 'free_cash_flow', 'fixed_charge_coverage', 'cash_flow_leverage', 'liquidity', 'profitability', 'growth', 'noi', 'property_value', 'dscr', 'ltv']
    
    # Add metrics with time periods
    for metric in metric_cols:
        if metric in facility:
            primary_val = facility.get(metric, None)
            row_data[f"{metric}_{primary_period}"] = primary_val
            
            # Comparison data
            if len(comparison_data) > 0 and comparison_period:
                comp_facility = comparison_data[comparison_data['facility_id'] == facility['facility_id']]
                if len(comp_facility) > 0:
                    comp_val = comp_facility.iloc[0].get(metric, None)
                    row_data[f"{metric}_{comparison_period}"] = comp_val
                    
                    # Calculate change
                    if pd.notna(primary_val) and pd.notna(comp_val) and comp_val != 0:
                        change_pct = ((primary_val - comp_val) / comp_val) * 100
                        row_data[f"{metric}_change_pct"] = change_pct
    
    return row_data


def create_html_table(table_rows, primary_period, comparison_period, is_grouped=False):
    """Create unified HTML table for both grouped and non-grouped data with frozen headers"""
    
    if not table_rows:
        return html.Div("No data available.", className="p-4 text-center text-ink-500")
    
    # Extract a sample row to get column structure
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
    
    # Define header columns based on available data
    header_columns = []
    
    # Basic columns
    header_columns.extend(['Facility ID', 'Obligor Name', 'Rating'])
    
    # LOB-specific columns
    if 'industry' in sample_facility:
        header_columns.append('Industry')
    if 'cre_property_type' in sample_facility:
        header_columns.append('Property Type')
    if 'msa' in sample_facility:
        header_columns.append('MSA')
    
    # Metric columns - build from actual data keys
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
    
    # Create table header with frozen positioning
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
            'boxShadow': '0 2px 2px -1px rgba(0,0,0,0.1)'  # Add shadow for better separation
        }) for col in header_columns
    ])
    
    # Create body rows
    body_rows = []
    
    for row in table_rows:
        if is_grouped and row.get('group_header'):
            # Group header row (only for grouped tables)
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
            # Regular facility row
            cells = []
            
            # Facility ID (indented if grouped)
            facility_style = {
                'padding': '10px 12px', 
                'fontSize': '13px',
                'fontFamily': 'Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif',
                'borderBottom': '1px solid #f1f5f9'
            }
            
            # Add indentation for grouped facilities
            if is_grouped and (row.get('is_grouped') or row.get('is_facility')):
                facility_style['paddingLeft'] = '24px'
            
            cells.append(html.Td(row.get('facility_id', ''), style=facility_style))
            
            # Standard cell style
            cell_style = {
                'padding': '10px 12px', 
                'fontSize': '13px',
                'fontFamily': 'Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif',
                'borderBottom': '1px solid #f1f5f9'
            }
            
            cells.append(html.Td(row.get('obligor_name', ''), style=cell_style))
            cells.append(html.Td(row.get('obligor_rating', ''), style=cell_style))
            
            # LOB-specific columns
            if 'industry' in sample_facility:
                cells.append(html.Td(row.get('industry', ''), style=cell_style))
            if 'cre_property_type' in sample_facility:
                cells.append(html.Td(row.get('cre_property_type', ''), style=cell_style))
            if 'msa' in sample_facility:
                cells.append(html.Td(row.get('msa', ''), style=cell_style))
            
            # Add metric cells in the same order as headers
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
    
    # Create complete table with frozen headers
    table = html.Table([
        html.Thead([header_row]),
        html.Tbody(body_rows)
    ], style={
        'borderCollapse': 'collapse',
        'width': '100%',
        'minWidth': '1200px'
    })
    
    # Wrap in container with proper scrolling and header positioning
    return html.Div([
        table
    ], style={
        'overflowX': 'auto',
        'overflowY': 'auto',
        'maxHeight': '70vh',  # Limit height to enable vertical scrolling
        'position': 'relative'
    })