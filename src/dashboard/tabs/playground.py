"""
Playground tab — drill-down portfolio explorer.

Layout: FULL (dynamic grid managed internally).
Up to 3 cards in a horizontal chain. Clicking a chart segment in card N
creates an ephemeral filter that feeds into card N+1.

Add Column / Close / grid layout handled by assets/playground.js (pure JS).
Chart updates use @app.callback (not @callback which doesn't bind to the app).
"""

from __future__ import annotations

import plotly.graph_objs as go
import polars as pl
from dash import callback_context, dash_table, dcc, html, Input, Output, State, no_update

from .registry import BaseTab, ContentLayout, TabContext, register_tab
from ..utils.helpers import (
    plotly_theme, empty_figure, add_period_column, format_period,
)

_MAX_CARDS = 3

_COLORS = [
    "#c96442", "#4d8b6f", "#d97757", "#87867f", "#6da58b",
    "#b85538", "#3d7a5f", "#a0472e", "#5e5d59", "#2d6a4f",
    "#c9856a", "#b5725a", "#4d4c48", "#a06050", "#3d3d3a",
]


class PlaygroundTab(BaseTab):
    id = "playground"
    label = "Playground"
    order = 60
    tier = "gold"
    content_layout = ContentLayout.FULL
    nav_align = "right"

    def get_toolbar_controls(self, ctx: TabContext):
        from ..components.toolbar import RawControl, ToolbarAlign
        return [
            RawControl(
                "pg-add-col-ctrl",
                html.Button(
                    "+ Drill Down", id="pg-add-col",
                    className="btn btn-sm btn-outline pg-add-col-btn",
                    n_clicks=0,
                ),
                align=ToolbarAlign.RIGHT,
                order=1,
            ),
            RawControl(
                "pg-save-port-ctrl",
                html.Button(
                    "Save to Portfolio", id="pg-save-portfolio",
                    className="btn btn-sm btn-outline pg-save-btn pg-save-btn--disabled",
                    n_clicks=0,
                ),
                align=ToolbarAlign.RIGHT,
                order=2,
            ),
        ]

    def render_content(self, ctx: TabContext):
        from ..app_state import app_state

        metric_opts = _get_metric_options(ctx.facilities_df)
        seg_opts = _get_segmentation_options(ctx.facilities_df)
        default_metric = "balance" if any(o["value"] == "balance" for o in metric_opts) else (metric_opts[0]["value"] if metric_opts else "balance")

        fig0 = _build_chart(
            ctx.facilities_df, ctx.portfolios, ctx.selected_portfolio,
            default_metric, "monthly", None, "sum", "bar", [],
        )

        cards = []
        for i in range(_MAX_CARDS):
            visible = i == 0
            card = html.Div([
                # Filter badge (cards 1-2 only)
                html.Div(
                    id=f"pg-card-{i}-badge",
                    className="text-xs text-ink-500 mb-1",
                    style={"display": "none"} if i == 0 else {},
                ),
                # Hidden stores
                dcc.Store(id=f"pg-card-{i}-plot", data="bar"),
                dcc.Store(id=f"pg-card-{i}-trace-vis", data=None),
                # Inline controls row
                html.Div([
                    # Bar/Line toggle icon
                    html.Button(
                        html.Span("III", className="pg-icon-inner"),
                        id=f"pg-card-{i}-plot-toggle",
                        className="btn btn-sm btn-outline pg-icon-btn",
                        title="Switch to line chart",
                    ),
                    # Settings popover trigger
                    html.Div([
                        html.Button(
                            html.Span("⚙", className="pg-icon-inner"),
                            id=f"pg-card-{i}-settings-btn",
                            className="btn btn-sm btn-outline pg-icon-btn",
                            title="Chart settings",
                        ),
                        html.Div([
                            html.Label("Metric", className="text-xs text-ink-500", style={"marginBottom": "2px"}),
                            dcc.Dropdown(
                                id=f"pg-card-{i}-metric",
                                options=metric_opts,
                                value=default_metric, clearable=False,
                                style={"width": "100%", "fontSize": "12px", "marginBottom": "8px"},
                            ),
                            html.Label("Segment", className="text-xs text-ink-500", style={"marginBottom": "2px"}),
                            dcc.Dropdown(
                                id=f"pg-card-{i}-seg",
                                options=seg_opts,
                                value=None, clearable=True, placeholder="None",
                                style={"width": "100%", "fontSize": "12px", "marginBottom": "8px"},
                            ),
                            html.Label("Aggregation", className="text-xs text-ink-500", style={"marginBottom": "2px"}),
                            dcc.Dropdown(
                                id=f"pg-card-{i}-agg",
                                options=[
                                    {"label": "Sum", "value": "sum"},
                                    {"label": "Avg", "value": "avg"},
                                ],
                                value="sum", clearable=False,
                                style={"width": "100%", "fontSize": "12px"},
                            ),
                        ], id=f"pg-card-{i}-settings-panel",
                           className="pg-settings-panel",
                           style={"display": "none"}),
                    ], style={"position": "relative"}),
                    html.Button(
                        html.Span("✕", className="pg-icon-inner"),
                        id=f"pg-card-{i}-close",
                        className="btn btn-sm btn-outline pg-icon-btn pg-close-btn ml-auto",
                        style={"display": "none"} if i == 0 else {},
                    ),
                ], className="flex items-center gap-2 mb-2"),
                # Chart + detail panel
                dcc.Store(id=f"pg-card-{i}-last-click", data=None),
                dcc.Graph(
                    id=f"pg-card-{i}-chart",
                    figure=fig0 if i == 0 else empty_figure("", 380),
                    config={"displayModeBar": False},
                    style={"height": "380px"},
                ),
                html.Div(
                    id=f"pg-card-{i}-detail-panel",
                    className="detail-panel",
                    style={"display": "none"},
                    children=[
                        html.Div([
                            html.Span(id=f"pg-card-{i}-detail-title",
                                      className="detail-panel__title"),
                            html.Button("✕", id=f"pg-card-{i}-detail-close",
                                        className="detail-panel__close", n_clicks=0),
                        ], className="detail-panel__header"),
                        dash_table.DataTable(
                            id=f"pg-card-{i}-detail-table",
                            page_size=200,
                            style_table={"overflowX": "auto", "maxHeight": "300px",
                                         "overflowY": "auto"},
                            style_header={
                                "backgroundColor": "var(--bg-raised)",
                                "color": "var(--text-primary)",
                                "fontWeight": "600", "fontSize": "12px",
                                "borderBottom": "1px solid var(--border-default)",
                            },
                            style_cell={
                                "backgroundColor": "transparent",
                                "color": "var(--text-secondary)",
                                "fontSize": "12px", "padding": "6px 10px",
                                "border": "none",
                                "borderBottom": "1px solid var(--border-subtle)",
                                "textAlign": "left",
                            },
                            style_data_conditional=[{
                                "if": {"row_index": "odd"},
                                "backgroundColor": "var(--glass-hover)",
                            }],
                        ),
                    ],
                ),
            ], id=f"pg-card-{i}-wrapper",
               className="glass-card p-4",
               style={} if visible else {"display": "none"})
            cards.append(card)

        # Per-card drill filter stores: card i's store holds the filter
        # that card i-1's legend selection produced (i.e., what filters card i).
        drill_stores = [dcc.Store(id=f"pg-drill-{i}", data=None) for i in range(_MAX_CARDS)]
        reset_signal = dcc.Store(id="pg-reset-signal", data=0)

        return html.Div([html.Div([
            *drill_stores, reset_signal,
            html.Div(cards, id="pg-cards-grid",
                     className="pg-cards-grid"),
        ])])

    def register_callbacks(self, app):
        from ..app_state import app_state
        from ..utils.helpers import MODAL_SHOWN, MODAL_HIDDEN

        for i in range(_MAX_CARDS):
            _register_chart_update(app, i, app_state)
            _register_badge_callback(app, i)
            _register_plot_toggle(app, i)
            _register_settings_toggle(app, i)
            _register_detail_callback(app, i, app_state)

        for i in range(_MAX_CARDS - 1):
            _register_click_callback(app, i, app_state)

        _register_save_to_portfolio(app, app_state)
        _register_global_reset(app)


def _register_global_reset(app):
    """Reset all playground state when global controls change."""
    outputs = []
    # For every card: reset controls + stores
    for i in range(_MAX_CARDS):
        outputs.append(Output(f"pg-card-{i}-seg", "value", allow_duplicate=True))
        outputs.append(Output(f"pg-card-{i}-agg", "value", allow_duplicate=True))
        outputs.append(Output(f"pg-card-{i}-plot", "data", allow_duplicate=True))
        outputs.append(Output(f"pg-card-{i}-trace-vis", "data", allow_duplicate=True))
        outputs.append(Output(f"pg-card-{i}-last-click", "data", allow_duplicate=True))
        outputs.append(Output(f"pg-card-{i}-detail-panel", "style", allow_duplicate=True))
    # Drill stores for cards 1+
    for i in range(1, _MAX_CARDS):
        outputs.append(Output(f"pg-drill-{i}", "data", allow_duplicate=True))
    # Reset signal — triggers JS to hide cards 1+ and update grid
    outputs.append(Output("pg-reset-signal", "data", allow_duplicate=True))

    @app.callback(
        outputs,
        [Input("universal-portfolio-dropdown", "value"),
         Input("time-window-store", "data"),
         Input("custom-metric-store", "data")],
        [State("pg-reset-signal", "data")],
        prevent_initial_call=True,
    )
    def reset_on_global(*args):
        prev_signal = args[-1] or 0
        result = []
        # Reset controls for all cards
        for _ in range(_MAX_CARDS):
            result.append(None)                # seg = None
            result.append("sum")               # agg = sum
            result.append("bar")               # plot type = bar
            result.append(None)                # trace-vis = None
            result.append(None)                # last-click = None
            result.append({"display": "none"}) # hide detail panel
        # Clear drill stores for cards 1+
        for _ in range(1, _MAX_CARDS):
            result.append(None)
        # Bump reset signal so JS hides cards
        result.append(prev_signal + 1)
        return result

    # Clientside callback: when reset signal changes, hide cards 1+ via DOM and update grid
    app.clientside_callback(
        """
        function(signal) {
            for (var i = 1; i < """ + str(_MAX_CARDS) + """; i++) {
                var card = document.getElementById("pg-card-" + i + "-wrapper");
                if (card) card.style.display = "none";
            }
            if (window.pgUpdateGrid) window.pgUpdateGrid();
            return "pg-cards-grid";
        }
        """,
        Output("pg-cards-grid", "className"),
        Input("pg-reset-signal", "data"),
        prevent_initial_call=True,
    )


def _register_chart_update(app, i: int, app_state):
    inputs = [
        Input(f"pg-card-{i}-plot", "data"),
        Input(f"pg-card-{i}-metric", "value"),
        Input(f"pg-card-{i}-seg", "value"),
        Input(f"pg-card-{i}-agg", "value"),
    ]
    # Card i listens only to pg-drill-{i} (the filter that applies to it)
    if i > 0:
        inputs.append(Input(f"pg-drill-{i}", "data"))

    # Read all prior drill filters as State (for cumulative filtering)
    drill_states = [State(f"pg-drill-{j}", "data") for j in range(1, i + 1)]

    @app.callback(
        Output(f"pg-card-{i}-chart", "figure"),
        inputs,
        [State("universal-portfolio-dropdown", "value"),
         State("time-window-store", "data"),
         State("custom-metric-store", "data"),
         *drill_states],
        prevent_initial_call=True,
    )
    def update_chart(*args, _i=i):
        n_drill = _i  # number of drill state values
        plot_type, metric, seg, agg = args[0], args[1], args[2], args[3]
        # States at end: portfolio, tw, cm, then drill filters 1.._i
        portfolio = args[-(n_drill + 3)]

        if not portfolio:
            return no_update

        metric = metric or "balance"
        agg = agg or "sum"
        plot_type = plot_type or "bar"
        windowed = app_state._apply_time_window(app_state.facilities_df)

        # Collect cumulative drill filters from states
        active_filters = []
        for j in range(n_drill):
            f = args[-(n_drill - j)]
            if f:
                active_filters.append(f)

        return _build_chart(
            windowed, app_state.portfolios, portfolio,
            metric, "monthly", seg, agg, plot_type, active_filters,
        )


def _register_click_callback(app, i: int, app_state):
    """Drill into next card based on legend selection (visible traces)."""
    graph_id = f"pg-card-{i}-chart"

    # Clientside: read trace visibility from Plotly _fullData on restyleData
    app.clientside_callback(
        """
        function(restyleData, figureData) {
            if (!figureData || !figureData.data) return window.dash_clientside.no_update;
            var graphEl = document.getElementById('%s');
            var traces = (graphEl && graphEl._fullData) ? graphEl._fullData : figureData.data;
            var result = [];
            for (var t = 0; t < traces.length; t++) {
                var vis = traces[t].visible;
                if (vis === undefined || vis === true) {
                    result.push(traces[t].name || '');
                }
            }
            return result;
        }
        """ % graph_id,
        Output(f"pg-card-{i}-trace-vis", "data"),
        Input(graph_id, "restyleData"),
        State(graph_id, "figure"),
        prevent_initial_call=True,
    )

    # Server: update the NEXT card's drill filter store
    next_card = i + 1
    # Also clear downstream filters when this card's legend changes
    downstream_outputs = [Output(f"pg-drill-{next_card}", "data")]
    for j in range(next_card + 1, _MAX_CARDS):
        downstream_outputs.append(Output(f"pg-drill-{j}", "data", allow_duplicate=True))

    @app.callback(
        downstream_outputs,
        Input(f"pg-card-{i}-trace-vis", "data"),
        [State(f"pg-card-{i}-seg", "value"),
         State(f"pg-card-{i}-chart", "figure")],
        prevent_initial_call=True,
    )
    def on_vis_change(visible_names, seg_col, figure, _i=i, _next=next_card):
        n_outputs = _MAX_CARDS - _next
        if not seg_col or not figure or "data" not in figure:
            return [no_update] * n_outputs

        total_traces = len(figure["data"])

        if visible_names and len(visible_names) < total_traces:
            new_filter = {"column": seg_col, "values": visible_names}
        else:
            new_filter = None

        # First output is next card's filter, rest are cleared
        return [new_filter] + [None] * (n_outputs - 1)


def _register_badge_callback(app, i: int):
    @app.callback(
        Output(f"pg-card-{i}-badge", "children"),
        Input(f"pg-drill-{i}", "data"),
        prevent_initial_call=True,
    )
    def update_badge(f, _i=i):
        if not f:
            return ""
        col = f["column"].replace("_", " ").title()
        if f.get("values"):
            vals = ", ".join(f["values"])
            return f"Filter: {col} ∈ {{{vals}}}"
        return f"Filter: {col} = {f.get('value', '')}"


def _register_plot_toggle(app, i: int):
    @app.callback(
        [Output(f"pg-card-{i}-plot", "data"),
         Output(f"pg-card-{i}-plot-toggle", "children"),
         Output(f"pg-card-{i}-plot-toggle", "title")],
        Input(f"pg-card-{i}-plot-toggle", "n_clicks"),
        State(f"pg-card-{i}-plot", "data"),
        prevent_initial_call=True,
    )
    def toggle_plot(n, current):
        bar_icon = html.Span("III", className="pg-icon-inner")
        line_icon = html.Span("∿", className="pg-icon-inner")
        if current == "bar":
            return "line", line_icon, "Switch to bar chart"
        return "bar", bar_icon, "Switch to line chart"


def _register_settings_toggle(app, i: int):
    @app.callback(
        Output(f"pg-card-{i}-settings-panel", "style"),
        Input(f"pg-card-{i}-settings-btn", "n_clicks"),
        State(f"pg-card-{i}-settings-panel", "style"),
        prevent_initial_call=True,
    )
    def toggle_settings(n, style):
        if style and style.get("display") == "none":
            return {"display": "block"}
        return {"display": "none"}


def _register_detail_callback(app, i: int, app_state):
    """Wire clickData on card chart to the detail panel below it."""
    graph_id = f"pg-card-{i}-chart"

    @app.callback(
        [Output(f"pg-card-{i}-detail-panel", "style"),
         Output(f"pg-card-{i}-detail-table", "data"),
         Output(f"pg-card-{i}-detail-table", "columns"),
         Output(f"pg-card-{i}-detail-title", "children"),
         Output(f"pg-card-{i}-last-click", "data"),
         Output(graph_id, "figure", allow_duplicate=True)],
        [Input(graph_id, "clickData"),
         Input(f"pg-card-{i}-detail-close", "n_clicks")],
        [State(f"pg-card-{i}-last-click", "data"),
         State(f"pg-card-{i}-metric", "value"),
         State(f"pg-card-{i}-seg", "value"),
         State(f"pg-card-{i}-agg", "value"),
         State("universal-portfolio-dropdown", "value"),
         State(graph_id, "figure"),
         *[State(f"pg-drill-{j}", "data") for j in range(1, i + 1)]],
        prevent_initial_call=True,
    )
    def handle_detail(click_data, close_clicks, last_click,
                      metric, seg, agg, portfolio, current_fig,
                      *drill_states, _i=i):
        triggered = callback_context.triggered_id
        hide = {"display": "none"}

        def _reset_opacity(fig_dict):
            if not fig_dict or "data" not in fig_dict:
                return no_update
            fig = go.Figure(fig_dict)
            for trace in fig.data:
                trace.marker.opacity = 1.0
            return fig

        def _dim_others(fig_dict, clicked_x, clicked_curve):
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

        # Close button — hide panel
        if triggered != graph_id:
            return hide, no_update, no_update, no_update, None, _reset_opacity(current_fig)

        if not click_data or not click_data.get("points"):
            return hide, no_update, no_update, no_update, None, _reset_opacity(current_fig)

        point = click_data["points"][0]
        curve_name = ""
        if point.get("customdata"):
            cd = point["customdata"]
            curve_name = str(cd[0]) if isinstance(cd, (list, tuple)) else str(cd)
        x_value = str(point.get("x", ""))

        # Toggle: same point → hide
        click_key = f"{x_value}|{curve_name}"
        if last_click == click_key:
            return hide, no_update, no_update, no_update, None, _reset_opacity(current_fig)

        # Build detail dataframe
        if not portfolio or portfolio not in app_state.portfolios:
            return hide, no_update, no_update, no_update, None, no_update

        windowed = app_state._apply_time_window(app_state.facilities_df)
        filtered = _apply_filters(windowed, app_state.portfolios[portfolio])

        # Apply drill filters for this card (from per-card stores)
        active_filters = [f for f in drill_states if f]
        filtered = _apply_drill_filters(filtered, active_filters)

        # Filter to clicked period
        filtered = add_period_column(filtered, "monthly")
        filtered = filtered.filter(pl.col("_period") == x_value)

        # Filter to clicked segment if segmented
        if seg and curve_name and seg in filtered.columns:
            filtered = filtered.filter(pl.col(seg).cast(pl.Utf8) == curve_name)

        if filtered.is_empty():
            return hide, no_update, no_update, no_update, None, _reset_opacity(current_fig)

        # Drop internal columns, limit display columns
        drop = {"_period"}
        display_cols = [c for c in filtered.columns if c not in drop]
        detail_df = filtered.select(display_cols).head(200)

        # Format for DataTable
        columns = [{"name": c.replace("_", " ").title(), "id": c} for c in detail_df.columns]
        data = detail_df.to_dicts()
        title = f"Details for {x_value}"
        if curve_name:
            title += f" — {curve_name}"

        updated_fig = _dim_others(current_fig, x_value, curve_name)

        return (
            {"display": "block", "animation": "detail-slide-in 0.2s ease-out"},
            data, columns, title, click_key, updated_fig,
        )


register_tab(PlaygroundTab())


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_metric_options(df: pl.DataFrame) -> list[dict]:
    from ..app_state import app_state
    exclude = {"facility_id", "obligor_rating", "latitude", "longitude"}
    numeric_types = (pl.Float64, pl.Float32, pl.Int64, pl.Int32)
    cols = [c for c in df.columns if c not in exclude and df[c].dtype in numeric_types]
    for name, meta in app_state.custom_metrics.items():
        mt = meta.get("metric_type", "numeric")
        if mt == "numeric" and name in df.columns and name not in cols:
            cols.append(name)
    if "balance" in cols:
        cols.remove("balance")
        cols.insert(0, "balance")
    return [{"label": c.replace("_", " ").title(), "value": c} for c in cols]


def _get_segmentation_options(df: pl.DataFrame) -> list[dict]:
    from ..utils.helpers import append_custom_segmentation_options
    exclude_ids = {"facility_id", "reporting_date", "origination_date", "maturity_date", "obligor_name"}
    cols = []
    for c in df.columns:
        if c in exclude_ids:
            continue
        if df[c].dtype in (pl.Utf8, pl.Categorical):
            cols.append({"label": c.replace("_", " ").title(), "value": c})
    return append_custom_segmentation_options(cols)


def _apply_filters(df: pl.DataFrame, criteria) -> pl.DataFrame:
    from ..data.dataset import Dataset
    return Dataset.apply_criteria(df, criteria)


def _apply_drill_filters(df: pl.DataFrame, drill_filters: list[dict | None]) -> pl.DataFrame:
    """Apply a chain of ephemeral drill-down filters."""
    for f in drill_filters:
        if not f or not f.get("column"):
            continue
        col = f["column"]
        if col not in df.columns:
            continue
        if f.get("values"):
            # Multiple values (legend selection)
            df = df.filter(pl.col(col).cast(pl.Utf8).is_in(f["values"]))
        elif f.get("value"):
            # Single value (legacy)
            df = df.filter(pl.col(col).cast(pl.Utf8) == str(f["value"]))
    return df


def _build_chart(
    df: pl.DataFrame, portfolios: dict, portfolio: str,
    metric: str, freq: str, segmentation: str | None,
    agg: str, plot_type: str, drill_filters: list[dict | None],
) -> go.Figure:
    """Build a bar or line chart with cumulative drill filters applied."""
    if portfolio not in portfolios:
        return empty_figure("Select a portfolio", 380)

    filtered = _apply_filters(df, portfolios[portfolio])
    filtered = _apply_drill_filters(filtered, drill_filters)

    if filtered.is_empty() or metric not in filtered.columns:
        return empty_figure("No data", 380)
    if "reporting_date" not in filtered.columns:
        return empty_figure("No date column", 380)

    filtered = add_period_column(filtered, freq)

    group_cols = ["_period"]
    if segmentation and segmentation in filtered.columns:
        filtered = filtered.filter(pl.col(segmentation).is_not_null())
        group_cols.append(segmentation)

    agg_expr = pl.col(metric).mean() if agg == "avg" else pl.col(metric).sum()
    agg_df = filtered.group_by(group_cols).agg(agg_expr).sort("_period")

    if agg_df.is_empty():
        return empty_figure("No data", 380)

    fig = go.Figure()
    metric_label = metric.replace("_", " ").title()

    if segmentation and segmentation in agg_df.columns:
        segments = agg_df[segmentation].unique().sort().to_list()
        for idx, seg in enumerate(segments):
            seg_data = agg_df.filter(pl.col(segmentation) == seg)
            periods = seg_data["_period"].to_list()
            y_vals = seg_data[metric].to_list()
            color = _COLORS[idx % len(_COLORS)]
            if plot_type == "line":
                fig.add_trace(go.Scatter(
                    x=periods, y=y_vals, mode="lines",
                    name=str(seg), line=dict(color=color, width=2),
                    customdata=[[str(seg)] for _ in periods],
                ))
            else:
                fig.add_trace(go.Bar(
                    x=periods, y=y_vals, name=str(seg),
                    customdata=[[str(seg)] for _ in periods],
                    marker_color=color,
                ))
        if plot_type == "bar":
            fig.update_layout(barmode="stack")
    else:
        periods = agg_df["_period"].to_list()
        y_vals = agg_df[metric].to_list()
        if plot_type == "line":
            fig.add_trace(go.Scatter(
                x=periods, y=y_vals, mode="lines",
                line=dict(color="#c96442", width=2),
                name=metric_label,
                customdata=[[metric_label] for _ in periods],
            ))
        else:
            fig.add_trace(go.Bar(
                x=periods, y=y_vals,
                customdata=[[metric_label] for _ in periods],
                marker_color="#c96442", name=metric_label,
            ))

    all_periods = agg_df["_period"].unique().sort().to_list()
    tick_labels = [format_period(p, freq) for p in all_periods]

    theme = plotly_theme(
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_layout(**theme, yaxis_title=metric_label, clickmode="event")
    fig.update_xaxes(
        tickvals=all_periods,
        ticktext=tick_labels,
        tickangle=-45 if len(all_periods) > 12 else 0,
    )
    return fig


def _register_save_to_portfolio(app, app_state):
    """Open the portfolio creation wizard pre-populated with playground drill filters."""
    from ..callbacks.portfolio_callbacks import _render_filter_levels
    from ..utils.helpers import MODAL_SHOWN

    @app.callback(
        [Output("portfolio-create-modal", "style", allow_duplicate=True),
         Output("portfolio-filter-state", "data", allow_duplicate=True),
         Output("filter-levels-container", "children", allow_duplicate=True),
         Output("portfolio-edit-name", "data", allow_duplicate=True),
         Output("portfolio-wizard-title", "children", allow_duplicate=True),
         Output("create-portfolio-name-input", "value", allow_duplicate=True),
         Output("create-portfolio-name-input", "disabled", allow_duplicate=True),
         Output("reference-portfolio-dropdown", "options", allow_duplicate=True),
         Output("reference-portfolio-dropdown", "value", allow_duplicate=True)],
        Input("pg-save-portfolio", "n_clicks"),
        [State("universal-portfolio-dropdown", "value"),
         *[State(f"pg-drill-{j}", "data") for j in range(1, _MAX_CARDS)]],
        prevent_initial_call=True,
    )
    def save_to_portfolio(n_clicks, current_portfolio, *drill_filters):
        if not n_clicks:
            return (no_update,) * 9

        # Start with existing portfolio filters (from the reference portfolio)
        base_filters = []
        if current_portfolio and current_portfolio in app_state.portfolios:
            from ..app_state import AppState
            criteria = AppState._migrate_criteria(app_state.portfolios[current_portfolio])
            base_filters = list(criteria.get("filters", []))

        # Append drill filters from playground cards
        for f in drill_filters:
            if f and f.get("column") and f.get("values"):
                base_filters.append({
                    "column": f["column"],
                    "values": [str(v) for v in f["values"]],
                })

        if not base_filters:
            return (no_update,) * 9

        ref_opts = [{"label": p, "value": p} for p in app_state.available_portfolios]
        title = f"Create Portfolio from Playground"
        if current_portfolio:
            title += f" ({current_portfolio})"
        return (
            MODAL_SHOWN,
            base_filters,
            _render_filter_levels(base_filters),
            None,
            title,
            "",
            False,
            ref_opts,
            no_update,  # Don't set reference dropdown — it would trigger overwrite
        )
