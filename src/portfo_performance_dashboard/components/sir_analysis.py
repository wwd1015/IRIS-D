from dash import html, dcc


def create_sir_analysis_sidebar(selected_portfolio, portfolios):
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