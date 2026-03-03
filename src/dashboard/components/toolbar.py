"""
ToolbarControl hierarchy — Layer 2 per-tab toolbar controls.

Each tab can declare toolbar controls via ``get_toolbar_controls(ctx)``.
The framework renders them in a full-width row above the sidebar + content
grid.

Built-in presets:

* :class:`DropdownControl` — labeled dropdown
* :class:`SliderControl`   — labeled slider
* :class:`ToggleControl`   — labeled toggle switch

Example::

    class MyTab(BaseTab):
        def get_toolbar_controls(self, ctx):
            return [
                DropdownControl(
                    id="my-view",
                    label="View",
                    options=[{"label": "Industry", "value": "industry"}],
                    order=10,
                ),
                SliderControl(
                    id="my-lookback",
                    label="Lookback (quarters)",
                    min_val=1, max_val=12,
                    order=20,
                ),
            ]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from dash import dcc, html

from ..tabs.registry import TabContext
from .cards import CallbackSpec


class ToolbarAlign(Enum):
    """Horizontal alignment of a control within the toolbar row."""
    LEFT = "left"
    RIGHT = "right"


# =============================================================================
# BASE CLASS
# =============================================================================


class ToolbarControl(ABC):
    """Abstract base for controls in the per-tab toolbar row (Layer 2).

    Attributes
    ----------
    id : str
        Unique component id (used as HTML id for the main control element).
    label : str
        Display label shown above the control.
    order : int
        Sort key — controls are rendered left-to-right by ascending order.
    align : ToolbarAlign
        Whether the control sits on the LEFT or RIGHT side of the toolbar.
    width : str
        CSS class(es) controlling the control's width.
    visible : bool
        Whether the control is initially visible.
    preserve : bool
        If True, the control's value survives global state changes (portfolio,
        time window).  Default False — control resets to its hardcoded default.
    """

    id: str
    label: str = ""
    order: int = 50
    align: ToolbarAlign = ToolbarAlign.RIGHT
    width: str = "min-w-[180px]"
    visible: bool = True
    preserve: bool = False

    @abstractmethod
    def render(self, ctx: TabContext) -> html.Div:
        """Return the Dash component for this toolbar control."""
        ...

    def callback_specs(self) -> list[CallbackSpec]:
        """Declare callbacks.  Override in subclasses."""
        return []


# =============================================================================
# PRESET: DROPDOWN
# =============================================================================


class DropdownControl(ToolbarControl):
    """Dropdown selector for the tab toolbar.

    Parameters
    ----------
    id, label, order : inherited
    options : list of ``{"label": ..., "value": ...}`` dicts
    value : default value(s)
    multi : allow multiple selections
    placeholder : placeholder text
    """

    def __init__(
        self,
        id: str,
        label: str = "",
        options: list[dict] | None = None,
        value: Any = None,
        multi: bool = False,
        placeholder: str = "Select...",
        order: int = 50,
        align: ToolbarAlign = ToolbarAlign.RIGHT,
        width: str = "min-w-[180px]",
        visible: bool = True,
        preserve: bool = False,
    ):
        self.id = id
        self.label = label
        self.options = options or []
        self.value = value
        self.multi = multi
        self.placeholder = placeholder
        self.order = order
        self.align = align
        self.width = width
        self.visible = visible
        self.preserve = preserve

    def render(self, ctx: TabContext) -> html.Div:
        effective_value = self.value
        if self.preserve:
            from ..app_state import app_state
            app_state.register_control(self.id, preserve=True)
            effective_value = app_state.get_control_value(self.id, self.value)
        style = {} if self.visible else {"display": "none"}
        return html.Div([
            html.Span(
                self.label,
                className="control-label",
            ),
            dcc.Dropdown(
                id=self.id,
                options=self.options,
                value=effective_value,
                multi=self.multi,
                placeholder=self.placeholder,
                className="text-xs",
                style={"fontSize": "12px"},
            ),
        ], className=f"{self.width} flex-shrink-0", style=style)


# =============================================================================
# PRESET: SLIDER
# =============================================================================


class SliderControl(ToolbarControl):
    """Range slider for the tab toolbar.

    Parameters
    ----------
    id, label, order : inherited
    min_val, max_val : slider range
    step : step size
    value : default value
    marks : dict of position → label
    """

    def __init__(
        self,
        id: str,
        label: str = "",
        min_val: int = 0,
        max_val: int = 100,
        step: int = 1,
        value: int | None = None,
        marks: dict | None = None,
        order: int = 50,
        align: ToolbarAlign = ToolbarAlign.RIGHT,
        width: str = "min-w-[200px]",
        visible: bool = True,
        preserve: bool = False,
    ):
        self.id = id
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.value = value if value is not None else min_val
        self.marks = marks
        self.order = order
        self.align = align
        self.width = width
        self.visible = visible
        self.preserve = preserve

    def render(self, ctx: TabContext) -> html.Div:
        effective_value = self.value
        if self.preserve:
            from ..app_state import app_state
            app_state.register_control(self.id, preserve=True)
            effective_value = app_state.get_control_value(self.id, self.value)
        style = {} if self.visible else {"display": "none"}
        marks = self.marks or {self.min_val: str(self.min_val), self.max_val: str(self.max_val)}
        return html.Div([
            html.Span(
                self.label,
                className="control-label",
            ),
            dcc.Slider(
                id=self.id,
                min=self.min_val,
                max=self.max_val,
                step=self.step,
                value=effective_value,
                marks=marks,
                tooltip={"placement": "bottom", "always_visible": True},
            ),
        ], className=f"{self.width} flex-shrink-0", style=style)


# =============================================================================
# PRESET: TOGGLE
# =============================================================================


class ToggleControl(ToolbarControl):
    """On/off toggle switch for the tab toolbar.

    Renders as a ``dcc.Checklist`` styled as a toggle switch.
    """

    def __init__(
        self,
        id: str,
        label: str = "",
        default: bool = False,
        order: int = 50,
        align: ToolbarAlign = ToolbarAlign.RIGHT,
        width: str = "min-w-[120px]",
        visible: bool = True,
        preserve: bool = False,
    ):
        self.id = id
        self.label = label
        self.default = default
        self.order = order
        self.align = align
        self.width = width
        self.visible = visible
        self.preserve = preserve

    def render(self, ctx: TabContext) -> html.Div:
        effective_value = ["on"] if self.default else []
        if self.preserve:
            from ..app_state import app_state
            app_state.register_control(self.id, preserve=True)
            effective_value = app_state.get_control_value(self.id, effective_value)
        style = {} if self.visible else {"display": "none"}
        return html.Div([
            html.Span(
                self.label,
                className="control-label",
            ),
            dcc.Checklist(
                id=self.id,
                options=[{"label": "", "value": "on"}],
                value=effective_value,
                className="toggle-switch",
            ),
        ], className=f"{self.width} flex-shrink-0", style=style)


# =============================================================================
# TOOLBAR RENDERER
# =============================================================================


# =============================================================================
# PRESET: RANGE SLIDER
# =============================================================================


class RangeSliderControl(ToolbarControl):
    """Dual-handle range slider for the tab toolbar.

    Parameters
    ----------
    id, label, order : inherited
    min_val, max_val : slider range
    step : step size
    value : default ``[low, high]`` pair
    marks : dict of position → label
    """

    def __init__(
        self,
        id: str,
        label: str = "",
        min_val: int = 0,
        max_val: int = 100,
        step: int = 1,
        value: list | None = None,
        marks: dict | None = None,
        order: int = 50,
        align: ToolbarAlign = ToolbarAlign.RIGHT,
        width: str = "min-w-[240px]",
        visible: bool = True,
        preserve: bool = False,
    ):
        self.id = id
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.value = value if value is not None else [min_val, max_val]
        self.marks = marks
        self.order = order
        self.align = align
        self.width = width
        self.visible = visible
        self.preserve = preserve

    def render(self, ctx: TabContext) -> html.Div:
        effective_value = self.value
        if self.preserve:
            from ..app_state import app_state
            app_state.register_control(self.id, preserve=True)
            effective_value = app_state.get_control_value(self.id, self.value)
        style = {} if self.visible else {"display": "none"}
        marks = self.marks or {self.min_val: str(self.min_val), self.max_val: str(self.max_val)}
        return html.Div([
            html.Span(
                self.label,
                className="control-label",
            ),
            dcc.RangeSlider(
                id=self.id,
                min=self.min_val,
                max=self.max_val,
                step=self.step,
                value=effective_value,
                marks=marks,
                tooltip={"placement": "bottom", "always_visible": True},
            ),
        ], className=f"{self.width} flex-shrink-0", style=style)


# =============================================================================
# PRESET: RAW CONTROL (arbitrary Dash component in the toolbar)
# =============================================================================


class RawControl(ToolbarControl):
    """Wraps an arbitrary Dash component directly in the toolbar row.

    Use when none of the preset controls fit (e.g. a conditional slider
    container whose visibility is toggled by a callback).

    Parameters
    ----------
    id : str
        Logical ID — only used for ordering; the component itself carries its own DOM id.
    component : Dash component
        The pre-built component to render.
    """

    def __init__(
        self,
        id: str,
        component,
        order: int = 50,
        align: ToolbarAlign = ToolbarAlign.RIGHT,
    ):
        self.id = id
        self.label = ""
        self.component = component
        self.order = order
        self.align = align
        self.width = ""
        self.visible = True

    def render(self, ctx: TabContext) -> html.Div:
        return self.component


# =============================================================================
# TOOLBAR RENDERER
# =============================================================================


def render_toolbar(controls: list[ToolbarControl], ctx: TabContext, badge=None) -> html.Div:
    """Render all toolbar controls into a single row.

    Controls are split into left-aligned and right-aligned groups (each
    sorted by ``order``).  The two groups sit at opposite ends of the
    toolbar with ``justify-between``.

    Always renders a toolbar row (even if empty) so the tier badge is visible.

    Parameters
    ----------
    badge : Dash component, optional
        A badge component (e.g. tier badge) rendered first in the left group.
    """
    from ..utils.helpers import toolbar_row

    left = sorted(
        [c for c in controls if c.align == ToolbarAlign.LEFT],
        key=lambda c: c.order,
    )
    right = sorted(
        [c for c in controls if c.align == ToolbarAlign.RIGHT],
        key=lambda c: c.order,
    )

    left_children = []
    if badge is not None:
        left_children.append(badge)
    left_children.extend(c.render(ctx) for c in left)

    left_group = html.Div(
        left_children,
        className="flex flex-wrap items-end gap-4",
    ) if left_children else None

    right_group = html.Div(
        [c.render(ctx) for c in right],
        className="flex flex-wrap items-end gap-4",
    ) if right else None

    children = [g for g in [left_group, right_group] if g is not None]
    return toolbar_row(children)
