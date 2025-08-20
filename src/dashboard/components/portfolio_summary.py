from dash import html, dcc
import plotly.graph_objs as go
import pandas as pd


def create_charts(portfolio_data):
    """Create charts for the selected portfolio with dark theme and purple styling"""
    
    if len(portfolio_data) == 0:
        # Return empty charts if no data
        empty_bar = go.Figure()
        empty_bar.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        empty_bar.update_layout(plot_bgcolor='#ffffff', paper_bgcolor='#ffffff', title="Top 10 Holdings by Borrower", height=300)
        
        empty_pie = go.Figure()
        empty_pie.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        empty_pie.update_layout(plot_bgcolor='#ffffff', paper_bgcolor='#ffffff', title="Holdings by Industry", height=300)
        
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
        height=300,
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
    else:
        # For CRE, use property type
        property_data = portfolio_data[portfolio_data['lob'] == 'CRE']['cre_property_type'].value_counts()
        pie_labels = property_data.index.tolist()
        pie_values = property_data.values.tolist()
    
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
        height=300
    )
    
    return bar_fig, pie_fig


def create_watchlist_table(portfolio_data, facilities_df):
    """Create risk table for the selected portfolio with modern styling and new logic"""
    
    if len(portfolio_data) == 0:
        return html.Div("No data available for this portfolio.", className="p-4")

    # Get latest and previous quarter for each facility
    portfolio_data = portfolio_data.copy()
    portfolio_data['reporting_date'] = pd.to_datetime(portfolio_data['reporting_date'])
    facilities_df['reporting_date'] = pd.to_datetime(facilities_df['reporting_date'])
    
    watchlist_rows = []
    for _, row in portfolio_data.iterrows():
        fac_id = row['facility_id']
        obligor = row['obligor_name']
        current_rating = row['obligor_rating']
        current_balance = row['balance']
        current_date = row['reporting_date']
        
        # Get previous quarter data for this facility
        prev_facility_data = facilities_df[
            (facilities_df['facility_id'] == fac_id) & 
            (facilities_df['reporting_date'] < current_date)
        ].sort_values('reporting_date').tail(1)
        
        if not prev_facility_data.empty:
            prev_rating = prev_facility_data.iloc[0]['obligor_rating']
            rating_movement = "↓" if prev_rating < current_rating else "↑" if prev_rating > current_rating else "→"
            rating_color = "text-red-600" if rating_movement == "↓" else "text-green-600" if rating_movement == "↑" else "text-gray-600"
        else:
            rating_movement = "New"
            rating_color = "text-blue-600"
        
        # Include all facilities, watchlist logic based on high-risk criteria
        is_watchlist = current_rating >= 6 or current_balance > 50000000  # Rating 6+ or balance > $50M
        
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
    
    # Sort by rating (descending) and balance (descending)
    watchlist_rows.sort(key=lambda x: (x['rating'], float(x['balance'].replace('$', '').replace('M', ''))), reverse=True)
    
    # Take top 10
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


def create_main_content(selected_portfolio, get_filtered_data, facilities_df, portfolios=None):
    """Create the main content area with dark theme and purple styling"""
    # get_filtered_data is the wrapper function that only takes one argument
    portfolio_data = get_filtered_data(selected_portfolio)
    bar_fig, pie_fig = create_charts(portfolio_data)
    
    # Determine dynamic titles based on portfolio type
    if len(portfolio_data) > 0 and 'Corporate Banking' in portfolio_data['lob'].values:
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
            create_watchlist_table(portfolio_data, facilities_df)
        ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 p-4 mt-4 flex-1 min-h-0 overflow-y-auto")
    ], className="flex flex-col min-h-[600px]")


def create_positions_panel(selected_portfolio, facilities_df, portfolios, get_filtered_data):
    """Create portfolio positions panel with modern Tailwind styling"""
    print(f"DEBUG: create_positions_panel called for portfolio: {selected_portfolio}")
    
    # Get current quarter end data only
    
    # Filter to current quarter snapshot
    portfolio_data = get_filtered_data(selected_portfolio)
    print(f"DEBUG: portfolio_data length: {len(portfolio_data)}")
    print(f"DEBUG: portfolios keys: {list(portfolios.keys())}")
    print(f"DEBUG: portfolio criteria: {portfolios.get(selected_portfolio, 'NOT FOUND')}")
    
    if len(portfolio_data) == 0:
        print(f"DEBUG: No data for portfolio '{selected_portfolio}' - checking portfolio existence and criteria")
        return html.Div("No data available for this portfolio.", className="p-4 positions-panel")
    
    # Use latest_facilities data directly since it's already filtered to latest reporting date
    # No need to filter by reporting_date again as get_filtered_data already returns latest data
    
    # Get all data for comparison, with safe filtering
    all_portfolios_data = []
    for pname in portfolios.keys():
        pdata = get_filtered_data(pname)
        if len(pdata) > 0:
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
    ], className="chart-card positions-panel h-full")