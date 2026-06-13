"""
GlobalControl hierarchy — Layer 1 header controls.

Each control is a self-contained class that renders into the sticky header bar
and declares its own callbacks via ``callback_specs()``.  The layout auto-
discovers controls through the registry.

To add a new global control::

    class NotificationBell(GlobalControl):
        id = "notification-bell"
        label = "Notifications"
        position = ControlPosition.RIGHT
        order = 35

        def render(self):
            return html.Button("🔔", id=self.id, className="header-btn")

    register_global_control(NotificationBell())
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from dash import dcc, html

from .cards import CallbackSpec
from .signals import Signal


def icon(name: str, size: int = 16) -> html.Span:
    """Return a monochrome mask-icon span that inherits ``currentColor``.

    Icon glyphs are defined as CSS ``mask-image`` rules (``.ic-<name>``) in
    ``assets/style.css`` so they adapt to theme and hover automatically.
    """
    return html.Span(
        className=f"ic ic-{name}",
        style={"width": f"{size}px", "height": f"{size}px"},
    )


# =============================================================================
# REGISTRY
# =============================================================================


class ControlPosition(Enum):
    """Where in the header a control appears."""

    LEFT = "left"  # next to the app title
    RIGHT = "right"  # right side of the header


_GLOBAL_CONTROLS: dict[str, "GlobalControl"] = {}


def register_global_control(ctrl: "GlobalControl") -> None:
    """Register a global control instance.  Call at module level."""
    _GLOBAL_CONTROLS[ctrl.id] = ctrl


def get_global_controls(position: Optional[ControlPosition] = None) -> list["GlobalControl"]:
    """Return registered controls, optionally filtered by *position*."""
    ctrls = list(_GLOBAL_CONTROLS.values())
    if position is not None:
        ctrls = [c for c in ctrls if c.position == position]
    return sorted(ctrls, key=lambda c: c.order)


def get_all_global_controls() -> list["GlobalControl"]:
    """Return every registered global control, sorted by order."""
    return sorted(_GLOBAL_CONTROLS.values(), key=lambda c: c.order)


# =============================================================================
# BASE CLASS
# =============================================================================


class GlobalControl(ABC):
    """Abstract base for controls in the sticky header bar (Layer 1).

    Attributes
    ----------
    id : str
        Unique identifier (used as HTML id prefix).
    label : str
        Human-readable label.
    position : ControlPosition
        LEFT (near title) or RIGHT (near user actions).
    order : int
        Sort key within the position group.  Lower = further left.
    """

    id: str
    label: str = ""
    position: ControlPosition = ControlPosition.RIGHT
    order: int = 50
    power_user: bool = False

    @abstractmethod
    def render(self, **kwargs) -> html.Div:
        """Return the Dash component tree for this control."""
        ...

    def callback_specs(self) -> list[CallbackSpec]:
        """Declare Dash callbacks.  Override in subclasses that need interactivity."""
        return []


# =============================================================================
# BUILT-IN CONTROLS
# =============================================================================


class PortfolioSelector(GlobalControl):
    """Dropdown for selecting the active portfolio (Layer 1 → all layers)."""

    id = "portfolio-selector"
    label = "Portfolio"
    position = ControlPosition.LEFT
    order = 10

    def __init__(self, selected: str = "", options: list[str] | None = None):
        self._selected = selected
        self._options = options or []

    def render(self, **kwargs) -> html.Div:
        selected = kwargs.get("selected_portfolio", self._selected)
        options = kwargs.get("available_portfolios", self._options)
        _btn = {"fontSize": "12px", "flex": "1"}
        return html.Div([
            html.Button(
                id="portfolio-selector-btn",
                children=[
                    html.Span(className="portfolio-pill-dot"),
                    html.Span(selected or "Select Portfolio"),
                    html.Span("▾", className="portfolio-pill-caret"),
                ],
                n_clicks=0,
                className="portfolio-pill",
                title="Click to change portfolio",
            ),
            dcc.Dropdown(
                id="universal-portfolio-dropdown",
                options=[{"label": p, "value": p} for p in options],
                value=selected,
                style={"display": "none"},
            ),
            html.Div([
                html.Div(id="portfolio-backdrop", className="tw-backdrop", n_clicks=0),
                html.Div([
                    html.Div([
                        html.H3("Portfolio"),
                        html.Button(icon("x", 13), id="portfolio-modal-cancel",
                                    className="icon-btn", style={"width": "26px", "height": "26px"},
                                    **{"aria-label": "Close"}),
                    ], className="tw-head"),
                    html.Div([
                        html.Label("Select a portfolio or create a new one", className="tw-label"),
                        dcc.Dropdown(id="portfolio-modal-dropdown", placeholder="Choose portfolio…",
                                     className="text-xs", style={"fontSize": "12px", "marginBottom": "12px"}),
                        html.Div([
                            html.Button("Select", id="portfolio-select-confirm",
                                        className="btn btn-primary", style=_btn),
                            html.Button("Update", id="portfolio-update-btn",
                                        className="btn btn-outline", style=_btn, disabled=True),
                            html.Button("Delete", id="portfolio-delete-btn",
                                        className="btn btn-danger", style=_btn, disabled=True),
                        ], className="tw-actions"),
                        html.Div(id="portfolio-delete-error", className="text-red-500 text-xs mt-2",
                                 style={"textAlign": "center"}),
                    ], className="tw-body"),
                ], className="tw-menu", role="dialog", **{"aria-label": "Portfolio"}),
            ], id="portfolio-modal", style={"display": "none"}),
        ], className="tw-wrap")

    def callback_specs(self) -> list[CallbackSpec]:
        # The portfolio dropdown callback is handled by the tab navigation
        # callback in app.py since it needs to rebuild the entire tab.
        # We declare the signal write here for documentation:
        return []


class ProfileAvatar(GlobalControl):
    """Avatar button that opens the profile-switch modal."""

    id = "profile-avatar"
    label = "Profile"
    position = ControlPosition.RIGHT
    order = 30

    def render(self, **kwargs) -> html.Button:
        from ..auth import user_management
        name = user_management.get_current_user()
        words = name.split() if name else []
        initials = (words[0][0] + words[-1][0]).upper() if len(words) >= 2 else (name[0].upper() if name else "?")
        from .layout import _profile_switch_modal
        return html.Div([
            html.Button(
                id="profile-avatar-btn",
                children=initials,
                n_clicks=0,
                className="avatar",
                title="Switch Profile",
            ),
            _profile_switch_modal(),
        ], className="tw-wrap")


class ThemeToggle(GlobalControl):
    """Dark / light mode toggle button."""

    id = "theme-toggle"
    label = "Theme"
    position = ControlPosition.RIGHT
    order = 20

    def render(self, **kwargs) -> html.Button:
        return html.Button(
            html.Span(id="theme-toggle-icon", className="ic ic-moon",
                      style={"width": "15px", "height": "15px"}),
            id="theme-toggle",
            n_clicks=0,
            className="icon-btn theme-toggle-btn",
            title="Toggle theme",
        )

    def callback_specs(self) -> list[CallbackSpec]:
        return [CallbackSpec(
            outputs=[("theme-toggle-icon", "className"), (Signal.THEME, "data")],
            inputs=[("theme-toggle", "n_clicks")],
            client_side="""\
            function(n_clicks){
              const root = document.documentElement;
              document.body.style.removeProperty('color');
              document.body.style.removeProperty('background');
              if (!window._themeInit){
                const s = localStorage.getItem('theme');
                if (s === 'dark') root.classList.add('dark');
                else root.classList.remove('dark');
                window._themeInit = true;
              }
              if (n_clicks && n_clicks > 0){
                const isDark = root.classList.toggle('dark');
                const mode = isDark ? 'dark' : 'light';
                localStorage.setItem('theme', mode);
                return ['ic ' + (isDark ? 'ic-moon' : 'ic-sun'), mode];
              }
              var mode = root.classList.contains('dark') ? 'dark' : 'light';
              return ['ic ' + (mode === 'dark' ? 'ic-moon' : 'ic-sun'), mode];
            }
            """,
        )]


class AccentColorPicker(GlobalControl):
    """Small button to cycle through accent color palettes at runtime."""

    id = "accent-color-picker"
    label = "Accent Color"
    position = ControlPosition.RIGHT
    order = 22  # right after theme toggle

    def render(self, **kwargs) -> html.Button:
        return html.Button(
            icon("sliders", 15),
            id="accent-color-btn",
            n_clicks=0,
            className="icon-btn",
            title="Change accent color",
        )

    def callback_specs(self) -> list[CallbackSpec]:
        return [CallbackSpec(
            outputs=[("accent-color-btn", "title")],
            inputs=[("accent-color-btn", "n_clicks")],
            client_side="""\
            function(n_clicks){
              var palettes = window.__IRIS_PALETTES || {};
              var keys = Object.keys(palettes);
              if (!keys.length) return window.dash_clientside.no_update;
              var cur = localStorage.getItem('accent_color') || keys[0];
              if (n_clicks && n_clicks > 0){
                var idx = keys.indexOf(cur);
                cur = keys[(idx + 1) % keys.length];
                localStorage.setItem('accent_color', cur);
              }
              var p = palettes[cur];
              if (p){
                var r = document.documentElement.style;
                r.setProperty('--primary-400', p['400']);
                r.setProperty('--primary-500', p['500']);
                r.setProperty('--primary-600', p['600']);
                r.setProperty('--primary-700', p['700']);
                r.setProperty('--primary-glow', 'rgba(' + p.glow + ', 0.12)');
                r.setProperty('--primary-glow-rgb', p.glow);
                r.setProperty('--primary-tint', 'rgba(' + p.glow + ', 0.08)');
                r.setProperty('--primary-border', 'rgba(' + p.glow + ', 0.28)');
              }
              return 'Accent: ' + cur;
            }
            """,
        )]


class TimeWindowButton(GlobalControl):
    """Button showing the active time window; opens a modal to adjust it."""

    id = "time-window"
    label = "Time Window"
    position = ControlPosition.LEFT
    order = 15  # right after portfolio selector

    def render(self, **kwargs) -> html.Div:
        from datetime import datetime as _dt
        import polars as pl
        from ..app_state import app_state

        start, end = app_state.get_time_window()
        label = _format_time_label(start, end)

        all_dates = (
            app_state.facilities_df["reporting_date"].unique().sort().cast(pl.Utf8).to_list()
            if not app_state.facilities_df.is_empty() else []
        )
        options = [
            {"label": _dt.fromisoformat(d[:10]).strftime("%b %Y"), "value": d[:10]}
            for d in all_dates
        ]
        start_val = start[:10] if start else (all_dates[0][:10] if all_dates else None)
        end_val = end[:10] if end else (all_dates[-1][:10] if all_dates else None)

        return html.Div([
            html.Button(
                [html.Span(className="dot"), html.Span(label),
                 html.Span("▾", className="portfolio-pill-caret", style={"marginLeft": "4px"})],
                id="time-window-btn", n_clicks=0, className="time-pill",
                title="Change time window",
            ),
            html.Div([
                html.Div(id="time-window-backdrop", className="tw-backdrop", n_clicks=0),
                html.Div([
                    html.Div([
                        html.H3("Time Window"),
                        html.Button(icon("x", 13), id="time-window-cancel-x",
                                    className="icon-btn", style={"width": "26px", "height": "26px"},
                                    **{"aria-label": "Close"}),
                    ], className="tw-head"),
                    html.Div([
                        html.Div([
                            html.Button("3M", id="tw-preset-3m", n_clicks=0, className="tw-preset"),
                            html.Button("6M", id="tw-preset-6m", n_clicks=0, className="tw-preset"),
                            html.Button("1Y", id="tw-preset-1y", n_clicks=0, className="tw-preset"),
                            html.Button("2Y", id="tw-preset-2y", n_clicks=0, className="tw-preset"),
                            html.Button("ALL", id="tw-preset-all", n_clicks=0, className="tw-preset"),
                        ], className="tw-presets"),
                        html.Div([
                            html.Div([
                                html.Label("Start month", className="tw-label"),
                                dcc.Dropdown(id="time-window-start-dropdown", options=options,
                                             value=start_val, clearable=False,
                                             className="text-xs", style={"fontSize": "12px"}),
                            ], className="tw-field"),
                            html.Div([
                                html.Label("End month", className="tw-label"),
                                dcc.Dropdown(id="time-window-end-dropdown", options=options,
                                             value=end_val, clearable=False,
                                             className="text-xs", style={"fontSize": "12px"}),
                            ], className="tw-field"),
                        ], className="tw-fields"),
                        html.Div([
                            html.Button("Apply", id="time-window-apply", n_clicks=0, className="tw-btn primary"),
                            html.Button("Show All", id="time-window-reset", n_clicks=0, className="tw-btn outline"),
                        ], className="tw-actions"),
                        dcc.Store(id="time-window-dates", data=all_dates),
                        html.Div(id="time-window-cancel", style={"display": "none"}),
                    ], className="tw-body"),
                ], className="tw-menu", role="dialog", **{"aria-label": "Time window"}),
            ], id="time-window-modal", style={"display": "none"}),
        ], className="tw-wrap")


def _format_time_label(start: str | None, end: str | None) -> str:
    """Format ISO dates as "Mar '24 → Mar '26" (Ledger pill style)."""
    from datetime import datetime
    if start and end:
        s = datetime.fromisoformat(start[:10])
        e = datetime.fromisoformat(end[:10])
        return f"{s.strftime('%b')} '{s.strftime('%y')} → {e.strftime('%b')} '{e.strftime('%y')}"
    return "All Time"


class CustomMetricButton(GlobalControl):
    """Button that opens the custom metric formula builder modal."""

    id = "custom-metric"
    label = "Custom Metrics"
    position = ControlPosition.LEFT
    order = 20  # after time window
    power_user = True

    def render(self, **kwargs) -> html.Div:
        from .layout import _custom_metric_modal
        return html.Div([
            html.Button(
                icon("sparkles", 15),
                id="custom-metric-btn",
                n_clicks=0,
                className="icon-btn",
                title="Custom Metrics",
            ),
            _custom_metric_modal(),
        ], className="tw-wrap")


class PowerUserToggle(GlobalControl):
    """Toggle button to enable/disable power user mode (shows advanced controls)."""

    id = "power-user-toggle"
    label = "Power User"
    position = ControlPosition.RIGHT
    order = 24

    def render(self, **kwargs) -> html.Button:
        return html.Button(
            icon("bolt", 15),
            id="power-user-toggle-btn",
            n_clicks=0,
            className="icon-btn power-user-toggle-btn",
            title="Power User Mode",
            style={"opacity": "0.6"},
        )

    def callback_specs(self) -> list[CallbackSpec]:
        specs = []

        # 1. Store changes → update toggle button style + show/hide gated controls
        specs.append(CallbackSpec(
            outputs=[("power-user-toggle-btn", "style")],
            inputs=[("power-user-store", "data")],
            client_side="""\
            function(active){
              document.querySelectorAll('[id^="power-gate-"]').forEach(function(el){
                el.style.display = active ? '' : 'none';
              });
              if (active){
                return {
                  "opacity": "1",
                  "background": "var(--primary-tint)",
                  "color": "var(--primary-400)"
                };
              }
              return {"opacity": "0.6"};
            }
            """,
        ))

        # 2. Single callback for toggle click, confirm, cancel → store + modal
        specs.append(CallbackSpec(
            outputs=[("power-user-store", "data"), ("power-user-confirm-modal", "style")],
            inputs=[
                ("power-user-toggle-btn", "n_clicks"),
                ("power-user-confirm", "n_clicks"),
                ("power-user-cancel", "n_clicks"),
            ],
            states=[("power-user-store", "data")],
            prevent_initial_call=True,
            client_side="""\
            function(nToggle, nConfirm, nCancel, active){
              var nu = window.dash_clientside.no_update;
              var hidden = {"position":"fixed","top":"0","left":"0","width":"100%",
                "height":"100%","backgroundColor":"rgba(0,0,0,0.5)","zIndex":"1000","display":"none"};
              var show = Object.assign({}, hidden, {"display":"flex"});
              var ctx = window.dash_clientside.callback_context;
              if (!ctx || !ctx.triggered || !ctx.triggered.length) return [nu, nu];
              var tid = ctx.triggered[0].prop_id;
              if (tid === 'power-user-confirm.n_clicks'){
                localStorage.setItem('power_user_confirmed', 'true');
                return [true, hidden];
              }
              if (tid === 'power-user-cancel.n_clicks'){
                return [nu, hidden];
              }
              // toggle button
              if (active) return [false, hidden];
              if (localStorage.getItem('power_user_confirmed') === 'true'){
                return [true, hidden];
              }
              return [nu, show];
            }
            """,
        ))

        return specs


class ContactButton(GlobalControl):
    """Button that opens the contact/support modal."""

    id = "contact-btn"
    label = "Contact"
    position = ControlPosition.RIGHT
    order = 26

    def render(self, **kwargs) -> html.Div:
        from .layout import _contact_modal
        return html.Div([
            html.Button(
                icon("help", 15),
                id="contact-btn",
                n_clicks=0,
                className="icon-btn",
                title="Contact & Support",
            ),
            _contact_modal(),
        ], className="tw-wrap")


class CommandPaletteButton(GlobalControl):
    """Search-style trigger that opens the ⌘K command palette."""

    id = "command-palette"
    label = "Search"
    position = ControlPosition.LEFT
    order = 17  # after the time-window pill

    def render(self, **kwargs) -> html.Button:
        # Compact trigger — the Ledger masthead keeps controls quiet.
        return html.Button(
            [
                icon("search", 13),
                html.Span("⌘K", className="kbd"),
            ],
            id="command-palette-trigger",
            n_clicks=0,
            className="cmd-hint",
            title="Search facilities, metrics, portfolios (⌘K)",
        )


# =============================================================================
# AUTO-REGISTER BUILT-IN CONTROLS
# =============================================================================

register_global_control(PortfolioSelector())
register_global_control(TimeWindowButton())
register_global_control(CommandPaletteButton())
register_global_control(ProfileAvatar())
register_global_control(ThemeToggle())
# AccentColorPicker intentionally NOT registered: runtime accent switching
# desynced the CSS chrome from the (fixed-color) chart series. The app uses a
# single accent (config.settings.ui.accent_color → injected --primary-*).
register_global_control(CustomMetricButton())
register_global_control(PowerUserToggle())
register_global_control(ContactButton())
