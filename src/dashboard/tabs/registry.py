"""
Tab registry – the core of the extensible tab system.

Each tab is a subclass of :class:`BaseTab` that declares:

  - ``id``, ``label``, ``order``, ``required_roles``
  - ``tier``, ``tier_tooltip``, ``content_layout``
  - ``get_toolbar_controls(ctx)`` → list[ToolbarControl]   (Layer 2)
  - ``get_cards(ctx)``            → list[DisplayCard]       (Layer 3)
  - ``render_sidebar(ctx)``       → Dash component or None  (Layer 3)
  - ``render_content(ctx)``       → Dash component          (fallback)
  - ``register_callbacks(app)``   → called once at startup

Render call hierarchy
---------------------
::

    render(ctx)
    ├── get_toolbar_controls(ctx)  →  Layer 2: full-width toolbar bar
    ├── render_sidebar(ctx)        →  Layer 3: optional left-side panel
    └── render_content(ctx)        →  Layer 3: main content area
        └── get_cards(ctx)         →      declarative card grid (if not overridden)

The framework iterates over registered tabs to build navigation buttons,
route tab clicks, and wire up callbacks — no manual wiring needed.
"""

from __future__ import annotations
from abc import ABC
from enum import Enum
from typing import Optional

from dash import html

# ── Global registry ────────────────────────────────────────────────────────────
_TABS: dict[str, "BaseTab"] = {}


class ContentLayout(Enum):
    """Pre-defined CSS grid layouts for the tab content area."""
    FULL = "content-layout--full"
    TWO_COL = "content-layout--two-col"
    THREE_COL = "content-layout--three-col"
    WIDE_LEFT = "content-layout--wide-left"
    WIDE_RIGHT = "content-layout--wide-right"
    FOUR_COL = "content-layout--four-col"


class TabContext:
    """
    Shared context object passed to every tab's render methods.

    Holds references to shared data so tabs don't need global imports.
    Extend this class as the app grows (e.g. add user info, filters, etc.).
    """
    def __init__(
        self,
        selected_portfolio: str,
        available_portfolios: list[str],
        portfolios: dict,
        facilities_df,
        latest_facilities,
        custom_metrics: dict,
        get_filtered_data,
    ):
        self.selected_portfolio = selected_portfolio
        self.available_portfolios = available_portfolios
        self.portfolios = portfolios
        self.facilities_df = facilities_df
        self.latest_facilities = latest_facilities
        self.custom_metrics = custom_metrics
        self.get_filtered_data = get_filtered_data


class BaseTab(ABC):
    """
    Abstract base class for dashboard tabs.

    Subclass this and implement the desired methods to create a new tab.
    The framework handles navigation, routing, and callback wiring
    automatically.

    **Three ways to define content** (choose one):

    1. **Declarative (recommended)**: override ``get_cards()`` to return a list
       of :class:`DisplayCard` instances.  The framework renders them in a grid.
    2. **Direct**: override ``render_content()`` for full control.
    3. **Custom**: override ``render()`` for a totally custom layout.

    Attributes
    ----------
    id : str
        Unique slug used in HTML IDs (e.g. ``"portfolio-summary"``).
    label : str
        Display text in the navigation bar.
    order : int
        Sort key — lower numbers appear first (left-most in nav bar).
    required_roles : list[str] | None
        If set, only users whose role appears in the list see this tab.
        ``None`` or ``[]`` means the tab is visible to everyone.
    tier : str
        Tier badge level: ``"gold"``, ``"silver"``, or ``"bronze"``.
    tier_tooltip : str
        Hover tooltip text for the tier badge.
    content_layout : ContentLayout
        CSS grid layout preset for the content area.
    primary_column : int
        0-indexed column whose height sets the grid row height.
        Other columns scroll if their content overflows.
    """

    id: str
    label: str
    order: int = 100
    required_roles: Optional[list[str]] = None
    tier: str = "bronze"
    tier_tooltip: str = ""
    content_layout: ContentLayout = ContentLayout.FULL
    primary_column: int = 0
    nav_align: str = "left"

    # ── Tier badge ────────────────────────────────────────────────────────

    def _render_tier_badge(self) -> html.Div:
        """Render a labeled tier badge aligned with toolbar controls."""
        return html.Div([
            html.Span("Status", className="control-label"),
            html.Div(
                className=f"tier-badge tier-badge--{self.tier}",
                **{"data-tooltip": self.tier_tooltip or self.tier.capitalize()},
            ),
        ], className="tier-badge-wrapper")

    # ── Layer 2: Toolbar ───────────────────────────────────────────────────

    def get_toolbar_controls(self, ctx: TabContext) -> list:
        """Return Layer 2 toolbar controls for this tab.

        The framework renders them in a full-width row above the
        sidebar + content grid.  Return an empty list for no toolbar.

        Returns
        -------
        list of :class:`ToolbarControl`
        """
        return []

    # ── Layer 3: Sidebar ───────────────────────────────────────────────────

    def render_sidebar(self, ctx: TabContext) -> Optional[html.Div]:
        """Return sidebar component, or None for no sidebar."""
        return None

    # ── Layer 3: Cards / Content ───────────────────────────────────────────

    def get_cards(self, ctx: TabContext) -> list:
        """Return Layer 3 display cards declaratively.

        Override this to compose your tab from reusable card instances.
        If this returns a non-empty list, ``render_content()`` uses the
        card grid renderer automatically.

        Returns
        -------
        list of :class:`DisplayCard`
        """
        return []

    def render_content(self, ctx: TabContext) -> html.Div:
        """Return the main content component.

        By default, renders cards from ``get_cards()``.  Override for
        full manual control of the content area.
        """
        cards = self.get_cards(ctx)
        if cards:
            from ..components.cards import render_card_grid
            return render_card_grid(cards, ctx)
        return html.Div("No content defined", className="p-4 text-slate-400")

    # ── Full assembly ──────────────────────────────────────────────────────

    def render(self, ctx: TabContext) -> html.Div:
        """
        Assemble the full tab layout:

        1. Layer 2 toolbar (always rendered, with tier badge)
        2. Layer 3 content grid (using content_layout preset)
        """
        from ..components.toolbar import render_toolbar

        # Layer 2: toolbar (always rendered)
        toolbar_controls = self.get_toolbar_controls(ctx)
        toolbar = render_toolbar(toolbar_controls, ctx, badge=self._render_tier_badge())

        # Layer 3: sidebar + content
        sidebar = self.render_sidebar(ctx)
        content = self.render_content(ctx)

        if sidebar is not None:
            grid_class = "grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4 items-stretch"
            body = html.Div([sidebar, content], className=grid_class)
        else:
            raw = content.children if hasattr(content, 'children') else [content]
            wrapped = []
            for i, child in enumerate(raw):
                if i == self.primary_column:
                    wrapped.append(html.Div(child, className="content-grid-col content-grid-col--primary"))
                else:
                    wrapped.append(html.Div(child, className="content-grid-col content-grid-col--scroll"))
            body = html.Div(
                wrapped,
                className=f"content-grid {self.content_layout.value}",
            )

        return html.Div([toolbar, body], className="tab-shell")

    # ── Callbacks ──────────────────────────────────────────────────────────

    def register_callbacks(self, app) -> None:
        """Register any Dash callbacks specific to this tab.

        Called once during app startup by :class:`CallbackRegistry`.
        Override to add interactivity.
        """
        pass


# ── Registry helpers ───────────────────────────────────────────────────────────

def register_tab(tab: BaseTab) -> None:
    """Register a tab instance. Call at module level in each tab file.

    Raises
    ------
    ValueError
        If a tab with the same ``id`` is already registered.
    """
    if tab.id in _TABS:
        raise ValueError(f"Tab '{tab.id}' is already registered.")
    _TABS[tab.id] = tab


def get_all_tabs() -> list[BaseTab]:
    """Return all registered tabs, sorted by order then label."""
    return sorted(_TABS.values(), key=lambda t: (t.order, t.label))


def get_tab(tab_id: str) -> Optional[BaseTab]:
    """Get a tab by its id, or None if not found."""
    return _TABS.get(tab_id)
