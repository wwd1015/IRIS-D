"""
Layout and navigation components for IRIS-D (Interactive Reporting & Insight Generation System - Dashboard)
"""

from dash import html, dcc
from ..auth import user_management


def create_role_based_navigation():
    """Create navigation tabs based on user role - all tabs present but visibility controlled"""
    user_role = user_management.get_current_user_role()
    print(f"DEBUG: Creating navigation for user '{user_management.get_current_user()}' with role '{user_role}'")
    
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


def get_tab_button_classes():
    """Get CSS classes for tab buttons"""
    return {
        'active': "px-3 py-1.5 rounded bg-ink-900 text-white",
        'inactive': "px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700"
    }


def create_layout(selected_portfolio, app_index_string, available_portfolios=None):
    """Create the main layout with modern Tailwind styling"""
    return html.Div(className="min-h-screen", children=[
        # Modern Header with Tailwind styling
        html.Header([
            html.Div([
                html.Div([
                    html.Div("IRIS-D", className="dashboard-title"),
                    # Portfolio button for universal access
                    html.Div([
                        html.Button(
                            id="portfolio-selector-btn",
                            children=selected_portfolio or "Select Portfolio",
                            n_clicks=0,
                            className="px-3 py-1.5 text-sm rounded-lg border border-white/10 bg-white/5 text-purple-200 hover:bg-white/10 cursor-pointer min-w-[200px] text-left transition-all duration-200",
                            title="Click to change portfolio"
                        ),
                        # Hidden dropdown for callback compatibility
                        dcc.Dropdown(
                            id='universal-portfolio-dropdown',
                            options=[{'label': portfolio, 'value': portfolio} for portfolio in (available_portfolios or [])],
                            value=selected_portfolio,
                            style={"display": "none"}
                        )
                    ], className="ml-4")
                ], className="flex items-center gap-3"),
                html.Div([
                    html.Button("Login/Register", id="login-btn", n_clicks=0,
                                className="px-3 py-1.5 text-xs rounded-lg border border-white/10 text-white/70 hover:bg-white/5 hover:text-white transition-all duration-200"),
                    html.Button(
                        id="profile-avatar-btn",
                        children="G",
                        n_clicks=0,
                        className="ml-2 h-8 w-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 text-white text-sm font-semibold hover:from-purple-400 hover:to-indigo-500 flex items-center justify-center cursor-pointer shadow-lg shadow-purple-500/20 transition-all duration-200",
                        title="Switch Profile"
                    ),
                    html.Button("Dark", id="theme-toggle", n_clicks=0,
                                className="ml-2 px-3 py-1.5 text-xs rounded-lg border border-white/10 text-white/70 hover:bg-white/5 hover:text-white transition-all duration-200"),
                    html.Button("Contact", id="contact-btn", n_clicks=0,
                                className="ml-2 px-3 py-1.5 text-xs rounded-lg border border-white/10 text-white/70 hover:bg-white/5 hover:text-white transition-all duration-200")
                ], className="flex items-center gap-2 text-sm")
            ], className="flex h-14 items-center justify-between gap-3"),
            # Navigation tabs row - dynamically updated based on user role
            html.Nav(id="navigation-tabs-container", children=create_role_based_navigation(), 
                    className="flex items-center gap-2 overflow-x-auto py-2 text-sm")
        ], className="header sticky top-0 z-40 mx-auto max-w-[1600px]"),
        
        # Main content with 3-column grid layout
        html.Main([
            html.Div(id='tab-content-container')
        ], className="mx-auto max-w-[1600px] px-5 py-4"),
        
        # Login/Register Modal
        html.Div([
            html.Div([
                html.H3("Login / Register", style={"marginBottom": "20px", "color": "rgba(255,255,255,0.92)", "textAlign": "center"}),
                dcc.Input(
                    id="username-input",
                    type="text",
                    placeholder="Enter username",
                    className="form-input",
                    style={"width": "100%", "marginBottom": "15px"}
                ),
                html.Div([
                    html.Label("Select Role:", style={"fontSize": "14px", "fontWeight": "500", "marginBottom": "5px", "display": "block", "color": "rgba(255,255,255,0.6)"}),
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
                    html.Button("Login", id="login-submit", className="btn btn-primary btn-glow", style={"marginRight": "10px"}),
                    html.Button("Register", id="register-submit", className="btn btn-secondary", style={"marginRight": "10px"}),
                    html.Button("Cancel", id="login-cancel", className="btn btn-ghost")
                ], style={"textAlign": "center", "marginBottom": "30px", "display": "flex", "justifyContent": "center", "gap": "8px"}),
                
                # Separator line
                html.Hr(style={"margin": "20px 0", "border": "1px solid rgba(255,255,255,0.08)"}),
                
                # Delete Profile Section
                html.Div([
                    html.H4("Delete Profile", style={"marginBottom": "15px", "color": "#f87171", "textAlign": "center", "fontSize": "18px"}),
                    dcc.Dropdown(
                        id="delete-profile-dropdown",
                        placeholder="Select profile to delete...",
                        style={"marginBottom": "15px"},
                        className="form-select"
                    ),
                    html.Div([
                        html.Button("Delete Profile", id="delete-profile-btn", className="btn btn-danger")
                    ], style={"textAlign": "center"})
                ], style={"marginTop": "20px"})
            ], style={
                "background": "rgba(17, 22, 39, 0.95)",
                "backdropFilter": "blur(20px)",
                "WebkitBackdropFilter": "blur(20px)",
                "padding": "40px",
                "borderRadius": "16px",
                "border": "1px solid rgba(255,255,255,0.08)",
                "width": "420px",
                "maxWidth": "90vw",
                "position": "absolute",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",
                "boxShadow": "0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(139, 92, 246, 0.08)",
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
                html.H3("Switch Profile", style={"marginBottom": "20px", "color": "rgba(255,255,255,0.92)", "textAlign": "center"}),
                html.Div([
                    html.Label("Select Profile:", style={"fontSize": "14px", "fontWeight": "500", "marginBottom": "10px", "display": "block", "color": "rgba(255,255,255,0.6)"}),
                    dcc.Dropdown(
                        id="profile-switch-dropdown",
                        placeholder="Choose a profile...",
                        style={"marginBottom": "20px"},
                        className="form-select"
                    )
                ]),
                html.Div([
                    html.Button("Switch", id="profile-switch-confirm", className="btn btn-primary", style={"marginRight": "10px"}),
                    html.Button("Cancel", id="profile-switch-cancel", className="btn btn-outline")
                ], style={"textAlign": "center", "display": "flex", "justifyContent": "center", "gap": "8px"})
            ], style={
                "background": "rgba(17, 22, 39, 0.95)",
                "backdropFilter": "blur(20px)",
                "WebkitBackdropFilter": "blur(20px)",
                "padding": "30px",
                "borderRadius": "16px",
                "border": "1px solid rgba(255,255,255,0.08)",
                "width": "380px",
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
                    html.H4("💭 Feedback", style={"fontSize": "16px", "fontWeight": "600", "color": "rgba(255,255,255,0.92)", "marginBottom": "15px"}),
                    html.P("Help us improve by sharing your thoughts:", style={"marginBottom": "15px", "color": "rgba(255,255,255,0.5)"}),
                    html.A("Provide Feedback", 
                          href="https://forms.google.com/feedback-form", 
                          target="_blank",
                          className="btn btn-success",
                          style={"textDecoration": "none", "marginBottom": "20px", "display": "inline-block"})
                ]),
                
                html.Div([
                    html.Button("Close", id="contact-close", className="btn btn-outline")
                ], style={"textAlign": "center"})
            ], style={
                "background": "rgba(17, 22, 39, 0.95)",
                "backdropFilter": "blur(20px)",
                "WebkitBackdropFilter": "blur(20px)",
                "padding": "30px",
                "borderRadius": "16px",
                "border": "1px solid rgba(255,255,255,0.08)",
                "width": "420px",
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
        
        # Portfolio Management Modal - Complete Sidebar Replication
        html.Div([
            html.Div([
                # Modal Header
                html.Header([
                    html.Div([
                        html.H2("Portfolio Management", className="text-lg font-semibold text-ink-800 dark:text-slate-200"),
                        html.Button("✕", id="portfolio-modal-cancel", className="btn btn-ghost text-xl cursor-pointer", style={"padding": "4px 8px", "minWidth": "auto", "minHeight": "auto"})
                    ], className="flex items-center justify-between")
                ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700"),
                
                # Modal Content - Replicating the complete sidebar
                html.Div([
                    # Portfolio Selection Section
                    html.Div([
                        html.Label("Current Portfolio:", className="block text-sm font-medium mb-2 text-ink-600 dark:text-slate-300"),
                        dcc.Dropdown(
                            id="portfolio-modal-dropdown",
                            placeholder="Select portfolio...",
                            className="text-sm mb-4",
                            style={"fontSize": "14px"}
                        ),
                        html.Button("✓ Select Portfolio", id="portfolio-select-confirm", 
                                   className="btn btn-primary w-full mb-4", style={"fontSize": "13px"})
                    ]),
                    
                    # Portfolio Creator & Manager Section - Exact replica
                    html.Div([
                        html.H3("Create New Portfolio", className="text-sm font-semibold mb-3 text-brand-500"),
                        html.Div([
                            html.Label("Line of Business", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                            dcc.Dropdown(
                                id='modal-lob-dropdown',
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
                                id='modal-industry-dropdown',
                                options=[],
                                placeholder="Select Industry...",
                                className="text-xs",
                                multi=True
                            )
                        ], className="mb-3", id='modal-industry-group', style={'display': 'none'}),
                        html.Div([
                            html.Label("Property Type", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                            dcc.Dropdown(
                                id='modal-property-type-dropdown',
                                options=[],
                                placeholder="Select Property Type...",
                                className="text-xs",
                                multi=True
                            )
                        ], className="mb-3", id='modal-property-type-group', style={'display': 'none'}),
                        html.Div([
                            html.Label("OR Select Obligors Directly", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                            dcc.Dropdown(
                                id='modal-obligor-dropdown',
                                options=[],
                                placeholder="Select obligors...",
                                className="text-xs",
                                multi=True
                            )
                        ], className="mb-3", id='modal-obligor-group'),
                        html.Div([
                            html.Label("Portfolio Name", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                            dcc.Input(
                                id='modal-portfolio-name-input',
                                type='text',
                                placeholder="Enter portfolio name...",
                                className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-ink-600 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                            )
                        ], className="mb-3"),
                        html.Button("Save Portfolio", id='modal-save-portfolio-btn', 
                                   className="btn btn-primary btn-glow w-full mb-4", style={"fontSize": "12px"}),
                        
                        # Separator
                        html.Hr(className="border-slate-200 dark:border-ink-700 mb-4"),
                        
                        # Delete Portfolio Section
                        html.H3("Delete Portfolio", className="text-sm font-semibold mb-3 text-red-600"),
                        html.Div([
                            html.Label("Select Portfolio to Delete", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                            dcc.Dropdown(
                                id='modal-delete-portfolio-dropdown',
                                options=[],
                                placeholder="Select portfolio to delete...",
                                className="text-xs"
                            )
                        ], className="mb-3"),
                        html.Button("Delete Portfolio", id='modal-delete-confirm-btn', 
                                   className="btn btn-danger w-full", style={"fontSize": "12px"})
                    ], className="space-y-3 mt-4")
                ], className="p-4 flex-1 overflow-auto")
                
            ], className="overflow-hidden flex flex-col", 
               style={
                "background": "rgba(17, 22, 39, 0.95)",
                "backdropFilter": "blur(20px)",
                "WebkitBackdropFilter": "blur(20px)",
                "borderRadius": "16px",
                "border": "1px solid rgba(255,255,255,0.08)",
                "boxShadow": "0 20px 60px rgba(0, 0, 0, 0.5)",
                "width": "420px",
                "maxWidth": "90vw", 
                "maxHeight": "85vh",
                "position": "absolute",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",
                "zIndex": "1001"
            })
        ], id="portfolio-modal", style={
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
                "display": "flex",
                "alignItems": "center",
                "position": "absolute",
                "bottom": "20px",
                "right": "20px",
                "zIndex": "1000",
                "fontSize": "14px",
                "fontWeight": "500"
            })
        ], id="auto-save-notification", style={
            "position": "fixed",
            "top": "0",
            "right": "0",
            "width": "100%",
            "height": "100%",
            "pointerEvents": "none",
            "zIndex": "999",
            "display": "none"
        }),
        
        # Hidden interval components
        dcc.Interval(
            id='auto-save-interval',
            interval=30*1000,  # 30 seconds
            n_intervals=0
        ),
        dcc.Interval(
            id='hide-notification-interval',
            interval=3*1000,  # 3 seconds
            n_intervals=0,
            disabled=True
        ),
        
        # Store component to track current user for navigation updates
        dcc.Store(id='current-user-store', data='Guest')
    ])


def get_app_index_string():
    """Get the HTML template string for the app"""
    return '''
<!DOCTYPE html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>IRIS-D</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
      tailwind.config = {
        darkMode: 'class',
        theme: { extend: {
          colors: {
            ink: { 900:'#06080f',800:'#0c1020',700:'#111627',600:'#1c2333',500:'#64748b',100:'#e2e8f0',50:'#f1f5f9' },
            brand: {500:'#8b5cf6',400:'#a78bfa',300:'#c4b5fd'}
          },
          boxShadow: {
            soft: '0 2px 12px rgba(0,0,0,.25)',
            glow: '0 0 20px rgba(139,92,246,.15)'
          }
        }}
      };
    </script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    {%metas%}
    {%favicon%}
    {%css%}
  </head>
  <body style="background:#06080f;color:rgba(255,255,255,.92);font-family:Inter,-apple-system,BlinkMacSystemFont,system-ui,sans-serif;">
    <div id="root">{%app_entry%}</div>
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>
  </body>
</html>
'''