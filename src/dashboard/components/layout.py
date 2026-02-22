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

    Tabs with required_roles are hidden unless the current user's role is in the list.
    Adding a new tab to the registry automatically adds it to navigation.
    """
    user_role = user_management.get_current_user_role()
    tabs = get_all_tabs()

    buttons = []
    for i, tab in enumerate(tabs):
        # Determine visibility: hide if tab requires specific roles and user doesn't have one
        visible = True
        if tab.required_roles and user_role not in tab.required_roles:
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
                style=style if tab.required_roles else {},
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
                    html.Div("Portfolio Dashboard", className="dashboard-title"),
                    *left_controls,
                ], className="flex items-center gap-3"),
                html.Div([
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
            html.Div([
                html.Div(id="tab-content-container"),
                html.Div([
                    html.Div(className="tab-loading-spinner"),
                    html.Div("Refreshing", className="tab-loading-text"),
                ], id="tab-loading-overlay"),
            ], id="tab-content-wrapper", className="tab-content-wrapper"),
        ], className="mx-auto max-w-[1600px] px-5 py-4"),

        # ── Modals ──────────────────────────────────────────────────────────
        _profile_switch_modal(),
        _contact_modal(),
        _portfolio_modal(),
        _portfolio_create_modal(),
        _time_window_modal(),

        # ── Hidden infrastructure ───────────────────────────────────────────
        dcc.Store(id="active-tab-store", data=None),
        dcc.Store(id="current-user-store", data=user_management.get_current_user()),
        dcc.Store(id="time-window-store", data=_initial_time_window()),
        *signal_stores,
    ])


# ── Modal helpers (keep layout.py clean) ────────────────────────────────────

_MODAL_BG = {
    "background": "var(--bg-raised)",
    "backdropFilter": "blur(20px)",
    "WebkitBackdropFilter": "blur(20px)",
    "borderRadius": "16px",
    "border": "1px solid var(--glass-border)",
    "boxShadow": "0 20px 60px rgba(0, 0, 0, 0.3), 0 0 40px var(--primary-glow)",
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
    """Portfolio Manager modal — dropdown selector + action buttons."""
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
                html.Label("Select a portfolio or create a new one:", className="block text-sm font-medium mb-2 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(id="portfolio-modal-dropdown", placeholder="Choose portfolio...", className="text-sm mb-4", style={"fontSize": "14px"}),
                html.Div([
                    html.Button("Select", id="portfolio-select-confirm", className="btn btn-primary", style={"fontSize": "13px", "flex": "1"}),
                    html.Button("Update", id="portfolio-update-btn", className="btn btn-outline", style={"fontSize": "13px", "flex": "1"}, disabled=True),
                    html.Button("Delete", id="portfolio-delete-btn", className="btn btn-outline", style={"fontSize": "13px", "flex": "1", "color": "#ef4444", "borderColor": "#ef4444"}, disabled=True),
                ], className="flex gap-2"),
                html.Div(id="portfolio-delete-error", className="text-red-500 text-xs mt-2", style={"textAlign": "center"}),
            ], className="p-4"),
        ], className="flex flex-col",
           style={**_MODAL_BG, **_MODAL_CENTER, "width": "400px", "maxWidth": "90vw", "overflow": "visible"}),
    ], id="portfolio-modal", style=_MODAL_OVERLAY)


def _portfolio_create_modal():
    """Portfolio Creation/Edit Wizard — dynamic hierarchical filter builder."""
    return html.Div([
        html.Div([
            html.Header([
                html.Div([
                    html.H2(id="portfolio-wizard-title", children="Create New Portfolio",
                            className="text-lg font-semibold text-ink-800 dark:text-slate-200"),
                    html.Button("✕", id="portfolio-create-cancel", className="btn btn-ghost text-xl cursor-pointer",
                                style={"padding": "4px 8px", "minWidth": "auto", "minHeight": "auto"}),
                ], className="flex items-center justify-between"),
            ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700"),
            html.Div([
                # Dynamic filter levels container — populated by callback
                html.Div(id="filter-levels-container", children=[]),
                # Add Level button
                html.Div([
                    html.Button("+ Add Level", id="add-filter-level-btn", className="btn btn-outline text-sm mt-2",
                                style={"fontSize": "12px"}),
                ], className="text-right"),
                # Portfolio name input
                html.Div([
                    html.Label("Portfolio Name", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                    dcc.Input(id="create-portfolio-name-input", type="text", placeholder="Enter portfolio name...",
                              className="w-full px-3 py-2 text-xs border border-slate-300 dark:border-ink-600 rounded-md focus:ring-2 focus:ring-brand-500"),
                ], className="mt-4 mb-3"),
                html.Button("Save Portfolio", id="save-new-portfolio-btn", className="btn btn-primary btn-glow w-full",
                            style={"fontSize": "13px"}),
                html.Div(id="create-portfolio-error", className="text-red-500 text-xs mt-2", style={"textAlign": "center"}),
            ], className="p-4 flex-1 overflow-auto"),
        ], className="flex flex-col",
           style={**_MODAL_BG, **_MODAL_CENTER, "width": "480px", "maxWidth": "90vw", "maxHeight": "85vh", "overflow": "auto"}),
        # Store for in-progress filter state: list of {column, values}
        dcc.Store(id="portfolio-filter-state", data=[]),
        # Store for edit mode: portfolio name being edited (None = create mode)
        dcc.Store(id="portfolio-edit-name", data=None),
    ], id="portfolio-create-modal", style=_MODAL_OVERLAY)


def _initial_time_window() -> dict | None:
    """Return the initial time-window store value from AppState."""
    from ..app_state import app_state
    start, end = app_state.get_time_window()
    if start and end:
        return {"start": start, "end": end}
    return None


def _time_window_modal():
    """Modal with two dropdowns for selecting the global time window."""
    from ..app_state import app_state
    from datetime import datetime as _dt

    start, end = app_state.get_time_window()

    # Build dropdown options from unique reporting dates
    import polars as pl
    all_dates = (
        app_state.facilities_df["reporting_date"]
        .unique()
        .sort()
        .cast(pl.Utf8)
        .to_list()
    ) if not app_state.facilities_df.is_empty() else []

    options = [
        {"label": _dt.fromisoformat(d[:10]).strftime("%b %Y"), "value": d[:10]}
        for d in all_dates
    ]

    start_val = start[:10] if start else (all_dates[0][:10] if all_dates else None)
    end_val = end[:10] if end else (all_dates[-1][:10] if all_dates else None)

    return html.Div([
        html.Div([
            html.H3("Time Window", style={"marginBottom": "16px", "color": "rgba(255,255,255,0.92)", "textAlign": "center"}),
            html.Div([
                html.Div([
                    html.Label("From", className="block text-xs font-medium mb-1",
                               style={"color": "rgba(255,255,255,0.6)"}),
                    dcc.Dropdown(
                        id="time-window-start-dropdown",
                        options=options,
                        value=start_val,
                        clearable=False,
                        className="text-sm",
                        style={"fontSize": "13px"},
                    ),
                ], style={"flex": "1"}),
                html.Div([
                    html.Label("To", className="block text-xs font-medium mb-1",
                               style={"color": "rgba(255,255,255,0.6)"}),
                    dcc.Dropdown(
                        id="time-window-end-dropdown",
                        options=options,
                        value=end_val,
                        clearable=False,
                        className="text-sm",
                        style={"fontSize": "13px"},
                    ),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "16px", "marginBottom": "24px"}),
            # Keep the store for backward compat (callbacks reference it)
            dcc.Store(id="time-window-dates", data=all_dates),
            html.Div([
                html.Button("Apply", id="time-window-apply", className="btn btn-primary", style={"marginRight": "10px"}),
                html.Button("Show All", id="time-window-reset", className="btn btn-outline", style={"marginRight": "10px"}),
                html.Button("Cancel", id="time-window-cancel", className="btn btn-outline"),
            ], style={"textAlign": "center", "display": "flex", "justifyContent": "center", "gap": "8px"}),
        ], style={**_MODAL_BG, **_MODAL_CENTER, "padding": "30px", "width": "440px", "maxWidth": "90vw"}),
    ], id="time-window-modal", style=_MODAL_OVERLAY)


def get_app_index_string():
    """Get the HTML template string for the app.

    Injects the accent-color CSS overrides based on ``config.settings.ui.accent_color``.
    """
    from .. import config as _cfg
    palette = _cfg.COLOR_PALETTES.get(
        _cfg.settings.ui.accent_color,
        _cfg.COLOR_PALETTES["blue"],
    )
    p400, p500, p600, p700 = palette["400"], palette["500"], palette["600"], palette["700"]
    glow_rgb = palette["glow"]

    import json as _json
    palettes_js = _json.dumps(_cfg.COLOR_PALETTES)

    return f'''
<!DOCTYPE html>
<html lang="en" class="dark">
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Portfolio Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
      tailwind.config = {{
        darkMode: 'class',
        theme: {{ extend: {{
          colors: {{
            ink: {{ 900:'#06080f',800:'#0c1020',700:'#111627',600:'#1c2333',500:'#64748b',100:'#e2e8f0',50:'#f1f5f9' }},
            brand: {{500:'{p500}',400:'{p400}',300:'{p400}'}}
          }},
          boxShadow: {{
            soft: '0 2px 12px rgba(0,0,0,.25)',
            glow: '0 0 20px rgba({glow_rgb},.15)'
          }}
        }}}}
      }};
    </script>
    <script>
      window.__IRIS_PALETTES = {palettes_js};
    </script>
    <style>
      :root {{
        --primary-400: {p400};
        --primary-500: {p500};
        --primary-600: {p600};
        --primary-700: {p700};
        --primary-glow: rgba({glow_rgb}, 0.18);
      }}
      html.dark {{
        --primary-glow: rgba({glow_rgb}, 0.25);
      }}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    {{%metas%}}
    {{%favicon%}}
    {{%css%}}
  </head>
  <body>
    <div id="root">{{%app_entry%}}</div>
    <footer>
      {{%config%}}
      {{%scripts%}}
      {{%renderer%}}
    </footer>
    <script>
      (function(){{
        var t = localStorage.getItem('theme');
        if (t === 'light') {{
          document.documentElement.classList.remove('dark');
        }} else {{
          document.documentElement.classList.add('dark');
        }}
        // Restore saved accent color
        var ac = localStorage.getItem('accent_color');
        var p = ac && window.__IRIS_PALETTES && window.__IRIS_PALETTES[ac];
        if (p) {{
          var r = document.documentElement.style;
          r.setProperty('--primary-400', p['400']);
          r.setProperty('--primary-500', p['500']);
          r.setProperty('--primary-600', p['600']);
          r.setProperty('--primary-700', p['700']);
          r.setProperty('--primary-glow', 'rgba(' + p.glow + ', 0.25)');
        }}
      }})();
    </script>
  </body>
</html>
'''