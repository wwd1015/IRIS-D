"""
Layout and navigation components for the Bank Risk Dashboard
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


def create_layout(selected_portfolio, app_index_string):
    """Create the main layout with modern Tailwind styling"""
    return html.Div(className="min-h-screen", children=[
        # Modern Header with Tailwind styling
        html.Header([
            html.Div([
                html.Div([
                    html.Div("Portfolio Performance Dashboard", className="dashboard-title"),
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
                "display": "flex",
                "alignItems": "center",
                "position": "absolute",
                "top": "20px",
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
            interval=1*1000,  # 1 second
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