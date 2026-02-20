"""
Tab registry – the core of the extensible tab system.

Each tab is a subclass of BaseTab that declares:
  - id, label, order, required_role
  - get_toolbar_controls(ctx) → list[ToolbarControl]  (Layer 2)
  - get_cards(ctx)            → list[DisplayCard]      (Layer 3)
  - render_sidebar(ctx)       → Dash component or None (Layer 3)
  - render_content(ctx)       → Dash component         (fallback)
  - register_callbacks(app)   → called once at startup

The framework iterates over registered tabs to build navigation buttons,
route tab clicks, and wire up callbacks — no manual wiring needed.
"""

from __future__ import annotations
from abc import ABC
from typing import Optional

from dash import html

# ── Global registry ────────────────────────────────────────────────────────────
_TABS: dict[str, "BaseTab"] = {}


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
    3. **Custom**: override ``render()`` for totally custom layout.

    Attributes:
        id:            Unique slug used in HTML ids  (e.g. "portfolio-summary")
        label:         Display text in the navigation bar
        order:         Sort key — lower numbers appear first
        required_role: If set, only users with this role see the tab.
                       None means visible to everyone.
        grid_class:    CSS grid class for the sidebar + content layout.
    """

    id: str
    label: str
    order: int = 100
    required_role: Optional[str] = None
    grid_class: str = "grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-4 items-stretch"

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

        1. Layer 2 toolbar (full-width row, if any controls)
        2. Layer 3 sidebar + content grid

        Override this if you need a completely custom layout
        (e.g. 3-column grid like PortfolioSummaryTab).
        """
        # Layer 2: toolbar
        toolbar_controls = self.get_toolbar_controls(ctx)
        toolbar = None
        if toolbar_controls:
            from ..components.toolbar import render_toolbar
            toolbar = render_toolbar(toolbar_controls, ctx)

        # Layer 3: sidebar + content
        sidebar = self.render_sidebar(ctx)
        content = self.render_content(ctx)
        if sidebar is not None:
            grid = html.Div([sidebar, content], className=self.grid_class)
        else:
            grid = content

        # Combine
        parts = [p for p in [toolbar, grid] if p is not None]
        return html.Div(parts) if len(parts) > 1 else parts[0]

    # ── Callbacks ──────────────────────────────────────────────────────────

    def register_callbacks(self, app) -> None:
        """
        Register any Dash callbacks specific to this tab.

        Called once during app startup. Override to add interactivity.
        """
        pass


# ── Registry helpers ───────────────────────────────────────────────────────────

def register_tab(tab: BaseTab) -> None:
    """Register a tab instance. Call at module level in each tab file."""
    _TABS[tab.id] = tab


def get_all_tabs() -> list[BaseTab]:
    """Return all registered tabs, sorted by order then label."""
    return sorted(_TABS.values(), key=lambda t: (t.order, t.label))


def get_tab(tab_id: str) -> Optional[BaseTab]:
    """Get a tab by its id, or None if not found."""
    return _TABS.get(tab_id)
