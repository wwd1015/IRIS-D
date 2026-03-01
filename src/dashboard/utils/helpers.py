"""
Shared helper utilities used across all three layers.

Consolidates repeated patterns (card wrappers, Plotly theming, formatters,
dropdown builders) so component files stay focused on business logic.
"""

from __future__ import annotations

from typing import Any, Optional

from dash import dcc, html
import plotly.graph_objects as go


# =============================================================================
# MODAL OVERLAY STYLES
# =============================================================================

MODAL_SHOWN: dict[str, str] = {
    "position": "fixed", "top": "0", "left": "0", "width": "100%",
    "height": "100%", "backgroundColor": "rgba(0,0,0,0.5)",
    "zIndex": "1000", "display": "block",
}
MODAL_HIDDEN: dict[str, str] = {"display": "none"}


# =============================================================================
# PLOTLY THEME
# =============================================================================

_PLOTLY_DEFAULTS: dict[str, Any] = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="rgba(255,255,255,0.85)", size=12),
    margin=dict(l=40, r=20, t=30, b=40),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.06)",
        zerolinecolor="rgba(255,255,255,0.06)",
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.06)",
        zerolinecolor="rgba(255,255,255,0.06)",
    ),
    legend=dict(
        font=dict(size=11),
        bgcolor="rgba(0,0,0,0)",
    ),
)


def plotly_theme(**overrides: Any) -> dict[str, Any]:
    """Return a Plotly ``update_layout`` dict with the standard IRIS-D theme.

    Pass keyword arguments to override any default.

    Example::

        fig.update_layout(**plotly_theme(height=400, title="My Chart"))
    """
    merged = {**_PLOTLY_DEFAULTS, **overrides}
    # Deep-merge nested dicts (xaxis, yaxis, font, margin, legend)
    for key in ("xaxis", "yaxis", "font", "margin", "legend"):
        if key in overrides and key in _PLOTLY_DEFAULTS:
            merged[key] = {**_PLOTLY_DEFAULTS[key], **overrides[key]}
    return merged


def empty_figure(message: str = "No data available", height: int = 300) -> go.Figure:
    """Return a themed empty Plotly figure with a centered message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, xanchor="center", yanchor="middle",
        showarrow=False, font=dict(size=14, color="rgba(255,255,255,0.4)"),
    )
    fig.update_layout(**plotly_theme(height=height))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


# =============================================================================
# CARD WRAPPERS
# =============================================================================

_CARD_CSS = (
    "bg-white dark:bg-ink-800 rounded-xl shadow-soft "
    "border border-slate-200 dark:border-ink-700 overflow-hidden"
)


def card_wrapper(
    children: list,
    card_id: str = "",
    css_class: str = "",
) -> html.Div:
    """Wrap *children* in the standard IRIS-D card shell.

    Parameters
    ----------
    children : list
        Dash components to place inside the card.
    card_id : str
        Optional HTML ``id`` attribute for the outer div.
    css_class : str
        Extra CSS classes appended to the default card classes.
    """
    cls = f"{_CARD_CSS} {css_class}".strip()
    kwargs: dict[str, Any] = {"className": cls}
    if card_id:
        kwargs["id"] = card_id
    return html.Div(children, **kwargs)


def card_header(title: str, subtitle: str = "") -> html.Div:
    """Render a standard card header with title and optional subtitle."""
    parts = [
        html.H3(title, className="text-sm font-semibold text-slate-800 dark:text-white"),
    ]
    if subtitle:
        parts.append(html.P(subtitle, className="text-xs text-ink-500 dark:text-slate-400 mt-0.5"))
    return html.Div(
        parts,
        className="px-4 py-3 border-b border-slate-200 dark:border-ink-700",
    )


# =============================================================================
# SIDEBAR WRAPPER
# =============================================================================

_SIDEBAR_CSS = (
    "bg-white dark:bg-ink-800 rounded-xl shadow-soft "
    "border border-slate-200 dark:border-ink-700 overflow-hidden "
    "flex flex-col min-h-[640px]"
)


def sidebar_wrapper(
    title: str,
    children: list,
    subtitle: str = "",
) -> html.Section:
    """Wrap filter controls in the standard sidebar shell."""
    header = html.Header([
        html.H2(title, className="text-sm font-semibold"),
        *(
            [html.P(subtitle, className="text-xs text-ink-500 dark:text-slate-400")]
            if subtitle else []
        ),
    ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700 flex items-center justify-between")

    body = html.Div(children, className="p-4 flex-1 overflow-auto")
    return html.Section([header, body], className=_SIDEBAR_CSS)


# =============================================================================
# TOOLBAR ROW
# =============================================================================

_TOOLBAR_CSS = (
    "flex items-end justify-between gap-4 p-4 mb-4 "
    "bg-white dark:bg-ink-800 rounded-xl shadow-soft "
    "border border-slate-200 dark:border-ink-700"
)


def toolbar_row(children: list, css_class: str = "") -> html.Div:
    """Wrap toolbar controls in the Layer 2 toolbar row."""
    cls = f"{_TOOLBAR_CSS} {css_class}".strip()
    return html.Div(children, className=cls)


# =============================================================================
# DROPDOWN FILTER BUILDER
# =============================================================================

def dropdown_filter(
    id: str,
    label: str,
    options: list[dict] | None = None,
    value: Any = None,
    multi: bool = False,
    placeholder: str = "Select...",
    width: str = "min-w-[180px]",
) -> html.Div:
    """Build a labeled ``dcc.Dropdown`` with consistent styling.

    This is used in sidebars (Layer 3) and toolbars (Layer 2).
    """
    return html.Div([
        html.Label(
            label,
            className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300",
        ),
        dcc.Dropdown(
            id=id,
            options=options or [],
            value=value,
            multi=multi,
            placeholder=placeholder,
            className="text-xs",
            style={"fontSize": "12px"},
        ),
    ], className=f"{width} flex-shrink-0")


# =============================================================================
# FORMATTERS
# =============================================================================

_METRIC_NAME_OVERRIDES: dict[str, str] = {
    "warf": "WARF",
    "war": "WAR",
    "dscr": "DSCR",
    "ltv": "LTV",
    "ebitda": "EBITDA",
    "wac": "WAC",
    "wal": "WAL",
}


def format_metric_name(snake_name: str) -> str:
    """Convert a ``snake_case`` metric name to display-friendly ``Title Case``.

    Handles special acronyms (WARF, DSCR, LTV, EBITDA, etc.).

    >>> format_metric_name("avg_balance")
    'Avg Balance'
    >>> format_metric_name("warf")
    'WARF'
    """
    lower = snake_name.lower()
    if lower in _METRIC_NAME_OVERRIDES:
        return _METRIC_NAME_OVERRIDES[lower]
    return snake_name.replace("_", " ").title()


def format_currency(value: float, abbreviate: bool = True) -> str:
    """Format a numeric value as a currency string.

    >>> format_currency(2_500_000)
    '$2.5M'
    >>> format_currency(950, abbreviate=False)
    '$950'
    """
    if abbreviate:
        if abs(value) >= 1e9:
            return f"${value / 1e9:.1f}B"
        if abs(value) >= 1e6:
            return f"${value / 1e6:.1f}M"
        if abs(value) >= 1e3:
            return f"${value / 1e3:.0f}K"
    return f"${value:,.0f}"


def format_percent(value: float, decimals: int = 1) -> str:
    """Format a float as a percentage string.

    >>> format_percent(0.1234)
    '12.3%'
    """
    return f"{value * 100:.{decimals}f}%"
