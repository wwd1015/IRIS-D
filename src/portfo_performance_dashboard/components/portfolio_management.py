from dash import html, dcc
from .. import config
from ..auth import user_management


def get_current_user_portfolios():
    """Get portfolios for current user"""
    if user_management.get_current_user() == 'Guest':
        return config.DEFAULT_PORTFOLIOS.copy()
    else:
        user_data = user_management.get_user_data(user_management.get_current_user())
        user_portfolios = user_data.get('portfolios', {})
        if not user_portfolios:
            # Initialize with default portfolios for new users
            return config.DEFAULT_PORTFOLIOS.copy()
        return user_portfolios


def create_portfolio_sidebar(selected_portfolio, available_portfolios):
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


def save_portfolio_data(portfolios, available_portfolios, portfolio_name, lob_value, industry_value, property_type_value, obligor_value):
    """Save new portfolio and return updated portfolios and options"""
    if portfolio_name and (lob_value or obligor_value):
        # Add new portfolio
        portfolios[portfolio_name] = {
            'lob': lob_value,
            'industry': industry_value,
            'property_type': property_type_value,
            'obligors': obligor_value
        }
        
        # Update available portfolios
        available_portfolios = list(portfolios.keys())
        
        # Create dropdown options
        portfolio_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios]
        delete_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios if portfolio not in ['Corporate Banking', 'CRE']]
        
        return portfolios, available_portfolios, portfolio_options, delete_options, f"Portfolio '{portfolio_name}' saved successfully!"
    
    return portfolios, available_portfolios, None, None, "Please enter a portfolio name and select criteria."


def delete_portfolio_data(portfolios, available_portfolios, portfolio_to_delete):
    """Delete portfolio and return updated portfolios and options"""
    if portfolio_to_delete and portfolio_to_delete not in ['Corporate Banking', 'CRE']:
        # Remove portfolio
        portfolios.pop(portfolio_to_delete, None)
        
        # Update available portfolios
        available_portfolios = list(portfolios.keys())
        
        # Create dropdown options
        portfolio_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios]
        delete_options = [{'label': portfolio, 'value': portfolio} for portfolio in available_portfolios if portfolio not in ['Corporate Banking', 'CRE']]
        
        return portfolios, available_portfolios, portfolio_options, delete_options, f"Portfolio '{portfolio_to_delete}' deleted successfully!"
    
    return portfolios, available_portfolios, None, None, "Cannot delete default portfolios or invalid selection."