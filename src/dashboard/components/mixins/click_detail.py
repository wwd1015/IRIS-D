"""
Click-to-Detail: reusable chart drill-down component.

Usage:
    from dashboard.components.mixins.click_detail import (
        chart_with_detail_layout, register_detail_callback,
    )

    # In render_content:
    chart_with_detail_layout("my-chart", figure=fig)

    # In register_callbacks:
    register_detail_callback(app, "my-chart", detail_fn=my_detail_fn)

    # detail_fn signature:
    def my_detail_fn(click_point: dict, curve_name: str, x_value: str) -> pl.DataFrame | None
"""

from __future__ import annotations

from typing import Callable

import polars as pl
from dash import callback_context, dash_table, dcc, html, Input, Output, State, no_update


def chart_with_detail_layout(
    graph_id: str,
    figure=None,
    height: int = 400,
    detail_max_rows: int = 200,
) -> html.Div:
    """Return a Graph + collapsible detail table panel below it."""
    graph_kwargs = {"id": graph_id, "config": {"displayModeBar": False},
                    "style": {"height": f"{height}px"}}
    if figure is not None:
        graph_kwargs["figure"] = figure

    return html.Div([
        dcc.Store(id=f"{graph_id}-last-click", data=None),
        dcc.Graph(**graph_kwargs),
        html.Div(
            id=f"{graph_id}-detail-panel",
            className="detail-panel",
            style={"display": "none"},
            children=[
                html.Div([
                    html.Span(id=f"{graph_id}-detail-title", className="detail-panel__title"),
                    html.Div([
                        html.Button(
                            "CSV", id=f"{graph_id}-detail-download-btn",
                            className="detail-panel__download", n_clicks=0,
                            title="Download as CSV",
                        ),
                        html.Button("✕", id=f"{graph_id}-detail-close",
                                    className="detail-panel__close", n_clicks=0),
                    ], className="flex items-center gap-2"),
                ], className="detail-panel__header"),
                dash_table.DataTable(
                    id=f"{graph_id}-detail-table",
                    page_size=detail_max_rows,
                    style_table={"overflowX": "auto", "maxHeight": "300px", "overflowY": "auto"},
                    style_header={
                        "backgroundColor": "var(--bg-raised)",
                        "color": "var(--text-primary)",
                        "fontWeight": "600",
                        "fontSize": "12px",
                        "borderBottom": "1px solid var(--border-default)",
                    },
                    style_cell={
                        "backgroundColor": "transparent",
                        "color": "var(--text-secondary)",
                        "fontSize": "12px",
                        "padding": "6px 10px",
                        "border": "none",
                        "borderBottom": "1px solid var(--border-subtle)",
                        "textAlign": "left",
                    },
                    style_data_conditional=[{
                        "if": {"row_index": "odd"},
                        "backgroundColor": "var(--glass-hover)",
                    }],
                ),
                dcc.Download(id=f"{graph_id}-detail-download"),
            ],
        ),
    ], className="detail-chart-wrapper")


def register_detail_callback(
    app,
    graph_id: str,
    detail_fn: Callable,
    title_fn: Callable[[dict, str, str], str] | None = None,
    extra_states: list | None = None,
    reset_inputs: list | None = None,
):
    """Wire clickData on graph_id to the detail panel.

    Parameters
    ----------
    detail_fn : callable
        ``detail_fn(click_point, curve_name, x_value, *extra_state_values)``
        → ``pl.DataFrame | None``.
    title_fn : callable, optional
        ``title_fn(click_point, curve_name, x_value)`` → ``str``.
    extra_states : list[State], optional
        Additional ``State(...)`` objects whose values are forwarded to
        *detail_fn* as positional args after the first three.
    reset_inputs : list[Input], optional
        Additional ``Input(...)`` triggers that reset (hide) the detail panel.
        Use this for toolbar controls or in-chart dropdowns that rebuild the
        chart, so the stale detail table is dismissed automatically.
    """
    import plotly.graph_objs as go

    states = [State(f"{graph_id}-last-click", "data")]
    if extra_states:
        states.extend(extra_states)
    states.append(State(graph_id, "figure"))

    inputs = [
        Input(graph_id, "clickData"),
        Input(f"{graph_id}-detail-close", "n_clicks"),
    ]
    if reset_inputs:
        inputs.extend(reset_inputs)

    @app.callback(
        [Output(f"{graph_id}-detail-panel", "style"),
         Output(f"{graph_id}-detail-table", "data"),
         Output(f"{graph_id}-detail-table", "columns"),
         Output(f"{graph_id}-detail-title", "children"),
         Output(f"{graph_id}-last-click", "data"),
         Output(graph_id, "figure", allow_duplicate=True)],
        inputs,
        states,
        prevent_initial_call=True,
    )
    def _handle_click(click_data, close_clicks, *rest):
        # rest = (*reset_input_vals, last_click, *extra_vals, figure)
        n_reset = len(reset_inputs) if reset_inputs else 0
        # Skip reset input values
        state_vals = rest[n_reset:]
        last_click = state_vals[0]
        current_fig = state_vals[-1]
        extra_vals = state_vals[1:-1]

        triggered = callback_context.triggered_id
        hide = {"display": "none"}

        def _reset_opacity(fig_dict):
            """Restore full opacity on all traces."""
            if not fig_dict or "data" not in fig_dict:
                return no_update
            fig = go.Figure(fig_dict)
            for trace in fig.data:
                trace.marker.opacity = 1.0
            return fig

        def _dim_others(fig_dict, clicked_x, clicked_curve):
            """Dim all bars except the clicked one."""
            if not fig_dict or "data" not in fig_dict:
                return no_update
            fig = go.Figure(fig_dict)
            for trace in fig.data:
                x_vals = list(trace.x) if trace.x is not None else []
                opacities = []
                is_clicked_trace = (trace.name == clicked_curve)
                for x in x_vals:
                    if str(x) == clicked_x and is_clicked_trace:
                        opacities.append(1.0)
                    else:
                        opacities.append(0.25)
                trace.marker.opacity = opacities
            return fig

        # Close button or reset input — hide panel, restore opacity
        if triggered != graph_id:
            return hide, no_update, no_update, no_update, None, _reset_opacity(current_fig)

        if not click_data or not click_data.get("points"):
            return hide, no_update, no_update, no_update, None, _reset_opacity(current_fig)

        point = click_data["points"][0]
        curve_name = ""
        if point.get("customdata"):
            cd = point["customdata"]
            curve_name = str(cd[0]) if isinstance(cd, (list, tuple)) else str(cd)
        if not curve_name:
            curve_name = str(point.get("curveNumber", ""))
        x_value = str(point.get("x", ""))

        # Toggle: same point clicked again → hide + reset opacity
        click_key = f"{x_value}|{curve_name}"
        if last_click == click_key:
            return hide, no_update, no_update, no_update, None, _reset_opacity(current_fig)

        # Call the user-provided detail function
        df = detail_fn(point, curve_name, x_value, *extra_vals)
        if df is None or df.is_empty():
            return hide, no_update, no_update, no_update, None, _reset_opacity(current_fig)

        # Build title
        if title_fn:
            title = title_fn(point, curve_name, x_value)
        else:
            title = f"Details for {x_value}"
            if curve_name and curve_name != x_value:
                title += f" — {curve_name}"

        columns = [{"name": c.replace("_", " ").title(), "id": c} for c in df.columns]
        data = df.to_dicts()
        updated_fig = _dim_others(current_fig, x_value, curve_name)

        return (
            {"display": "block", "animation": "detail-slide-in 0.2s ease-out"},
            data, columns, title, click_key, updated_fig,
        )

    # CSV download callback — only fire on genuine button clicks
    @app.callback(
        Output(f"{graph_id}-detail-download", "data"),
        Input(f"{graph_id}-detail-download-btn", "n_clicks"),
        [State(f"{graph_id}-detail-table", "data"),
         State(f"{graph_id}-detail-title", "children")],
        prevent_initial_call=True,
    )
    def _download_csv(n_clicks, table_data, title):
        # Guard: only proceed if this was truly triggered by the button
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]["value"] in (None, 0):
            return no_update
        if not table_data:
            return no_update
        import pandas as pd
        pdf = pd.DataFrame(table_data)
        filename = (title or "detail").replace(" ", "_").replace("—", "-")
        filename = "".join(c for c in filename if c.isalnum() or c in "_-")
        return dcc.send_data_frame(pdf.to_csv, f"{filename}.csv", index=False)
