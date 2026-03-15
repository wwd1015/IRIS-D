"""
DisplayCard hierarchy — Layer 3 content components.

Provides a standardised, class-based way to build dashboard cards (charts,
tables, metrics, filters).  Each card owns its *render*, *callback specs*,
and *sizing* so tabs can be composed declaratively via ``get_cards()``.

Quick-start::

    class RevenueChart(ChartCard):
        card_id = "revenue-chart"
        title   = "Revenue by Quarter"
        size    = CardSize.HALF

        def build_figure(self, ctx):
            fig = go.Figure(...)
            return fig

    # In a tab:
    def get_cards(self, ctx):
        return [RevenueChart(), EbitdaTable()]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    import pandas as pd
import plotly.graph_objects as go
from dash import dash_table, dcc, html

from ..tabs.registry import TabContext
from ..utils.helpers import card_header, card_wrapper, empty_figure, plotly_theme


# =============================================================================
# CALLBACK SPEC — shared across all layers
# =============================================================================


@dataclass
class CallbackSpec:
    """Declarative specification for a single Dash callback.

    Used by ``GlobalControl``, ``ToolbarControl``, and ``DisplayCard`` so that
    the ``CallbackRegistry`` can auto-wire everything at startup.

    Parameters
    ----------
    outputs : list of (component_id, property) tuples
    inputs  : list of (component_id, property) tuples — these *trigger* the cb
    states  : list of (component_id, property) tuples — read but don't trigger
    handler : server-side Python callable, mutually exclusive with *client_side*
    client_side : JavaScript string for ``app.clientside_callback``
    prevent_initial_call : passed through to Dash
    """

    outputs: list[tuple[str, str]]
    inputs: list[tuple[str, str]]
    states: list[tuple[str, str]] = field(default_factory=list)
    handler: Optional[Callable] = None
    client_side: Optional[str] = None
    prevent_initial_call: bool = False

    def __post_init__(self):
        if self.handler and self.client_side:
            raise ValueError("Specify handler OR client_side, not both.")


# =============================================================================
# CARD SIZE
# =============================================================================


class CardSize(Enum):
    """Pre-defined grid column spans for cards inside a content grid.

    The content area uses a 2-column CSS grid by default.  Sizes map to
    Tailwind ``col-span-*`` classes.
    """

    FULL = "col-span-full"
    HALF = "col-span-1"
    THIRD = "lg:col-span-1"          # in a 3-col grid override
    QUARTER = "lg:col-span-1"        # in a 4-col grid override
    CUSTOM = ""                       # developer supplies their own class


# =============================================================================
# DISPLAY CARD — abstract base
# =============================================================================


class DisplayCard(ABC):
    """Abstract base for all Layer 3 dashboard cards.

    Subclass this and implement :meth:`render_body`.  The framework calls
    :meth:`render` which wraps the body in the standard card shell.
    """

    card_id: str = ""
    title: str = ""
    subtitle: str = ""
    size: CardSize = CardSize.FULL
    order: int = 0
    css_class: str = ""

    # ── Rendering ──────────────────────────────────────────────────────────

    @abstractmethod
    def render_body(self, ctx: TabContext) -> Any:
        """Return the inner content of this card (no wrapper)."""
        ...

    def get_controls(self, ctx: TabContext) -> list:
        """Return card-level controls rendered above the body.

        Each item should be a ``(label, widget)`` tuple or a Dash component.
        Override in subclasses to add per-card controls.
        """
        return []

    def render(self, ctx: TabContext) -> html.Div:
        """Return the fully wrapped card component."""
        header = card_header(self.title, self.subtitle) if self.title else None
        controls = self.get_controls(ctx)
        controls_row = None
        if controls:
            items = []
            for ctrl in controls:
                if isinstance(ctrl, tuple) and len(ctrl) == 2:
                    label, widget = ctrl
                    items.append(html.Div([
                        html.Span(label, className="control-label"),
                        widget,
                    ], className="flex flex-col gap-1"))
                else:
                    items.append(ctrl)
            controls_row = html.Div(items, className="flex flex-wrap items-end gap-4 p-4 pb-0")
        body = self.render_body(ctx)
        children = [x for x in [header, controls_row, body] if x is not None]
        return card_wrapper(
            children=children,
            card_id=self.card_id,
            css_class=f"{self.size.value} {self.css_class}".strip(),
        )

    # ── Callbacks ──────────────────────────────────────────────────────────

    def callback_specs(self) -> list[CallbackSpec]:
        """Declare callbacks for this card.  Override in subclasses."""
        return []


# =============================================================================
# CHART CARD
# =============================================================================


class ChartCard(DisplayCard):
    """Card that displays a Plotly chart.

    Subclass and implement :meth:`build_figure`.  The framework applies the
    standard IRIS-D Plotly theme automatically.
    """

    height: int = 300
    show_modebar: bool = False
    chart_config: dict = {}

    @abstractmethod
    def build_figure(self, ctx: TabContext) -> go.Figure:
        """Build and return a Plotly figure.  Theme is applied automatically."""
        ...

    def render_body(self, ctx: TabContext) -> dcc.Graph:
        try:
            fig = self.build_figure(ctx)
            fig.update_layout(**plotly_theme(height=self.height))
        except Exception:
            fig = empty_figure("Error building chart", height=self.height)
        config = {"displayModeBar": self.show_modebar, **self.chart_config}
        return dcc.Graph(
            id=f"{self.card_id}-graph",
            figure=fig,
            config=config,
            style={"height": f"{self.height}px"},
        )


# =============================================================================
# TABLE CARD
# =============================================================================


class TableCard(DisplayCard):
    """Card that displays a Dash ``DataTable``.

    Subclass and implement :meth:`get_data` and set :attr:`columns`.
    """

    columns: list[dict] = []
    max_rows: int = 20
    sortable: bool = True
    filterable: bool = False

    @abstractmethod
    def get_data(self, ctx: TabContext) -> pl.DataFrame | pd.DataFrame:
        """Return the DataFrame to display."""
        ...

    def render_body(self, ctx: TabContext) -> dash_table.DataTable:
        df = self.get_data(ctx)
        if isinstance(df, pl.DataFrame):
            records = df.head(self.max_rows).to_dicts()
            cols = self.columns or [{"name": c, "id": c} for c in df.columns]
        else:
            records = df.head(self.max_rows).to_dict("records")
            cols = self.columns or [{"name": c, "id": c} for c in df.columns]
        return dash_table.DataTable(
            id=f"{self.card_id}-table",
            columns=cols,
            data=records,
            sort_action="native" if self.sortable else "none",
            filter_action="native" if self.filterable else "none",
            page_size=self.max_rows,
            style_table={"overflowX": "auto"},
            style_header={
                "fontWeight": 600,
                "textAlign": "left",
                "padding": "10px 12px",
            },
            style_cell={
                "padding": "10px 12px",
                "whiteSpace": "nowrap",
                "fontFamily": "Plus Jakarta Sans, system-ui, sans-serif",
                "fontSize": 13,
            },
        )


# =============================================================================
# METRIC CARD
# =============================================================================


@dataclass
class MetricItem:
    """A single KPI metric displayed in a :class:`MetricCard`."""

    label: str
    value: str
    icon: str = ""
    change: str = ""
    change_positive: Optional[bool] = None


class MetricCard(DisplayCard):
    """Card that displays a grid of KPI / summary metrics.

    Set :attr:`metrics` to a list of :class:`MetricItem` instances or override
    :meth:`get_metrics` for dynamic values.
    """

    metrics: list[MetricItem] = []
    columns_count: int = 4  # number of metric columns in the grid

    def get_metrics(self, ctx: TabContext) -> list[MetricItem]:
        """Override to compute metrics dynamically.  Defaults to static list."""
        return self.metrics

    def render_body(self, ctx: TabContext) -> html.Div:
        items = self.get_metrics(ctx)
        grid_cols = f"grid-cols-{min(self.columns_count, len(items))}"
        return html.Div(
            [self._render_item(m) for m in items],
            className=f"grid {grid_cols} gap-4 p-4",
        )

    @staticmethod
    def _render_item(m: MetricItem) -> html.Div:
        change_cls = (
            "text-green-400" if m.change_positive
            else "text-red-400" if m.change_positive is False
            else "text-slate-400"
        )
        return html.Div([
            *(
                [html.Span(m.icon, className="text-2xl mb-1")]
                if m.icon else []
            ),
            html.Div(m.value, className="text-xl font-bold text-slate-900 dark:text-white"),
            html.Div(m.label, className="text-xs text-slate-500 dark:text-slate-400 mt-0.5"),
            *(
                [html.Div(m.change, className=f"text-xs mt-1 {change_cls}")]
                if m.change else []
            ),
        ], className="flex flex-col items-center p-3 rounded-lg bg-slate-100 dark:bg-ink-700/50")


# =============================================================================
# FILTER CARD (used as sidebar content)
# =============================================================================


@dataclass
class FilterDef:
    """Definition for a single filter control inside a :class:`FilterCard`."""

    id: str
    label: str
    options: list[dict] = field(default_factory=list)
    value: Any = None
    multi: bool = False
    placeholder: str = "Select..."


class FilterCard(DisplayCard):
    """Card that renders a set of dropdown filters.

    Typically used as the sidebar content.  Can also be placed inline.
    """

    filters: list[FilterDef] = []

    def render_body(self, ctx: TabContext) -> html.Div:
        from ..utils.helpers import dropdown_filter

        children = []
        for f in self.filters:
            children.append(dropdown_filter(
                id=f.id,
                label=f.label,
                options=f.options,
                value=f.value,
                multi=f.multi,
                placeholder=f.placeholder,
                width="w-full",
            ))
        return html.Div(children, className="space-y-4 p-4")


# =============================================================================
# CARD GRID RENDERER
# =============================================================================


def render_card_grid(cards: list[DisplayCard], ctx: TabContext) -> html.Div:
    """Render a list of cards into a responsive CSS grid.

    Cards are sorted by :attr:`order` and laid out using their
    :attr:`size` grid spans.
    """
    sorted_cards = sorted(cards, key=lambda c: c.order)
    return html.Div(
        [card.render(ctx) for card in sorted_cards],
        className="grid grid-cols-1 xl:grid-cols-2 gap-4",
    )
