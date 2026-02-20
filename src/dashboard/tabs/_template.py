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

from .registry import BaseTab, TabContext, register_tab

# Optional: contribute custom signal stores beyond the standard set.
# from ..components.signals import SignalRegistry
# SignalRegistry.register("my-tab-drilldown")


class TemplateTab(BaseTab):
    """Minimal annotated tab skeleton.

    Class attributes
    ----------------
    id : str
        Unique machine identifier used for routing and DOM IDs.
        Convention: lowercase-hyphenated.
    label : str
        Human-readable label shown in the navigation bar.
    order : int
        Determines tab order in the navigation bar (lower = leftmost).
    required_roles : list[str] | None
        If set, the tab is hidden for users whose role is not in the list.
        Available roles: "Corp SCO", "CRE SCO", "SAG", "BA".
        Leave as None (or empty) to show to all users.
    icon : str
        Optional icon character/emoji rendered before the label.
    """

    id = "template"                # ← CHANGE ME
    label = "Template"             # ← CHANGE ME
    order = 900                    # ← CHANGE ME (controls nav position)
    required_roles = None          # ← set e.g. ["Corp SCO", "BA"] to restrict
    icon = ""                      # ← optional, e.g. "📊 "

    # ------------------------------------------------------------------
    # Layer 2 — Toolbar controls (per-tab dropdowns, sliders, toggles)
    # ------------------------------------------------------------------

    def get_toolbar_controls(self, ctx: TabContext):
        """Return a list of ToolbarControl instances for this tab.

        These appear in the sub-header bar directly below the global nav.

        Examples::

            from ..components.toolbar import DropdownControl, SliderControl
            return [
                DropdownControl(
                    id="template-metric-dropdown",
                    label="Metric",
                    options=[{"label": "Balance", "value": "balance"}],
                    default="balance",
                ),
            ]
        """
        return []  # TODO: add toolbar controls

    # ------------------------------------------------------------------
    # Layer 3 — Cards (charts, tables, metrics)
    # ------------------------------------------------------------------

    def get_cards(self, ctx: TabContext):
        """Return a list of DisplayCard instances for the main content area.

        Cards are automatically laid out in the content grid.

        Examples::

            from ..components.cards import ChartCard, TableCard, MetricCard
            return [
                MetricCard(
                    card_id="template-total-balance",
                    title="Total Balance",
                    value_id="template-total-balance-value",
                ),
                ChartCard(
                    card_id="template-chart",
                    title="Balance Over Time",
                    figure_id="template-chart-fig",
                ),
            ]
        """
        return []  # TODO: add cards

    # ------------------------------------------------------------------
    # Layer 3 — Sidebar (optional)
    # ------------------------------------------------------------------

    def render_sidebar(self, ctx: TabContext):
        """Return a sidebar Dash component, or None to skip the sidebar.

        The sidebar appears to the left of the main content grid when
        ``render_sidebar`` returns a non-None value.
        """
        return None  # TODO: return html.Div([...]) if you need a sidebar

    # ------------------------------------------------------------------
    # Layer 3 — Content (fallback renderer)
    # ------------------------------------------------------------------

    def render_content(self, ctx: TabContext):
        """Return the main content Dash component.

        If you use get_cards(), the framework auto-renders them here.
        Override this method only when you need full control over the layout.
        """
        # TODO: replace with real content
        df = ctx.get_filtered_data(ctx.selected_portfolio)
        return html.Div([
            html.H2(f"{self.label} — {ctx.selected_portfolio}", className="text-xl font-bold"),
            html.P(f"{len(df)} facilities in this portfolio."),
        ])

    # ------------------------------------------------------------------
    # Callbacks (optional)
    # ------------------------------------------------------------------

    def register_callbacks(self, app) -> None:
        """Register any Dash callbacks for this tab.

        Called once at startup by the CallbackRegistry.  Use the Dash
        ``@app.callback`` decorator inside this method.

        Example::

            from dash import Input, Output

            @app.callback(
                Output("template-chart-fig", "figure"),
                Input("template-metric-dropdown", "value"),
            )
            def update_chart(metric):
                ...
        """
        pass  # TODO: add callbacks if needed


# ── Registration ────────────────────────────────────────────────────────────
# Uncomment (and keep) this line after you rename the class:
# register_tab(TemplateTab())
