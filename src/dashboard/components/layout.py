"""
Layout and navigation components for IRIS-D.

This module provides the shell layout (header, nav, modals, stores)
and dynamically builds navigation tabs from the tab registry.
"""

from dash import html, dcc
from ..auth import user_management
from ..tabs.registry import get_all_tabs


# Index-menu section order (Ledger nav directory). Unknown groups append last.
NAV_GROUP_ORDER = ["Home", "Portfolio", "Risk", "Analysis", "Tools"]


def create_navigation_tabs():
    """
    Build the Ledger "Index" navigation from the tab registry.

    A ☰ Index dropdown holds a grouped page directory (the tab buttons keep
    their ``tab-{id}`` ids so ``route_tabs`` wiring is unchanged), with a
    Group / Page breadcrumb beside it. Role-gated tabs are hidden via
    display:none (buttons must exist for callbacks).
    """
    user_role = user_management.get_current_user_role()
    tabs = get_all_tabs()

    def _visible(tab) -> bool:
        return not tab.required_roles or user_role in tab.required_roles

    # Active = first accessible tab (matches route_tabs' initial render)
    accessible = [t for t in tabs if _visible(t)]
    active = accessible[0] if accessible else (tabs[0] if tabs else None)
    active_id = active.id if active else None

    # Group tabs into Index sections
    group_names = list(NAV_GROUP_ORDER)
    for t in tabs:
        g = getattr(t, "nav_group", "Portfolio")
        if g not in group_names:
            group_names.append(g)

    sections = []
    for gname in group_names:
        gtabs = [t for t in tabs if getattr(t, "nav_group", "Portfolio") == gname]
        if not gtabs:
            continue
        rows = []
        for tab in gtabs:
            is_active = tab.id == active_id
            rows.append(html.Button(
                [html.Span(tab.label), html.Span("●", className="navtab-dot")],
                id=f"tab-{tab.id}",
                n_clicks=0,
                className="navtab active" if is_active else "navtab",
                style={} if _visible(tab) else {"display": "none"},
                role="tab",
                **{"aria-selected": "true" if is_active else "false",
                   "data-group": gname},
            ))
        sections.append(html.Div(
            [html.Div(gname, className="idx-group-label"), *rows],
            className="idx-group",
            style={} if any(_visible(t) for t in gtabs) else {"display": "none"},
        ))

    crumb = html.Span(
        _breadcrumb_children(active.nav_group if active else "", active.label if active else ""),
        id="nav-breadcrumb", className="idx-crumb",
    )

    return [
        html.Div([
            html.Button(
                [html.Span("☰", className="idx-glyph"), html.Span("Index")],
                id="index-menu-btn", n_clicks=0, className="idx-trigger",
                **{"aria-haspopup": "menu"},
            ),
            html.Div([
                html.Div(id="index-menu-backdrop", className="tw-backdrop"),
                html.Div(sections, className="tw-menu idx-menu", role="menu",
                         **{"aria-label": "Page index"}),
            ], id="index-menu-pop", style={"display": "none"}),
        ], className="tw-wrap"),
        crumb,
    ]


def _breadcrumb_children(group: str, label: str) -> list:
    """Group / Page breadcrumb fragments (ids let JS update them instantly)."""
    return [
        html.Span(group, id="crumb-group"),
        html.Span(" / ", className="idx-crumb-sep"),
        html.Span(label, id="crumb-label", className="idx-crumb-page"),
    ]


def create_command_palette():
    """Static markup for the ⌘K command palette (driven by command_palette.js)."""
    from .controls import icon

    def item(icon_name, title, sub, action, kbd=""):
        return html.Div([
            html.Div(icon(icon_name, 13), className="cmd-icon"),
            html.Div(title, className="cmd-title"),
            html.Div(sub, className="cmd-sub"),
            html.Span(kbd, className="cmd-kbd kbd") if kbd else html.Span(),
        ], className="cmd-item",
           **{"data-action": action, "data-search": f"{title} {sub}".lower()})

    def group(label, items):
        return html.Div(
            [html.Div(label, className="cmd-group-label"), *items],
            className="cmd-group",
        )

    tabs = get_all_tabs()
    jump = [item("chart", t.label, "Tab", f"tab:{t.id}", kbd=f"⌘{i + 1}" if i < 9 else "")
            for i, t in enumerate(tabs)]
    actions = [
        item("filter", "Change portfolio…", "Global filter", "click:#portfolio-selector-btn"),
        item("search", "Set time window…", "Reporting period range", "click:#time-window-btn"),
        item("sparkles", "Build custom metric…", "Power user · formula builder", "click:#custom-metric-btn"),
        item("help", "Contact & support", "Help", "click:#contact-btn"),
    ]

    return html.Div([
        html.Div([
            html.Div([
                icon("search", 16),
                dcc.Input(id="cmd-palette-input", className="cmd-input", type="text",
                          placeholder="Search or run command…", autoComplete="off"),
                html.Span("ESC", className="kbd"),
            ], className="cmd-input-wrap"),
            html.Div([group("Jump to", jump), group("Actions", actions)],
                     className="cmd-groups", id="cmd-palette-groups"),
            html.Div([
                html.Span("↑↓ Navigate   ↵ Select   ESC Close"),
                html.Span("✦ IRIS-D"),
            ], className="cmd-foot"),
        ], className="cmd-modal"),
    ], className="cmd-overlay", id="cmd-palette")


def _copilot_ai_msg(text):
    """One AI message bubble — same DOM shape copilot.js renders dynamically."""
    return html.Div([
        html.Div([
            html.Span("IQ", className="copilot-badge sm"),
            html.Span("Copilot", className="copilot-msg-role"),
        ], className="copilot-msg-head"),
        html.Div([
            html.Div(text, className="copilot-msg-text"),
        ], className="copilot-msg-body"),
    ], className="copilot-msg ai")


def _copilot_panel():
    """Portfolio Intelligence Copilot — foldable right-side AI assistant.

    Collapsed rail ↔ open 360px slide-over panel. All behaviour (open/collapse,
    context-aware suggested prompts, the ask → thinking → answer flow) lives in
    ``assets/copilot.js``. The backend is a placeholder: answers are
    deterministic and client-side, referencing the portfolio / tab in view.
    Whole feature is shown/hidden by the header ``CopilotToggle``.
    """
    from .controls import icon

    greeting = (
        "I'm your Portfolio Intelligence Copilot. Ask about exposure, "
        "covenants, segment trends, or market risk — answers reference the "
        "data currently in view."
    )

    rail = html.Button([
        html.Span("IQ", className="copilot-badge"),
        html.Span("Copilot", className="copilot-rail-label"),
    ], id="copilot-rail", n_clicks=0, className="copilot-rail",
       title="Open Copilot", **{"aria-label": "Open Portfolio Copilot"})

    panel = html.Aside([
        html.Div([
            html.Span("IQ", className="copilot-badge lg"),
            html.Div([
                html.Div("Portfolio Copilot", className="copilot-title"),
                html.Div(["Intelligence · ",
                          html.Span("Overview", id="copilot-subtitle")],
                         className="copilot-subtitle"),
            ], className="copilot-headmeta"),
            html.Button(icon("x", 13), id="copilot-collapse-btn", n_clicks=0,
                        className="icon-btn", style={"width": "26px", "height": "26px"},
                        title="Collapse", **{"aria-label": "Collapse Copilot"}),
        ], className="copilot-head"),
        html.Div([_copilot_ai_msg(greeting)], id="copilot-messages",
                 className="copilot-messages"),
        html.Div([
            html.Div("Suggested", className="copilot-sugg-label"),
            html.Div(id="copilot-suggestions", className="copilot-sugg-row"),
        ], className="copilot-sugg"),
        html.Div([
            dcc.Input(id="copilot-input", className="copilot-input", type="text",
                      placeholder="Ask the copilot…", autoComplete="off"),
            html.Button("↑", id="copilot-send", n_clicks=0, className="copilot-send",
                        **{"aria-label": "Send"}),
        ], className="copilot-inputbar"),
    ], id="copilot-panel", className="copilot-panel",
       **{"aria-label": "Portfolio Copilot"})

    return html.Div([rail, panel], id="copilot-root", className="copilot-root")


def create_layout(selected_portfolio, app_index_string, available_portfolios=None):
    """Create the main app shell layout."""
    from .controls import ControlPosition, get_global_controls
    from .signals import all_signal_ids

    # Render Layer 1 controls from the GlobalControl registry
    # Power-user controls are wrapped in a hidden gate div
    left_controls = []
    for c in get_global_controls(ControlPosition.LEFT):
        rendered = c.render(selected_portfolio=selected_portfolio,
                            available_portfolios=available_portfolios or [])
        if c.power_user:
            rendered = html.Div(rendered, id=f"power-gate-{c.id}", style={"display": "none"})
        left_controls.append(rendered)

    right_controls = []
    for c in get_global_controls(ControlPosition.RIGHT):
        rendered = c.render()
        if c.power_user:
            rendered = html.Div(rendered, id=f"power-gate-{c.id}", style={"display": "none"})
        right_controls.append(rendered)

    # Signal stores for cross-layer communication
    signal_stores = [dcc.Store(id=sid, data=None) for sid in all_signal_ids()]

    # Modal IDs for focus trap and Escape key handling
    _modal_ids = [
        "portfolio-delete-confirm-modal", "portfolio-create-modal",
        "perf-warning-modal", "power-user-confirm-modal",
    ]
    _modal_ids_js = ", ".join(f'"{mid}"' for mid in _modal_ids)

    return html.Div(className="min-h-screen app", children=[
        # ── Header — Ledger masthead ────────────────────────────────────────
        html.Header([
            # Row 1 — serif brand + eyebrow · controls right
            html.Div([
                html.Div([
                    html.Span("IRIS", className="masthead-title"),
                    html.Span("Portfolio Intelligence", className="masthead-eyebrow"),
                ], className="masthead-brand"),
                html.Div(className="gc-spacer"),
                *left_controls,
                *right_controls,
            ], className="header-row-1"),
            # Double rule (2px over 1px — the Ledger signature)
            html.Div(className="masthead-rule"),
            # Row 2 — ☰ Index directory + breadcrumb
            html.Nav(
                id="navigation-tabs-container",
                children=create_navigation_tabs(),
                className="header-row-2",
                role="navigation",
                **{"aria-label": "Page index"},
            ),
        ], className="header sticky top-0 z-40"),

        # ── Main content ────────────────────────────────────────────────────
        html.Main([
            html.Div([
                html.Div(id="tab-content-container", role="tabpanel"),
                html.Div([
                    html.Div(className="tab-loading-spinner"),
                    html.Div("Refreshing", className="tab-loading-text"),
                ], id="tab-loading-overlay"),
            ], id="tab-content-wrapper", className="tab-content-wrapper"),
        ], className="main-scroll"),

        # ── Modals ──────────────────────────────────────────────────────────
        # These are now anchored dropdown popovers rendered in their header
        # controls: profile-switch (ProfileAvatar), portfolio selector
        # (PortfolioSelector), time window (TimeWindowButton), custom metrics
        # (CustomMetricButton), contact & support (ContactButton). Only the
        # wizard + confirm/warning dialogs stay here.
        _portfolio_delete_confirm_modal(),
        _portfolio_create_modal(),
        _performance_warning_modal(),

        # ── Command palette (⌘K) ──────────────────────────────────────────────
        create_command_palette(),

        # ── Portfolio Intelligence Copilot (foldable right-side panel) ────────
        _copilot_panel(),
        dcc.Store(id="copilot-enabled-store", data=True, storage_type="local"),

        # ── Power User ────────────────────────────────────────────────────────
        _power_user_confirm_modal(),
        dcc.Store(id="power-user-store", data=False, storage_type="local"),

        # ── Hidden infrastructure ───────────────────────────────────────────
        dcc.Store(id="custom-metric-token-store", data=[]),
        dcc.Store(id="active-tab-store", data=None),
        dcc.Store(id="current-user-store", data=user_management.get_current_user()),
        dcc.Store(id="time-window-store", data=_initial_time_window()),
        *signal_stores,

        # ── Modal Escape key + focus trap ──────────────────────────────────
        html.Script(f"""
        (function(){{
          var MODAL_IDS = [{_modal_ids_js}];
          var FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

          function getVisibleModal(){{
            for(var i=0;i<MODAL_IDS.length;i++){{
              var el=document.getElementById(MODAL_IDS[i]);
              if(el && el.style.display && el.style.display!=='none') return el;
            }}
            return null;
          }}

          document.addEventListener('keydown',function(e){{
            var modal=getVisibleModal();
            if(!modal) return;
            if(e.key==='Escape'){{
              var close=modal.querySelector('[aria-label="Close"], .btn-outline, .detail-panel__close');
              if(close) close.click();
              return;
            }}
            if(e.key==='Tab'){{
              var focusable=Array.from(modal.querySelectorAll(FOCUSABLE)).filter(function(f){{
                return f.offsetParent!==null;
              }});
              if(!focusable.length) return;
              var first=focusable[0], last=focusable[focusable.length-1];
              if(e.shiftKey){{
                if(document.activeElement===first){{e.preventDefault();last.focus();}}
              }}else{{
                if(document.activeElement===last){{e.preventDefault();first.focus();}}
              }}
            }}
          }});

          // Focus first focusable element when modal becomes visible
          var observer=new MutationObserver(function(mutations){{
            mutations.forEach(function(m){{
              if(m.type==='attributes'&&m.attributeName==='style'){{
                var el=m.target;
                if(MODAL_IDS.indexOf(el.id)!==-1 && el.style.display && el.style.display!=='none'){{
                  setTimeout(function(){{
                    var first=el.querySelector(FOCUSABLE);
                    if(first) first.focus();
                  }},50);
                }}
              }}
            }});
          }});
          MODAL_IDS.forEach(function(id){{
            var el=document.getElementById(id);
            if(el) observer.observe(el,{{attributes:true,attributeFilter:['style']}});
          }});
        }})();
        """),
    ])


# ── Modal helpers (keep layout.py clean) ────────────────────────────────────

# Modal chrome mirrors the Time Window dropdown popover (.tw-menu): raised
# surface, default border, large radius + shadow — one popover look app-wide.
_MODAL_BG = {
    "background": "var(--bg-raised)",
    "borderRadius": "var(--r-lg)",
    "border": "1px solid var(--border-default)",
    "boxShadow": "var(--shadow-lg)",
}

_MODAL_OVERLAY = {
    "position": "fixed", "top": "0", "left": "0", "width": "100%",
    "height": "100%", "backgroundColor": "rgba(0,0,0,0.45)",
    "backdropFilter": "blur(4px)", "WebkitBackdropFilter": "blur(4px)",
    "zIndex": "1000", "display": "none",
}

_MODAL_CENTER = {
    "position": "absolute", "top": "50%", "left": "50%",
    "transform": "translate(-50%, -50%)", "zIndex": "1001",
}



def _profile_switch_modal():
    return html.Div([
        html.Div(id="profile-backdrop", className="tw-backdrop", n_clicks=0),
        html.Div([
            html.Header([
                html.Div([
                    html.H2("Switch Profile", id="profile-switch-title",
                            className="text-lg font-semibold text-ink-900 dark:text-ink-50"),
                    html.Button("✕", id="profile-switch-cancel-x", className="btn btn-ghost text-xl cursor-pointer",
                                style={"padding": "4px 8px", "minWidth": "auto", "minHeight": "auto"},
                                **{"aria-label": "Close"}),
                ], className="flex items-center justify-between"),
            ], className="px-4 py-3 border-b border-ink-100 dark:border-ink-600"),
            html.Div([
                html.Div([
                    html.Label("Select Profile", className="block text-xs font-medium mb-1 text-ink-600 dark:text-ink-500"),
                    dcc.Dropdown(id="profile-switch-dropdown", placeholder="Choose a profile...",
                                 className="text-sm", style={"fontSize": "13px"}),
                ], className="mb-4"),
                html.Div([
                    html.Button("Switch", id="profile-switch-confirm", className="btn btn-primary", style={"fontSize": "13px", "flex": "1"}),
                    html.Button("Cancel", id="profile-switch-cancel", className="btn btn-outline", style={"fontSize": "13px", "flex": "1"}),
                ], className="flex gap-2"),
            ], className="p-4"),
        ], className="tw-menu right flex flex-col",
           style={"width": "300px", "maxWidth": "calc(100vw - 32px)"}),
    ], id="profile-switch-modal", role="dialog", **{"aria-label": "Switch Profile"},
       style={"display": "none"})


def _contact_modal():
    """Contact & Support — anchored dropdown popover from the help icon."""
    from .controls import icon
    return html.Div([
        html.Div(id="contact-backdrop", className="tw-backdrop", n_clicks=0),
        html.Div([
            html.Div([
                html.H3("Contact & Support", id="contact-title"),
                html.Button(icon("x", 13), id="contact-cancel-x",
                            className="icon-btn", style={"width": "26px", "height": "26px"},
                            **{"aria-label": "Close"}),
            ], className="tw-head"),
            html.Div([
                html.H4("Contact Information",
                         className="text-sm font-semibold text-ink-700 dark:text-ink-100 mb-2"),
                html.Div([html.Strong("Email: "), html.A("support@portfolio-dashboard.com",
                          href="mailto:support@portfolio-dashboard.com",
                          style={"color": "var(--primary-400)", "textDecoration": "none"})],
                         className="text-sm mb-1"),
                html.Div([html.Strong("Phone: "), html.Span("+1 (555) 123-4567")],
                         className="text-sm mb-3"),
                html.P("Help us improve by sharing your thoughts.",
                       className="text-xs text-ink-500 dark:text-ink-500 mb-3"),
                html.Div([
                    html.Button("Close", id="contact-close", className="btn btn-outline",
                                style={"fontSize": "13px", "flex": "1"}),
                ], className="tw-actions"),
            ], className="tw-body"),
        ], className="tw-menu right flex flex-col",
           style={"width": "320px", "maxWidth": "calc(100vw - 32px)"}),
    ], id="contact-modal", role="dialog", **{"aria-label": "Contact & Support"},
       style={"display": "none"})


def _portfolio_modal():
    """Portfolio Manager modal — dropdown selector + action buttons."""
    return html.Div([
        html.Div([
            html.Header([
                html.Div([
                    html.H2("Portfolio Management", id="portfolio-modal-title",
                            className="text-lg font-semibold text-ink-900 dark:text-ink-50"),
                    html.Button("✕", id="portfolio-modal-cancel", className="btn btn-ghost text-xl cursor-pointer",
                                style={"padding": "4px 8px", "minWidth": "auto", "minHeight": "auto"},
                                **{"aria-label": "Close"}),
                ], className="flex items-center justify-between"),
            ], className="px-4 py-3 border-b border-ink-100 dark:border-ink-600"),
            html.Div([
                html.Label("Select a portfolio or create a new one:", className="block text-sm font-medium mb-2 text-ink-600 dark:text-ink-100"),
                dcc.Dropdown(id="portfolio-modal-dropdown", placeholder="Choose portfolio...", className="text-sm mb-4", style={"fontSize": "14px"}),
                html.Div([
                    html.Button("Select", id="portfolio-select-confirm", className="btn btn-primary", style={"fontSize": "13px", "flex": "1"}),
                    html.Button("Update", id="portfolio-update-btn", className="btn btn-outline", style={"fontSize": "13px", "flex": "1"}, disabled=True),
                    html.Button("Delete", id="portfolio-delete-btn", className="btn btn-danger", style={"fontSize": "13px", "flex": "1"}, disabled=True),
                ], className="flex gap-2"),
                html.Div(id="portfolio-delete-error", className="text-red-500 text-xs mt-2", style={"textAlign": "center"}),
            ], className="p-4"),
        ], className="flex flex-col",
           style={**_MODAL_BG, **_MODAL_CENTER, "width": "400px", "maxWidth": "90vw", "overflow": "visible"}),
    ], id="portfolio-modal", role="dialog", **{"aria-modal": "true", "aria-labelledby": "portfolio-modal-title"},
       style=_MODAL_OVERLAY)


def _portfolio_delete_confirm_modal():
    """Confirmation dialog before deleting a portfolio."""
    return html.Div([
        html.Div([
            html.Header([
                html.Div([
                    html.H2("Confirm Deletion", id="delete-confirm-title",
                            className="text-lg font-semibold text-ink-900 dark:text-ink-50"),
                ], className="flex items-center justify-between"),
            ], className="px-4 py-3 border-b border-ink-100 dark:border-ink-600"),
            html.Div([
                html.P(id="delete-confirm-message",
                       children="Are you sure you want to delete this portfolio? This action cannot be undone.",
                       className="text-sm text-ink-600 dark:text-ink-100 mb-4"),
                html.Div([
                    html.Button("Delete", id="portfolio-delete-confirm", className="btn btn-danger", style={"fontSize": "13px", "flex": "1"}),
                    html.Button("Cancel", id="portfolio-delete-cancel", className="btn btn-outline", style={"fontSize": "13px", "flex": "1"}),
                ], className="flex gap-2"),
            ], className="p-4"),
        ], className="flex flex-col",
           style={**_MODAL_BG, **_MODAL_CENTER, "width": "380px", "maxWidth": "90vw"}),
    ], id="portfolio-delete-confirm-modal", role="dialog", **{"aria-modal": "true", "aria-labelledby": "delete-confirm-title"},
       style=_MODAL_OVERLAY)


def _portfolio_create_modal():
    """Portfolio Creation/Edit Wizard — dynamic hierarchical filter builder."""
    return html.Div([
        html.Div([
            html.Header([
                html.Div([
                    html.H2(id="portfolio-wizard-title", children="Create New Portfolio",
                            className="text-lg font-semibold text-ink-900 dark:text-ink-50"),
                    html.Button("✕", id="portfolio-create-cancel", className="btn btn-ghost text-xl cursor-pointer",
                                style={"padding": "4px 8px", "minWidth": "auto", "minHeight": "auto"},
                                **{"aria-label": "Close"}),
                ], className="flex items-center justify-between"),
            ], className="px-4 py-3 border-b border-ink-100 dark:border-ink-600"),
            html.Div([
                # Reference portfolio dropdown
                html.Div([
                    html.Label("Reference Portfolio", className="block text-xs font-medium mb-1 text-ink-600 dark:text-ink-100"),
                    dcc.Dropdown(id="reference-portfolio-dropdown",
                                 placeholder="Start from scratch...",
                                 className="text-sm",
                                 style={"fontSize": "13px"}),
                    html.P("Select an existing portfolio to pre-populate filters, or leave blank to start fresh.",
                           className="text-xs text-ink-500 dark:text-ink-500 mt-1 mb-3"),
                ]),
                # Dynamic filter levels container — populated by callback
                html.Div(id="filter-levels-container", children=[]),
                # Add Level button
                html.Div([
                    html.Button("+ Add Level", id="add-filter-level-btn", className="btn btn-outline text-sm mt-2",
                                style={"fontSize": "12px"}),
                ], className="text-right"),
                # Portfolio name input
                html.Div([
                    html.Label("Portfolio Name", className="block text-xs font-medium mb-1 text-ink-600 dark:text-ink-100"),
                    dcc.Input(id="create-portfolio-name-input", type="text", placeholder="Enter portfolio name...",
                              className="w-full px-3 py-2 text-xs border border-ink-100 dark:border-ink-600 rounded-md focus:ring-2 focus:ring-brand-500"),
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
    ], id="portfolio-create-modal", role="dialog",
       **{"aria-modal": "true", "aria-labelledby": "portfolio-wizard-title"},
       style=_MODAL_OVERLAY)


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
            html.Header([
                html.Div([
                    html.H2("Time Window", id="time-window-title",
                            className="text-lg font-semibold text-ink-900 dark:text-ink-50"),
                    html.Button("✕", id="time-window-cancel-x", className="btn btn-ghost text-xl cursor-pointer",
                                style={"padding": "4px 8px", "minWidth": "auto", "minHeight": "auto"},
                                **{"aria-label": "Close"}),
                ], className="flex items-center justify-between"),
            ], className="px-4 py-3 border-b border-ink-100 dark:border-ink-600"),
            html.Div([
                html.Label("Select the reporting period range:", className="block text-sm font-medium mb-3 text-ink-600 dark:text-ink-100"),
                html.Div([
                    html.Div([
                        html.Label("Start Month", className="block text-xs font-medium mb-1 text-ink-600 dark:text-ink-500"),
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
                        html.Label("End Month", className="block text-xs font-medium mb-1 text-ink-600 dark:text-ink-500"),
                        dcc.Dropdown(
                            id="time-window-end-dropdown",
                            options=options,
                            value=end_val,
                            clearable=False,
                            className="text-sm",
                            style={"fontSize": "13px"},
                        ),
                    ], style={"flex": "1"}),
                ], className="flex gap-4 mb-4"),
                dcc.Store(id="time-window-dates", data=all_dates),
                html.Div([
                    html.Button("Apply", id="time-window-apply", className="btn btn-primary", style={"fontSize": "13px", "flex": "1"}),
                    html.Button("Show All", id="time-window-reset", className="btn btn-outline", style={"fontSize": "13px", "flex": "1"}),
                ], className="flex gap-2"),
                # Hidden placeholder so the callback Input still resolves
                html.Div(id="time-window-cancel", style={"display": "none"}),
            ], className="p-4"),
        ], className="flex flex-col",
           style={**_MODAL_BG, **_MODAL_CENTER, "width": "400px", "maxWidth": "90vw", "overflow": "visible"}),
    ], id="time-window-modal", role="dialog",
       **{"aria-modal": "true", "aria-labelledby": "time-window-title"},
       style=_MODAL_OVERLAY)


def _performance_warning_modal():
    """Warning when user selects Show All on the full portfolio."""
    return html.Div([
        html.Div([
            html.Header([
                html.Div([
                    html.H2("Performance Warning", id="perf-warning-title",
                            className="text-lg font-semibold text-ink-900 dark:text-ink-50"),
                ], className="flex items-center justify-between"),
            ], className="px-4 py-3 border-b border-ink-100 dark:border-ink-600"),
            html.Div([
                html.P(
                    "Loading the full portfolio over all time periods may cause "
                    "the app to slow down significantly.",
                    className="text-sm text-ink-600 dark:text-ink-100 mb-4",
                ),
                html.Div([
                    html.Button("Continue Anyway", id="perf-warning-confirm",
                                className="btn btn-danger", style={"fontSize": "13px", "flex": "1"}),
                    html.Button("Cancel", id="perf-warning-cancel",
                                className="btn btn-outline", style={"fontSize": "13px", "flex": "1"}),
                ], className="flex gap-2"),
            ], className="p-4"),
        ], className="flex flex-col",
           style={**_MODAL_BG, **_MODAL_CENTER, "width": "380px", "maxWidth": "90vw"}),
    ], id="perf-warning-modal", role="dialog",
       **{"aria-modal": "true", "aria-labelledby": "perf-warning-title"},
       style=_MODAL_OVERLAY)


def _power_user_confirm_modal():
    """Confirmation dialog before enabling power user mode."""
    return html.Div([
        html.Div([
            html.Header([
                html.Div([
                    html.H2("Enable Power User Mode", id="power-user-confirm-title",
                            className="text-lg font-semibold text-ink-900 dark:text-ink-50"),
                ], className="flex items-center justify-between"),
            ], className="px-4 py-3 border-b border-ink-100 dark:border-ink-600"),
            html.Div([
                html.P(
                    "Power User mode enables advanced controls (custom metrics, etc.) "
                    "that can modify data and may produce unexpected results.",
                    className="text-sm text-ink-600 dark:text-ink-100 mb-4",
                ),
                html.Div([
                    html.Button("Enable", id="power-user-confirm",
                                className="btn btn-primary", style={"fontSize": "13px", "flex": "1"}),
                    html.Button("Cancel", id="power-user-cancel",
                                className="btn btn-outline", style={"fontSize": "13px", "flex": "1"}),
                ], className="flex gap-2"),
            ], className="p-4"),
        ], className="flex flex-col",
           style={**_MODAL_BG, **_MODAL_CENTER, "width": "400px", "maxWidth": "90vw"}),
    ], id="power-user-confirm-modal", role="dialog",
       **{"aria-modal": "true", "aria-labelledby": "power-user-confirm-title"},
       style=_MODAL_OVERLAY)


def _custom_metric_modal():
    """Modal for building custom metrics with click-to-build formula builder."""
    from ..data.registry import DatasetRegistry

    dataset_options = []
    if DatasetRegistry.has("facilities"):
        dataset_options.append({"label": "Facilities", "value": "facilities"})

    _BTN = {
        "fontSize": "13px", "padding": "4px 10px", "minWidth": "34px",
        "minHeight": "30px", "fontFamily": "monospace", "fontWeight": "600",
    }
    _BTN_LOGIC = {
        "fontSize": "11px", "padding": "4px 8px", "minWidth": "auto",
        "minHeight": "30px", "fontWeight": "600",
    }

    return html.Div([
        html.Div(id="custom-metric-backdrop", className="tw-backdrop", n_clicks=0),
        html.Div([
            html.Header([
                html.Div([
                    html.H2("Custom Metrics", id="custom-metric-title",
                            className="text-lg font-semibold text-ink-900 dark:text-ink-50"),
                    html.Button("✕", id="custom-metric-close-x", className="btn btn-ghost text-xl cursor-pointer",
                                style={"padding": "4px 8px", "minWidth": "auto", "minHeight": "auto"},
                                **{"aria-label": "Close"}),
                ], className="flex items-center justify-between"),
            ], className="px-4 py-3 border-b border-ink-100 dark:border-ink-600"),
            html.Div([
                # Dataset selector
                html.Div([
                    html.Label("Dataset", className="block text-xs font-medium mb-1",
                               style={"color": "var(--text-secondary)"}),
                    dcc.Dropdown(id="custom-metric-dataset-dropdown", options=dataset_options,
                                 value="facilities" if dataset_options else None,
                                 clearable=False, className="text-sm", style={"fontSize": "13px"}),
                ], className="mb-3"),

                # Build Formula section
                html.Div([
                    html.H4("Build Formula", className="text-sm font-semibold mb-2",
                            style={"color": "var(--text-primary)"}),
                    # Column dropdown + add button
                    html.Div([
                        html.Div([
                            html.Label("Column", className="block text-xs font-medium mb-1",
                                       style={"color": "var(--text-secondary)"}),
                            dcc.Dropdown(id="custom-metric-column-dropdown", placeholder="Select column...",
                                         className="text-sm", style={"fontSize": "13px"}),
                        ], style={"flex": "1"}),
                        html.Div([
                            html.Label("", className="block text-xs mb-1", style={"visibility": "hidden"}),
                            html.Button("+ Col", id="custom-metric-add-col-btn", className="btn btn-outline",
                                        style={"fontSize": "12px", "padding": "6px 10px"}),
                        ]),
                    ], className="flex gap-2 items-end mb-2"),

                    # Arithmetic operator buttons
                    html.Div([
                        html.Button("+", id="custom-metric-op-add", className="btn btn-outline", style=_BTN),
                        html.Button("−", id="custom-metric-op-sub", className="btn btn-outline", style=_BTN),
                        html.Button("×", id="custom-metric-op-mul", className="btn btn-outline", style=_BTN),
                        html.Button("÷", id="custom-metric-op-div", className="btn btn-outline", style=_BTN),
                        html.Button("(", id="custom-metric-op-lparen", className="btn btn-outline", style=_BTN),
                        html.Button(")", id="custom-metric-op-rparen", className="btn btn-outline", style=_BTN),
                    ], className="flex gap-1 mb-2"),

                    # Logic / comparison buttons
                    html.Div([
                        html.Button(">=", id="custom-metric-op-gte", className="btn btn-outline", style=_BTN_LOGIC),
                        html.Button("<=", id="custom-metric-op-lte", className="btn btn-outline", style=_BTN_LOGIC),
                        html.Button(">", id="custom-metric-op-gt", className="btn btn-outline", style=_BTN_LOGIC),
                        html.Button("<", id="custom-metric-op-lt", className="btn btn-outline", style=_BTN_LOGIC),
                        html.Button("==", id="custom-metric-op-eq", className="btn btn-outline", style=_BTN_LOGIC),
                        html.Button("IF", id="custom-metric-op-if", className="btn btn-outline",
                                    style={**_BTN_LOGIC, "color": "var(--accent-400)"}),
                        html.Button("THEN", id="custom-metric-op-then", className="btn btn-outline",
                                    style={**_BTN_LOGIC, "color": "var(--accent-400)"}),
                        html.Button("ELSE", id="custom-metric-op-else", className="btn btn-outline",
                                    style={**_BTN_LOGIC, "color": "var(--accent-400)"}),
                        html.Button("AND", id="custom-metric-op-and", className="btn btn-outline",
                                    style={**_BTN_LOGIC, "color": "var(--accent-400)"}),
                        html.Button("OR", id="custom-metric-op-or", className="btn btn-outline",
                                    style={**_BTN_LOGIC, "color": "var(--accent-400)"}),
                        html.Button("TRUE", id="custom-metric-bool-true", className="btn btn-outline",
                                    style={**_BTN_LOGIC, "color": "#4D8B6F"}),
                        html.Button("FALSE", id="custom-metric-bool-false", className="btn btn-outline",
                                    style={**_BTN_LOGIC, "color": "#4D8B6F"}),
                    ], className="flex flex-wrap gap-1 mb-2"),

                    # Constant input + text constant + undo
                    html.Div([
                        dcc.Input(id="custom-metric-constant-input", type="text", placeholder="Number",
                                  className="px-2 py-1 text-xs rounded-md",
                                  style={"width": "70px", "border": "1px solid var(--border-default)",
                                         "background": "var(--bg-base)", "color": "var(--text-primary)"}),
                        html.Button("Add", id="custom-metric-add-const-btn", className="btn btn-outline",
                                    style={"fontSize": "12px", "padding": "4px 10px"}),
                        dcc.Input(id="custom-metric-text-input", type="text", placeholder="Text",
                                  className="px-2 py-1 text-xs rounded-md",
                                  style={"width": "70px", "border": "1px solid var(--border-default)",
                                         "background": "var(--bg-base)", "color": "var(--text-primary)"}),
                        html.Button("Add Text", id="custom-metric-add-text-btn", className="btn btn-outline",
                                    style={"fontSize": "12px", "padding": "4px 10px"}),
                        html.Div(style={"flex": "1"}),
                        html.Button("⌫ Undo", id="custom-metric-undo-btn", className="btn btn-ghost",
                                    style={"fontSize": "12px", "padding": "4px 10px",
                                           "color": "var(--text-muted)"}),
                    ], className="flex gap-2 items-center mb-3"),

                    # Formula display
                    html.Div([
                        html.Label("Formula", className="block text-xs font-medium mb-1",
                                   style={"color": "var(--text-secondary)"}),
                        html.Div(
                            id="custom-metric-formula-display",
                            className="px-3 py-2 rounded-md min-h-[40px] flex items-center flex-wrap gap-1",
                            style={
                                "background": "var(--bg-base)",
                                "border": "1px solid var(--border-default)",
                            },
                        ),
                    ]),
                ], className="p-3 rounded-lg mb-3",
                   style={"background": "var(--bg-surface)", "border": "1px solid var(--border-default)"}),

                # Metric name (below formula)
                html.Div([
                    html.Label("Metric Name", className="block text-xs font-medium mb-1",
                               style={"color": "var(--text-secondary)"}),
                    dcc.Input(id="custom-metric-name-input", type="text", placeholder="e.g. Leverage Ratio",
                              className="w-full px-3 py-2 text-xs rounded-md focus:ring-2 focus:ring-brand-500",
                              style={"border": "1px solid var(--border-default)",
                                     "background": "var(--bg-base)", "color": "var(--text-primary)"}),
                ], className="mb-3"),

                # Save button + status
                html.Button("Save Metric", id="custom-metric-save-btn",
                            className="btn btn-primary btn-glow w-full", style={"fontSize": "13px"}),
                html.Div(id="custom-metric-save-status", className="mt-2 text-center"),

                # Saved metrics list
                html.Div([
                    html.H4("Saved Metrics", className="text-sm font-semibold mb-2",
                            style={"color": "var(--text-primary)"}),
                    html.Div(id="custom-metric-saved-list"),
                ], className="mt-4 pt-3", style={"borderTop": "1px solid var(--border-default)"}),
            ], className="p-4 flex-1 overflow-auto"),
        ], className="tw-menu right flex flex-col",
           style={"width": "480px", "maxWidth": "calc(100vw - 32px)",
                  "maxHeight": "calc(100vh - 110px)", "overflowY": "auto"}),
        # Store for editing mode (metric name being edited, None = new)
        dcc.Store(id="custom-metric-edit-name", data=None),
    ], id="custom-metric-modal", role="dialog",
       **{"aria-label": "Custom Metrics"},
       style={"display": "none"})


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
<html lang="en">
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>IRIS — Portfolio Intelligence</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
      tailwind.config = {{
        darkMode: 'class',
        theme: {{ extend: {{
          colors: {{
            ink: {{ 900:'#16140f',800:'#1d1a13',700:'#2a261d',600:'#3d3a30',500:'#8d8775',100:'#e8e4d8',50:'#faf9f6' }},
            brand: {{500:'{p500}',400:'{p400}',300:'{p400}'}}
          }},
          boxShadow: {{
            soft: '0 1px 2px rgba(22,20,15,0.06)',
            glow: 'none'
          }},
          fontFamily: {{
            serif: ['Source Serif 4', 'Georgia', 'serif'],
            sans: ['Instrument Sans', 'system-ui', 'sans-serif'],
            mono: ['IBM Plex Mono', 'ui-monospace', 'monospace']
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
        --primary-glow: rgba({glow_rgb}, 0.10);
        --primary-glow-rgb: {glow_rgb};
        --primary-tint: rgba({glow_rgb}, 0.07);
        --primary-border: rgba({glow_rgb}, 0.30);
      }}
    </style>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preconnect" href="https://cdn.tailwindcss.com">
    <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400..700&family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
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
        // Ledger defaults to light (paper); dark only when explicitly chosen.
        var t = localStorage.getItem('theme');
        if (t === 'dark') {{
          document.documentElement.classList.add('dark');
        }} else {{
          document.documentElement.classList.remove('dark');
        }}
        // Single fixed accent (matches the chart colors). Clear any stale
        // runtime accent so the whole app stays one consistent oxblood.
        localStorage.removeItem('accent_color');
      }})();
    </script>
  </body>
</html>
'''