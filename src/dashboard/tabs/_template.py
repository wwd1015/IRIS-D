"""
_template.py — Annotated template for adding a new IRIS-D tab.

USAGE
-----
1. Copy this file to a new name, e.g. ``my_analysis.py``.
2. Rename ``TemplateTab`` → ``MyAnalysisTab`` and update ``id``, ``label``, ``order``.
3. Implement the methods marked with ``# TODO``.
4. The tab will appear automatically in navigation — no other files to edit.

DO NOT import or register _template.py itself; the leading underscore prevents
auto-discovery.
"""

from __future__ import annotations

from dash import html

from .registry import BaseTab, ContentLayout, TabContext, register_tab


class TemplateTab(BaseTab):
    """Minimal annotated tab skeleton.

    Class attributes
    ----------------
    id : str
        Unique machine identifier used for routing and DOM IDs.
    label : str
        Human-readable label shown in the navigation bar.
    order : int
        Determines tab order in the navigation bar (lower = leftmost).
    required_roles : list[str] | None
        If set, the tab is hidden for users whose role is not in the list.
    tier : str
        Badge tier: ``"gold"``, ``"silver"``, or ``"bronze"``.
    tier_tooltip : str
        Hover text for the tier badge.
    content_layout : ContentLayout
        Grid layout preset for the content area.
    """

    id = "template"                       # ← CHANGE ME
    label = "Template"                    # ← CHANGE ME
    order = 900                           # ← CHANGE ME
    required_roles = None                 # ← e.g. ["Corp SCO", "BA"]
    tier = "bronze"                       # ← "gold", "silver", or "bronze"
    tier_tooltip = ""                     # ← hover text
    content_layout = ContentLayout.FULL   # ← FULL, TWO_COL, THREE_COL, etc.

    # ------------------------------------------------------------------
    # Layer 2 — Toolbar controls
    # ------------------------------------------------------------------

    def get_toolbar_controls(self, ctx: TabContext):
        """Return a list of ToolbarControl instances for this tab."""
        return []  # TODO: add toolbar controls

    # ------------------------------------------------------------------
    # Layer 3 — Cards
    # ------------------------------------------------------------------

    def get_cards(self, ctx: TabContext):
        """Return a list of DisplayCard instances for the main content area."""
        return []  # TODO: add cards

    # ------------------------------------------------------------------
    # Layer 3 — Sidebar (optional)
    # ------------------------------------------------------------------

    def render_sidebar(self, ctx: TabContext):
        """Return a sidebar Dash component, or None to skip the sidebar."""
        return None  # TODO: return html.Div([...]) if you need a sidebar

    # ------------------------------------------------------------------
    # Callbacks (optional)
    # ------------------------------------------------------------------

    def register_callbacks(self, app) -> None:
        """Register any Dash callbacks for this tab."""
        pass  # TODO: add callbacks if needed

    # ------------------------------------------------------------------
    # Click-to-Detail (optional)
    # ------------------------------------------------------------------
    # To add drill-down on a chart, use the click_detail mixin:
    #
    #   from ..components.mixins.click_detail import (
    #       chart_with_detail_layout, register_detail_callback,
    #   )
    #
    # In render_content or get_cards:
    #   chart_with_detail_layout("my-chart", figure=fig, height=400)
    #
    # In register_callbacks:
    #   def _detail_fn(click_point, curve_name, x_value, portfolio):
    #       ...filter data for clicked element...
    #       return pl.DataFrame(...)  # or None to hide
    #
    #   register_detail_callback(
    #       app, "my-chart", detail_fn=_detail_fn,
    #       extra_states=[State("universal-portfolio-dropdown", "value")],
    #   )
    #
    # Important: set customdata on traces for reliable curve name extraction:
    #   fig.add_trace(go.Bar(..., customdata=[["name"] for _ in x_vals]))


# ── Registration ────────────────────────────────────────────────────────────
# Uncomment (and keep) this line after you rename the class:
# register_tab(TemplateTab())
