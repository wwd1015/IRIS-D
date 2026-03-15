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
        return html.Div([
            html.Span("Portfolio", className="control-label"),
            html.Button(
                id="portfolio-selector-btn",
                children=selected or "Select Portfolio",
                n_clicks=0,
                className="header-btn portfolio-selector-btn",
                title="Click to change portfolio",
            ),
            dcc.Dropdown(
                id="universal-portfolio-dropdown",
                options=[{"label": p, "value": p} for p in options],
                value=selected,
                style={"display": "none"},
            ),
        ], className="ml-4")

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
    order = 20

    def render(self, **kwargs) -> html.Button:
        from ..auth import user_management
        name = user_management.get_current_user()
        words = name.split() if name else []
        initials = (words[0][0] + words[-1][0]).upper() if len(words) >= 2 else (name[0].upper() if name else "?")
        return html.Button(
            id="profile-avatar-btn",
            children=initials,
            n_clicks=0,
            className=(
                "ml-2 h-8 w-8 rounded-full text-white text-sm font-semibold "
                "flex items-center justify-center cursor-pointer "
                "transition-all duration-200"
            ),
            style={
                "background": "var(--primary-500)",
                "boxShadow": "none",
            },
            title="Switch Profile",
        )


class ThemeToggle(GlobalControl):
    """Dark / light mode toggle button."""

    id = "theme-toggle"
    label = "Theme"
    position = ControlPosition.RIGHT
    order = 30

    def render(self, **kwargs) -> html.Button:
        return html.Button(
            "🌙",
            id="theme-toggle",
            n_clicks=0,
            className="header-btn theme-toggle-btn",
        )

    def callback_specs(self) -> list[CallbackSpec]:
        return [CallbackSpec(
            outputs=[("theme-toggle", "children"), (Signal.THEME, "data")],
            inputs=[("theme-toggle", "n_clicks")],
            client_side="""\
            function(n_clicks){
              const root = document.documentElement;
              document.body.style.removeProperty('color');
              document.body.style.removeProperty('background');
              if (!window._themeInit){
                const s = localStorage.getItem('theme');
                if (s === 'light') root.classList.remove('dark');
                window._themeInit = true;
              }
              if (n_clicks && n_clicks > 0){
                const isDark = root.classList.toggle('dark');
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
                return [isDark ? '🌙' : '☀️', isDark ? 'dark' : 'light'];
              }
              var mode = root.classList.contains('dark') ? 'dark' : 'light';
              return [mode === 'dark' ? '🌙' : '☀️', mode];
            }
            """,
        )]


class AccentColorPicker(GlobalControl):
    """Small button to cycle through accent color palettes at runtime."""

    id = "accent-color-picker"
    label = "Accent Color"
    position = ControlPosition.RIGHT
    order = 31  # right after theme toggle

    def render(self, **kwargs) -> html.Button:
        return html.Button(
            "🎨",
            id="accent-color-btn",
            n_clicks=0,
            className="header-btn",
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
        from ..app_state import app_state
        start, end = app_state.get_time_window()
        label = _format_time_label(start, end)
        return html.Div([
            html.Span("Time Window", className="control-label"),
            html.Button(
                label,
                id="time-window-btn",
                n_clicks=0,
                className="header-btn portfolio-selector-btn",
                title="Change time window",
            ),
        ])


def _format_time_label(start: str | None, end: str | None) -> str:
    """Format ISO dates as 'Jan 2025 – Jan 2026'."""
    from datetime import datetime
    if start and end:
        s = datetime.fromisoformat(start[:10])
        e = datetime.fromisoformat(end[:10])
        return f"{s.strftime('%b %Y')} – {e.strftime('%b %Y')}"
    return "All Time"


class CustomMetricButton(GlobalControl):
    """Button that opens the custom metric formula builder modal."""

    id = "custom-metric"
    label = "Custom Metrics"
    position = ControlPosition.LEFT
    order = 20  # after time window
    power_user = True

    def render(self, **kwargs) -> html.Div:
        return html.Div([
            html.Span("Metrics", className="control-label"),
            html.Button(
                "fx",
                id="custom-metric-btn",
                n_clicks=0,
                className="header-btn portfolio-selector-btn",
                title="Custom Metrics",
                style={"fontStyle": "italic"},
            ),
        ])


class PowerUserToggle(GlobalControl):
    """Toggle button to enable/disable power user mode (shows advanced controls)."""

    id = "power-user-toggle"
    label = "Power User"
    position = ControlPosition.RIGHT
    order = 25

    def render(self, **kwargs) -> html.Button:
        return html.Button(
            "\u2699\ufe0f",
            id="power-user-toggle-btn",
            n_clicks=0,
            className="header-btn power-user-toggle-btn",
            title="Power User Mode",
            style={"fontSize": "16px", "opacity": "0.6"},
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
                  "fontSize": "16px", "opacity": "1",
                  "border": "1px solid var(--primary-500)",
                  "boxShadow": "none"
                };
              }
              return {"fontSize": "16px", "opacity": "0.6"};
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
    order = 40

    def render(self, **kwargs) -> html.Button:
        return html.Button(
            "Contact",
            id="contact-btn",
            n_clicks=0,
            className="header-btn",
        )


# =============================================================================
# AUTO-REGISTER BUILT-IN CONTROLS
# =============================================================================

register_global_control(PortfolioSelector())
register_global_control(TimeWindowButton())
register_global_control(ProfileAvatar())
register_global_control(ThemeToggle())
register_global_control(AccentColorPicker())
register_global_control(CustomMetricButton())
register_global_control(PowerUserToggle())
register_global_control(ContactButton())
