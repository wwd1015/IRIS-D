"""
Layout and navigation components for IRIS-D.

This module provides the shell layout (header, nav, modals, stores)
and dynamically builds navigation tabs from the tab registry.
"""

from dash import html, dcc
from ..auth import user_management
from ..tabs.registry import get_all_tabs


def create_navigation_tabs():
    """
    Build navigation buttons from the tab registry.
    
    Tabs with a required_role are hidden unless the current user has that role.
    Adding a new tab to the registry automatically adds it to navigation.
    """
    user_role = user_management.get_current_user_role()
    tabs = get_all_tabs()

    buttons = []
    for i, tab in enumerate(tabs):
        # Determine visibility
        visible = True
        if tab.required_role and tab.required_role != user_role and user_role != "Guest":
            visible = False

        # First tab gets active styling by default
        cls = "px-3 py-1.5 rounded bg-ink-900 text-white" if i == 0 else "px-3 py-1.5 rounded hover:bg-slate-100 dark:hover:bg-ink-700"
        style = {"display": "inline-block"} if visible else {"display": "none"}

        buttons.append(
            html.Button(
                tab.label,
                id=f"tab-{tab.id}",
                n_clicks=0,
                className=cls,
                style=style if tab.required_role else {},
            )
        )

    return buttons


def create_layout(selected_portfolio, app_index_string, available_portfolios=None):
    """Create the main app shell layout."""
    from .controls import ControlPosition, get_global_controls
    from .signals import all_signal_ids

    # Render Layer 1 controls from the GlobalControl registry
    left_controls = [
        c.render(selected_portfolio=selected_portfolio,
                 available_portfolios=available_portfolios or [])
        for c in get_global_controls(ControlPosition.LEFT)
    ]
    right_controls = [
        c.render()
        for c in get_global_controls(ControlPosition.RIGHT)
    ]

    # Signal stores for cross-layer communication
    signal_stores = [dcc.Store(id=sid, data=None) for sid in all_signal_ids()]

    return html.Div(className="min-h-screen", children=[
        # ── Header ──────────────────────────────────────────────────────────
        html.Header([
            html.Div([
                html.Div([
                    html.Div("IRIS-D", className="dashboard-title"),
                    *left_controls,
                ], className="flex items-center gap-3"),
                html.Div([
                    # Login button (kept outside GlobalControl registry
                    # because user callbacks in app.py still reference it)
                    html.Button("Login/Register", id="login-btn", n_clicks=0,
                                className="header-btn"),
                    *right_controls,
                ], className="flex items-center gap-2 text-sm"),
            ], className="flex h-14 items-center justify-between gap-3"),
            html.Nav(
                id="navigation-tabs-container",
                children=create_navigation_tabs(),
                className="flex items-center gap-2 overflow-x-auto py-2 text-sm",
            ),
        ], className="header sticky top-0 z-40 mx-auto max-w-[1600px]"),

        # ── Main content ────────────────────────────────────────────────────
        html.Main([
            html.Div(id="tab-content-container")
        ], className="mx-auto max-w-[1600px] px-5 py-4"),

        # ── Modals ──────────────────────────────────────────────────────────
        _login_modal(),
        _profile_switch_modal(),
        _contact_modal(),
        _portfolio_modal(),
        _auto_save_notification(),

        # ── Hidden infrastructure ───────────────────────────────────────────
        dcc.Interval(id="auto-save-interval", interval=30_000, n_intervals=0),
        dcc.Interval(id="hide-notification-interval", interval=3_000, n_intervals=0, disabled=True),
        dcc.Store(id="current-user-store", data="Guest"),
        *signal_stores,
    ])


# ── Modal helpers (keep layout.py clean) ────────────────────────────────────

_MODAL_BG = {
    "background": "rgba(17, 22, 39, 0.95)",
    "backdropFilter": "blur(20px)",
    "WebkitBackdropFilter": "blur(20px)",
    "borderRadius": "16px",
    "border": "1px solid rgba(255,255,255,0.08)",
    "boxShadow": "0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(139, 92, 246, 0.08)",
}

_MODAL_OVERLAY = {
    "position": "fixed", "top": "0", "left": "0", "width": "100%",
    "height": "100%", "backgroundColor": "rgba(0,0,0,0.5)",
    "zIndex": "1000", "display": "none",
}

_MODAL_CENTER = {
    "position": "absolute", "top": "50%", "left": "50%",
    "transform": "translate(-50%, -50%)", "zIndex": "1001",
}


def _login_modal():
    return html.Div([
        html.Div([
            html.H3("Login / Register", style={"marginBottom": "20px", "color": "rgba(255,255,255,0.92)", "textAlign": "center"}),
            dcc.Input(id="username-input", type="text", placeholder="Enter username",
                      className="form-input", style={"width": "100%", "marginBottom": "15px"}),
            html.Div([
                html.Label("Select Role:", style={"fontSize": "14px", "fontWeight": "500", "marginBottom": "5px", "display": "block", "color": "rgba(255,255,255,0.6)"}),
                dcc.Dropdown(
                    id="role-dropdown",
                    options=[{"label": r, "value": r} for r in ("Corp SCO", "CRE SCO", "SAG", "BA")],
                    placeholder="Choose your role...",
                    style={"marginBottom": "20px"}, className="form-select",
                ),
            ]),
            html.Div([
                html.Button("Login", id="login-submit", className="btn btn-primary btn-glow", style={"marginRight": "10px"}),
                html.Button("Register", id="register-submit", className="btn btn-secondary", style={"marginRight": "10px"}),
                html.Button("Cancel", id="login-cancel", className="btn btn-ghost"),
            ], style={"textAlign": "center", "marginBottom": "30px", "display": "flex", "justifyContent": "center", "gap": "8px"}),
            html.Hr(style={"margin": "20px 0", "border": "1px solid rgba(255,255,255,0.08)"}),
            html.Div([
                html.H4("Delete Profile", style={"marginBottom": "15px", "color": "#f87171", "textAlign": "center", "fontSize": "18px"}),
                dcc.Dropdown(id="delete-profile-dropdown", placeholder="Select profile to delete...",
                             style={"marginBottom": "15px"}, className="form-select"),
                html.Div([html.Button("Delete Profile", id="delete-profile-btn", className="btn btn-danger")],
                         style={"textAlign": "center"}),
            ], style={"marginTop": "20px"}),
        ], style={**_MODAL_BG, **_MODAL_CENTER, "padding": "40px", "width": "420px", "maxWidth": "90vw"}),
    ], id="login-modal", style=_MODAL_OVERLAY)


def _profile_switch_modal():
    return html.Div([
        html.Div([
            html.H3("Switch Profile", style={"marginBottom": "20px", "color": "rgba(255,255,255,0.92)", "textAlign": "center"}),
            html.Div([
                html.Label("Select Profile:", style={"fontSize": "14px", "fontWeight": "500", "marginBottom": "10px", "display": "block", "color": "rgba(255,255,255,0.6)"}),
                dcc.Dropdown(id="profile-switch-dropdown", placeholder="Choose a profile...",
                             style={"marginBottom": "20px"}, className="form-select"),
            ]),
            html.Div([
                html.Button("Switch", id="profile-switch-confirm", className="btn btn-primary", style={"marginRight": "10px"}),
                html.Button("Cancel", id="profile-switch-cancel", className="btn btn-outline"),
            ], style={"textAlign": "center", "display": "flex", "justifyContent": "center", "gap": "8px"}),
        ], style={**_MODAL_BG, **_MODAL_CENTER, "padding": "30px", "width": "380px", "maxWidth": "90vw"}),
    ], id="profile-switch-modal", style=_MODAL_OVERLAY)


def _contact_modal():
    return html.Div([
        html.Div([
            html.H3("Contact & Support", style={"marginBottom": "20px", "color": "rgba(255,255,255,0.92)", "textAlign": "center"}),
            html.Div([
                html.H4("📧 Contact Information", style={"fontSize": "16px", "fontWeight": "600", "color": "rgba(255,255,255,0.8)", "marginBottom": "15px"}),
                html.P("For technical support and inquiries:", style={"marginBottom": "10px", "color": "rgba(255,255,255,0.5)"}),
                html.Div([html.Strong("Email: "), html.A("support@portfolio-dashboard.com", href="mailto:support@portfolio-dashboard.com", style={"color": "#a78bfa", "textDecoration": "none"})], style={"marginBottom": "10px"}),
                html.Div([html.Strong("Phone: "), html.Span("+1 (555) 123-4567")], style={"marginBottom": "20px"}),
            ]),
            html.Div([
                html.H4("💭 Feedback", style={"fontSize": "16px", "fontWeight": "600", "color": "rgba(255,255,255,0.8)", "marginBottom": "15px"}),
                html.P("Help us improve by sharing your thoughts:", style={"marginBottom": "15px", "color": "rgba(255,255,255,0.5)"}),
            ]),
            html.Div([html.Button("Close", id="contact-close", className="btn btn-outline")], style={"textAlign": "center"}),
        ], style={**_MODAL_BG, **_MODAL_CENTER, "padding": "30px", "width": "420px", "maxWidth": "90vw"}),
    ], id="contact-modal", style=_MODAL_OVERLAY)


def _portfolio_modal():
    return html.Div([
        html.Div([
            html.Header([
                html.Div([
                    html.H2("Portfolio Management", className="text-lg font-semibold text-ink-800 dark:text-slate-200"),
                    html.Button("✕", id="portfolio-modal-cancel", className="btn btn-ghost text-xl cursor-pointer",
                                style={"padding": "4px 8px", "minWidth": "auto", "minHeight": "auto"}),
                ], className="flex items-center justify-between"),
            ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700"),
            html.Div([
                html.Div([
                    html.Label("Current Portfolio:", className="block text-sm font-medium mb-2 text-ink-600 dark:text-slate-300"),
                    dcc.Dropdown(id="portfolio-modal-dropdown", placeholder="Select portfolio...", className="text-sm mb-4", style={"fontSize": "14px"}),
                    html.Button("✓ Select Portfolio", id="portfolio-select-confirm", className="btn btn-primary w-full mb-4", style={"fontSize": "13px"}),
                ]),
                html.Div([
                    html.H3("Create New Portfolio", className="text-sm font-semibold mb-3 text-brand-500"),
                    html.Div([
                        html.Label("Line of Business", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                        dcc.Dropdown(id="modal-lob-dropdown", options=[{"label": "Corporate Banking", "value": "Corporate Banking"}, {"label": "CRE", "value": "CRE"}], placeholder="Select LOB...", className="text-xs mb-3"),
                    ], className="mb-3"),
                    html.Div([
                        html.Label("Industry", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                        dcc.Dropdown(id="modal-industry-dropdown", options=[], placeholder="Select Industry...", className="text-xs", multi=True),
                    ], className="mb-3", id="modal-industry-group", style={"display": "none"}),
                    html.Div([
                        html.Label("Property Type", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                        dcc.Dropdown(id="modal-property-type-dropdown", options=[], placeholder="Select Property Type...", className="text-xs", multi=True),
                    ], className="mb-3", id="modal-property-type-group", style={"display": "none"}),
                    html.Div([
                        html.Label("OR Select Obligors Directly", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                        dcc.Dropdown(id="modal-obligor-dropdown", options=[], placeholder="Select obligors...", className="text-xs", multi=True),
                    ], className="mb-3", id="modal-obligor-group"),
                    html.Div([
                        html.Label("Portfolio Name", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                        dcc.Input(id="modal-portfolio-name-input", type="text", placeholder="Enter portfolio name...",
                                  className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-ink-600 rounded-md focus:ring-2 focus:ring-brand-500"),
                    ], className="mb-3"),
                    html.Button("Save Portfolio", id="modal-save-portfolio-btn", className="btn btn-primary btn-glow w-full mb-4", style={"fontSize": "12px"}),
                    html.Hr(className="border-slate-200 dark:border-ink-700 mb-4"),
                    html.H3("Delete Portfolio", className="text-sm font-semibold mb-3 text-red-600"),
                    html.Div([
                        html.Label("Select Portfolio to Delete", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                        dcc.Dropdown(id="modal-delete-portfolio-dropdown", options=[], placeholder="Select portfolio to delete...", className="text-xs"),
                    ], className="mb-3"),
                    html.Button("Delete Portfolio", id="modal-delete-confirm-btn", className="btn btn-danger w-full", style={"fontSize": "12px"}),
                ], className="space-y-3 mt-4"),
            ], className="p-4 flex-1 overflow-auto"),
        ], className="overflow-hidden flex flex-col",
           style={**_MODAL_BG, **_MODAL_CENTER, "width": "420px", "maxWidth": "90vw", "maxHeight": "85vh"}),
    ], id="portfolio-modal", style=_MODAL_OVERLAY)


def _auto_save_notification():
    return html.Div([
        html.Div([
            html.Span("💾", style={"marginRight": "8px", "fontSize": "16px"}),
            html.Span("Data auto-saved", id="save-message"),
        ], style={
            "backgroundColor": "#10b981", "color": "white", "padding": "10px 20px",
            "borderRadius": "6px", "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
            "display": "flex", "alignItems": "center",
            "position": "absolute", "bottom": "20px", "right": "20px",
            "zIndex": "1000", "fontSize": "14px", "fontWeight": "500",
        }),
    ], id="auto-save-notification", style={
        "position": "fixed", "top": "0", "right": "0", "width": "100%", "height": "100%",
        "pointerEvents": "none", "zIndex": "999", "display": "none",
    })


def get_app_index_string():
    """Get the HTML template string for the app."""
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
  <body>
    <div id="root">{%app_entry%}</div>
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>
    <script>
      // Apply saved theme on page load (before first paint).
      // Only toggle the class — CSS variables handle colors/backgrounds.
      (function(){
        var t = localStorage.getItem('theme');
        if (t === 'light') {
          document.documentElement.classList.remove('dark');
        } else {
          document.documentElement.classList.add('dark');
        }
      })();
    </script>
  </body>
</html>
'''