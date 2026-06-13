"""
Portfolio Summary tab – the default landing page.

Layout: TWO_COL (bar chart | waterfall chart).
Toolbar: Metric (all numeric cols) + Frequency (M/Q/A).
Left card: time-series bar chart with optional segmentation stacked bars.
Right card: period-over-period waterfall (run-off / changes / new origination).
"""

from __future__ import annotations

import json
from datetime import datetime

import plotly.graph_objs as go
import polars as pl
from dash import callback, dcc, html, Input, Output, no_update

from .registry import BaseTab, ContentLayout, TabContext, register_tab
from ..components.mixins.click_detail import chart_with_detail_layout, register_detail_callback
from ..utils.helpers import plotly_theme, empty_figure, add_period_column, format_period, SEGMENT_COLORS


class PortfolioSummaryTab(BaseTab):
    id = "portfolio-summary"
    label = "Portfolio Summary"
    order = 10
    tier = "gold"
    tier_tooltip = "Gold tier — set tier='gold' in your BaseTab subclass"
    content_layout = ContentLayout.TWO_COL

    def render(self, ctx: TabContext):
        """Custom layout: KPI strip · composition (bar + waterfall) · top movers."""
        from ..app_state import app_state

        metric_opts = _get_metric_options(ctx.facilities_df)
        default_metric = "balance" if any(o["value"] == "balance" for o in metric_opts) else (metric_opts[0]["value"] if metric_opts else "balance")
        seg_opts = _get_segmentation_options(ctx.facilities_df)
        app_state.register_control("ps-segmentation", preserve=True)
        current_seg = app_state.get_control_value("ps-segmentation")

        # Portfolio-filtered, time-windowed frame (all periods) for KPIs + movers
        if ctx.selected_portfolio in ctx.portfolios:
            pf = _apply_filters(ctx.facilities_df, ctx.portfolios[ctx.selected_portfolio])
        else:
            pf = ctx.facilities_df

        kpis = _compute_kpis(pf)
        movers = _top_movers(pf)

        # Timeline scrubber — a draggable sub-window over the available periods.
        scrub_dates, _scrub_totals = _scrubber_periods(pf)
        n = len(scrub_dates)
        s_idx = max(0, n - 12)
        e_idx = n - 1 if n else 0
        scrub_val = f"{scrub_dates[s_idx]},{scrub_dates[e_idx]}" if n >= 2 else ""
        scoped = _apply_scrubber(ctx.facilities_df, scrub_val)

        fig = _build_bar_chart(scoped, ctx.portfolios,
                               ctx.selected_portfolio, default_metric, "monthly", current_seg)
        fig_right = _build_waterfall_chart(scoped, ctx.portfolios,
                                           ctx.selected_portfolio, default_metric, "monthly")

        _dd = {"fontSize": "13px"}
        # Middle-level controls (apply to BOTH charts): metric + frequency.
        controls = html.Div([
            dcc.Dropdown(id="ps-metric", options=metric_opts, value=default_metric,
                         clearable=False, style={**_dd, "width": "170px"}),
            dcc.Dropdown(id="ps-freq", options=[
                {"label": "Monthly", "value": "monthly"},
                {"label": "Quarterly", "value": "quarterly"},
                {"label": "Annually", "value": "annually"},
            ], value="monthly", clearable=False, style={**_dd, "width": "130px"}),
        ], className="gc-group", style={"gap": "10px"})

        # Segmentation applies only to the Exposure-over-time bar chart.
        segmentation_ctrl = dcc.Dropdown(
            id="ps-segmentation", options=seg_opts, value=current_seg,
            placeholder="No segmentation", clearable=True,
            style={**_dd, "width": "190px"})

        return html.Div([
            _kpi_strip(kpis),

            # Control row: status dot (left) · metric · frequency · slider (right-aligned).
            html.Div([
                html.Span(className=f"tier-dot tier-badge--{self.tier}",
                          title=self.tier_tooltip or f"{self.tier.capitalize()} tier"),
                html.Div([
                    controls,
                    _scrubber(scrub_dates, s_idx, e_idx),
                ], className="gc-group", style={"gap": "12px", "justifyContent": "flex-end"}),
                dcc.Input(id="ps-scrubber-input", type="text", value=scrub_val,
                          style={"display": "none"}),
            ], className="section-head", style={"gap": "12px", "flexWrap": "wrap",
                                                "justifyContent": "space-between"}),

            html.Div([

                html.Div([
                    html.Div([
                        html.Div([
                            html.H3("Exposure over time"),
                            segmentation_ctrl,
                        ], className="card-head", style={"alignItems": "center"}),
                        html.Div(chart_with_detail_layout("ps-bar-chart", figure=fig, height=400),
                                 className="card-body pad-tight"),
                    ], className="card"),
                    html.Div([
                        html.Div([html.H3("Period-over-period change")], className="card-head"),
                        html.Div([
                            html.Div([
                                html.Span([html.Span(className="legend-swatch",
                                                     style={"background": _WATERFALL_COLORS["Run-off"]}), "Run-off"],
                                          className="legend-item"),
                                html.Span([html.Span(className="legend-swatch",
                                                     style={"background": _WATERFALL_COLORS["Changes"]}), "Changes"],
                                          className="legend-item"),
                                html.Span([html.Span(className="legend-swatch",
                                                     style={"background": _WATERFALL_COLORS["New Origination"]}), "New origination"],
                                          className="legend-item"),
                            ], className="legend", style={"marginBottom": "8px"}),
                            chart_with_detail_layout("ps-waterfall-chart", figure=fig_right, height=360),
                            html.Div(
                                _waterfall_stats(ctx.facilities_df, ctx.portfolios,
                                                 ctx.selected_portfolio, default_metric, "monthly"),
                                id="ps-waterfall-stats",
                            ),
                        ], className="card-body"),
                    ], className="card"),
                ], className="chart-row"),
            ], className="section"),

            html.Div([
                html.Div([
                    html.Div("Top movers", className="section-title"),
                    html.Span(f"{len(movers)} shown · by Δ exposure", className="section-sub"),
                ], className="section-head"),
                html.Div([_facility_card(m) for m in movers], className="facility-grid"),
            ], className="section"),
        ])

    def register_callbacks(self, app):
        from ..app_state import app_state

        @callback(
            Output("ps-bar-chart", "figure"),
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data"),
             Input("custom-metric-store", "data"),
             Input("ps-metric", "value"),
             Input("ps-freq", "value"),
             Input("ps-segmentation", "value"),
             Input("ps-scrubber-input", "value")],
            prevent_initial_call=True,
        )
        def update_chart(portfolio, _tw, _cm, metric, freq, segmentation, scrub):
            if not portfolio:
                return no_update
            app_state.set_control_value("ps-segmentation", segmentation)
            metric = metric or "balance"
            freq = freq or "monthly"
            windowed = app_state._apply_time_window(app_state.facilities_df)
            scoped = _apply_scrubber(windowed, scrub)
            return _build_bar_chart(scoped, app_state.portfolios,
                                    portfolio, metric, freq, segmentation)

        def _get_bar_detail(click_point, curve_name, x_value, portfolio):
            """Return filtered rows for the clicked bar's period + segment."""
            if not portfolio or portfolio not in app_state.portfolios:
                return None
            windowed = app_state._apply_time_window(app_state.facilities_df)
            filtered = _apply_filters(windowed, app_state.portfolios[portfolio])
            if filtered.is_empty():
                return None

            # Determine period column to match against
            if "reporting_date" not in filtered.columns:
                return None

            rd = filtered["reporting_date"]
            date_col = pl.col("reporting_date")
            if rd.dtype != pl.Utf8:
                date_col = date_col.cast(pl.Utf8)

            # Match rows whose reporting_date falls in the clicked period
            year_expr = date_col.str.slice(0, 4)
            month_expr = date_col.str.slice(5, 2)

            # x_value is the period string like "2024-06-01"
            period_year = x_value[:4]
            period_month = x_value[5:7] if len(x_value) >= 7 else "01"

            # Determine current frequency from the x_value pattern
            # We filter to rows matching the period
            result = filtered.filter(year_expr == period_year)
            if period_month != "01" or x_value.endswith("-01-01"):
                # Monthly or specific quarter start
                p_month = int(period_month)
                # Check if this is a quarter start (1,4,7,10)
                if p_month in (1, 4, 7, 10) and x_value.endswith("-01"):
                    # Could be quarterly — include 3 months
                    months = [str(m).zfill(2) for m in range(p_month, min(p_month + 3, 13))]
                    result = result.filter(month_expr.is_in(months))
                else:
                    result = result.filter(month_expr == period_month)

            # Filter by segment if stacked bar
            if curve_name and curve_name not in ("", x_value):
                # Find a categorical column that contains this segment value
                for col in filtered.columns:
                    if filtered[col].dtype in (pl.Utf8, pl.Categorical):
                        if curve_name in filtered[col].cast(pl.Utf8).unique().to_list():
                            result = result.filter(pl.col(col).cast(pl.Utf8) == curve_name)
                            break

            if result.is_empty():
                return None

            # Return a useful subset of columns
            show_cols = [c for c in result.columns if c not in ("_period",)]
            return result.select(show_cols).head(200)

        from dash import State as DashState
        register_detail_callback(
            app, "ps-bar-chart", detail_fn=_get_bar_detail,
            extra_states=[DashState("universal-portfolio-dropdown", "value")],
            reset_inputs=[
                Input("ps-metric", "value"),
                Input("ps-freq", "value"),
                Input("ps-segmentation", "value"),
            ],
        )

        @callback(
            [Output("ps-waterfall-chart", "figure"),
             Output("ps-waterfall-stats", "children")],
            [Input("universal-portfolio-dropdown", "value"),
             Input("time-window-store", "data"),
             Input("custom-metric-store", "data"),
             Input("ps-metric", "value"),
             Input("ps-freq", "value"),
             Input("ps-scrubber-input", "value")],
            prevent_initial_call=True,
        )
        def update_waterfall_chart(portfolio, _tw, _cm, metric, freq, scrub):
            if not portfolio:
                return no_update, no_update
            metric = metric or "balance"
            freq = freq or "monthly"
            windowed = app_state._apply_time_window(app_state.facilities_df)
            scoped = _apply_scrubber(windowed, scrub)
            fig = _build_waterfall_chart(scoped, app_state.portfolios,
                                         portfolio, metric, freq)
            stats = _waterfall_stats(scoped, app_state.portfolios, portfolio, metric, freq)
            return fig, stats

        def _get_waterfall_detail(click_point, curve_name, x_value, portfolio, freq):
            """Return facility rows for the clicked waterfall bar category."""
            if not portfolio or portfolio not in app_state.portfolios:
                return None
            windowed = app_state._apply_time_window(app_state.facilities_df)
            filtered = _apply_filters(windowed, app_state.portfolios[portfolio])
            if filtered.is_empty() or "reporting_date" not in filtered.columns:
                return None

            freq = freq or "monthly"
            df_with_period = _add_period_column(filtered, freq)
            periods = df_with_period["_period"].unique().sort().to_list()

            # Map x_value back to raw period
            curr_period = _x_value_to_period(x_value, periods, freq)
            if curr_period is None or curr_period not in periods:
                return None
            idx = periods.index(curr_period)
            if idx == 0:
                return None  # first period has no previous
            prev_period = periods[idx - 1]

            prev_rows = df_with_period.filter(pl.col("_period") == prev_period)
            curr_rows = df_with_period.filter(pl.col("_period") == curr_period)
            prev_ids = set(prev_rows["facility_id"].to_list())
            curr_ids = set(curr_rows["facility_id"].to_list())

            if curve_name == "Run-off":
                ids = prev_ids - curr_ids
                result = prev_rows.filter(pl.col("facility_id").is_in(list(ids)))
            elif curve_name == "New Origination":
                ids = curr_ids - prev_ids
                result = curr_rows.filter(pl.col("facility_id").is_in(list(ids)))
            elif curve_name == "Changes":
                ids = prev_ids & curr_ids
                result = curr_rows.filter(pl.col("facility_id").is_in(list(ids)))
            else:
                return None

            if result.is_empty():
                return None
            show_cols = [c for c in result.columns if c != "_period"]
            return result.select(show_cols).head(200)

        register_detail_callback(
            app, "ps-waterfall-chart", detail_fn=_get_waterfall_detail,
            extra_states=[DashState("universal-portfolio-dropdown", "value"),
                          DashState("ps-freq", "value")],
            reset_inputs=[
                Input("ps-metric", "value"),
                Input("ps-freq", "value"),
            ],
        )


register_tab(PortfolioSummaryTab())


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_metric_options(df: pl.DataFrame):
    from ..app_state import app_state
    # Always include balance; plus numeric custom metrics only
    allowed = {"balance"}
    for name, meta in app_state.custom_metrics.items():
        mt = meta.get("metric_type", "numeric")
        if mt == "numeric":
            allowed.add(name)
    numeric = [c for c in df.columns if c in allowed and df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32)]
    # Ensure balance appears first if present
    if "balance" in numeric:
        numeric.remove("balance")
        numeric.insert(0, "balance")
    return [{"label": c.replace("_", " ").title(), "value": c} for c in numeric]


def _get_segmentation_options(df: pl.DataFrame):
    """Return categorical columns suitable for segmentation, including custom categorical/indicator metrics."""
    from ..utils.helpers import append_custom_segmentation_options
    exclude_ids = {"facility_id", "reporting_date", "origination_date", "maturity_date", "obligor_name"}
    cols = []
    for c in df.columns:
        if c in exclude_ids:
            continue
        if df[c].dtype in (pl.Utf8, pl.Categorical):
            cols.append({"label": c.replace("_", " ").title(), "value": c})
    return append_custom_segmentation_options(cols)


def _apply_filters(df: pl.DataFrame, criteria):
    from ..data.dataset import Dataset
    return Dataset.apply_criteria(df, criteria)


def _resample(df: pl.DataFrame, freq: str, metric: str, segmentation: str | None):
    """Aggregate metric by date (and optional segmentation) at the given frequency."""
    if "reporting_date" not in df.columns or metric not in df.columns:
        return pl.DataFrame()

    df = _add_period_column(df, freq)

    group_cols = ["_period"]
    if segmentation and segmentation in df.columns:
        group_cols.append(segmentation)

    result = df.group_by(group_cols).agg(pl.col(metric).sum()).sort("_period")
    return result


# Palette for stacked segments — IRIS-D Redesign categorical colors
_COLORS = SEGMENT_COLORS


_format_period = format_period  # backward compat alias


def _build_bar_chart(df, portfolios, portfolio, metric, freq, segmentation):
    """Build a (stacked) bar chart of the metric over time."""
    if portfolio not in portfolios:
        return empty_figure("Select a portfolio", 400)

    filtered = _apply_filters(df, portfolios[portfolio])
    if len(filtered) == 0 or metric not in filtered.columns:
        return empty_figure("No data", 400)

    agg = _resample(filtered, freq, metric, segmentation)
    if agg.is_empty():
        return empty_figure("No data", 400)

    fig = go.Figure()

    metric_label = metric.replace("_", " ").title()

    if segmentation and segmentation in agg.columns:
        segments = agg[segmentation].unique().sort().to_list()
        for i, seg in enumerate(segments):
            seg_data = agg.filter(pl.col(segmentation) == seg)
            seg_periods = seg_data["_period"].to_list()
            fig.add_trace(go.Bar(
                x=seg_periods,
                y=seg_data[metric].to_list(),
                name=str(seg),
                customdata=[[str(seg)] for _ in seg_periods],
                marker_color=_COLORS[i % len(_COLORS)],
            ))
        fig.update_layout(barmode="stack")
    else:
        periods_list = agg["_period"].to_list()
        fig.add_trace(go.Bar(
            x=periods_list,
            y=agg[metric].to_list(),
            customdata=[[metric_label] for _ in periods_list],
            marker_color="#9d3a4a",
            name=metric_label,
        ))

    # Format x-axis tick labels based on frequency
    periods = agg["_period"].unique().sort().to_list()
    tick_labels = [_format_period(p, freq) for p in periods]

    theme = plotly_theme(
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_layout(**theme, yaxis_title=metric_label, clickmode="event")
    fig.update_xaxes(
        tickvals=periods,
        ticktext=tick_labels,
        tickangle=-45 if len(periods) > 12 else 0,
    )
    return fig


_add_period_column = add_period_column  # backward compat alias


def _compute_period_changes(df: pl.DataFrame, freq: str, metric: str) -> pl.DataFrame:
    """Compute run-off, changes, and new origination between consecutive periods."""
    if "reporting_date" not in df.columns or metric not in df.columns or "facility_id" not in df.columns:
        return pl.DataFrame()

    df = _add_period_column(df, freq)
    periods = df["_period"].unique().sort().to_list()
    if len(periods) < 2:
        return pl.DataFrame()

    rows: list[dict] = []
    for i in range(1, len(periods)):
        prev_p, curr_p = periods[i - 1], periods[i]
        prev = df.filter(pl.col("_period") == prev_p)
        curr = df.filter(pl.col("_period") == curr_p)
        prev_ids = set(prev["facility_id"].to_list())
        curr_ids = set(curr["facility_id"].to_list())

        runoff_ids = prev_ids - curr_ids
        new_ids = curr_ids - prev_ids
        common_ids = prev_ids & curr_ids

        runoff_val = -prev.filter(pl.col("facility_id").is_in(list(runoff_ids)))[metric].sum() if runoff_ids else 0
        new_val = curr.filter(pl.col("facility_id").is_in(list(new_ids)))[metric].sum() if new_ids else 0
        if common_ids:
            common_list = list(common_ids)
            curr_sum = curr.filter(pl.col("facility_id").is_in(common_list))[metric].sum()
            prev_sum = prev.filter(pl.col("facility_id").is_in(common_list))[metric].sum()
            changes_val = curr_sum - prev_sum
        else:
            changes_val = 0

        rows.append({"_period": curr_p, "category": "Run-off", "value": runoff_val})
        rows.append({"_period": curr_p, "category": "Changes", "value": changes_val})
        rows.append({"_period": curr_p, "category": "New Origination", "value": new_val})

    return pl.DataFrame(rows)


# Ledger waterfall: red run-off, blue changes, green new (mid-tones for both themes)
_WATERFALL_COLORS = {
    "Run-off": "#b4434e",
    "Changes": "#4a7396",
    "New Origination": "#2e8063",
}


def _build_waterfall_chart(df, portfolios, portfolio, metric, freq):
    """Build a period-over-period waterfall chart."""
    if portfolio not in portfolios:
        return empty_figure("Select a portfolio", 400)

    filtered = _apply_filters(df, portfolios[portfolio])
    if filtered.is_empty() or metric not in filtered.columns:
        return empty_figure("No data", 400)

    changes = _compute_period_changes(filtered, freq, metric)
    if changes.is_empty():
        return empty_figure("Not enough periods", 400)

    fig = go.Figure()

    for category in ["Run-off", "Changes", "New Origination"]:
        cat_data = changes.filter(pl.col("category") == category)
        periods_list = cat_data["_period"].to_list()
        fig.add_trace(go.Bar(
            x=periods_list,
            y=cat_data["value"].to_list(),
            name=category,
            customdata=[[category] for _ in periods_list],
            marker_color=_WATERFALL_COLORS[category],
        ))

    periods = changes["_period"].unique().sort().to_list()
    tick_labels = [_format_period(p, freq) for p in periods]
    metric_label = metric.replace("_", " ").title()

    theme = plotly_theme(
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_layout(**theme, barmode="relative", yaxis_title=f"{metric_label} Change",
                      clickmode="event")
    fig.update_xaxes(
        tickvals=periods,
        ticktext=tick_labels,
        tickangle=-45 if len(periods) > 12 else 0,
    )
    return fig



def _x_value_to_period(x_value: str, periods: list[str], freq: str) -> str | None:
    """Map an x_value (which may be a formatted label or raw period) to a raw period string."""
    if x_value in periods:
        return x_value
    # Try matching by formatted label
    for p in periods:
        if _format_period(p, freq) == x_value:
            return p
    return None


# ── KPI strip ─────────────────────────────────────────────────────────────────

def _fmt_m(v) -> str:
    """Format raw dollars as an abbreviated string (52.54B / 384M)."""
    v = v or 0
    if abs(v) >= 1e9:
        return f"{v / 1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"{v / 1e6:.0f}M"
    if abs(v) >= 1e3:
        return f"{v / 1e3:.0f}K"
    return f"{v:,.0f}"


def _fmt_kpi(v, fmt: str) -> str:
    if fmt == "currency":
        return "$" + _fmt_m(v)
    if fmt == "rating":
        return f"{v:.1f}"
    return f"{int(round(v or 0)):,}"


def _spark_img(points, color: str):
    """Build a tiny sparkline as an inline data-URI ``<img>`` (no Plotly needed)."""
    pts = [p for p in (points or []) if p is not None]
    if len(pts) < 2:
        return html.Span()
    w, h, pad = 80, 28, 2
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1
    n = len(pts)
    xs = [pad + i * (w - 2 * pad) / (n - 1) for i in range(n)]
    ys = [h - pad - ((p - lo) * (h - 2 * pad) / rng) for p in pts]
    line = " ".join(f"{'M' if i == 0 else 'L'}{xs[i]:.1f},{ys[i]:.1f}" for i in range(n))
    area = f"{line} L{xs[-1]:.1f},{h - pad:.1f} L{xs[0]:.1f},{h - pad:.1f} Z"
    c = color.replace("#", "%23")
    svg = (
        f"%3Csvg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}'%3E"
        f"%3Cpath d='{area}' fill='{c}' opacity='0.18'/%3E"
        f"%3Cpath d='{line}' fill='none' stroke='{c}' stroke-width='1.5'/%3E"
        f"%3C/svg%3E"
    )
    return html.Img(src="data:image/svg+xml," + svg, width=w, height=h, style={"display": "block"})


def _compute_kpis(df: pl.DataFrame) -> list[dict]:
    """Compute the 4 headline KPIs (time series + delta) from real facility data."""
    if df is None or df.is_empty() or "reporting_date" not in df.columns:
        return []
    dates = df["reporting_date"].unique().sort().to_list()
    if not dates:
        return []

    def smap(sub):
        return dict(zip(sub["reporting_date"].to_list(), sub["v"].to_list()))

    exp = smap(df.group_by("reporting_date").agg(pl.col("balance").sum().alias("v")))
    cnt = smap(df.group_by("reporting_date").agg(pl.col("facility_id").n_unique().alias("v")))
    watch_df = df.filter(pl.col("obligor_rating") >= 14)
    watch = smap(watch_df.group_by("reporting_date").agg(pl.col("facility_id").n_unique().alias("v"))) if not watch_df.is_empty() else {}
    rating = smap(df.group_by("reporting_date").agg(pl.col("obligor_rating").mean().alias("v")))

    def vals(m):
        return [m.get(d, 0) or 0 for d in dates]

    specs = [
        ("Total Exposure", vals(exp), "currency", False),
        ("Active Facilities", vals(cnt), "count", False),
        ("Watchlist", vals(watch), "count", True),
        ("Avg Risk Rating", vals(rating), "rating", True),
    ]
    out = []
    for label, series, fmt, inverse in specs:
        cur = series[-1] if series else 0
        prev = series[-2] if len(series) > 1 else cur
        dp = ((cur - prev) / prev * 100) if prev else 0.0
        up = cur >= prev
        good = (not up) if inverse else up
        out.append({
            "label": label, "raw": cur, "delta_pct": dp, "good": good, "up": up,
            "value_str": _fmt_kpi(cur, fmt), "spark": series[-12:],
        })
    return out


def _kpi_latest(kpis: list[dict], label: str):
    return next((k["raw"] for k in kpis if k["label"] == label), 0)


def _kpi_card(k: dict):
    arrow = "↑" if k["up"] else "↓"
    cls = "up" if k["good"] else "down"
    spark_color = "#2e8063" if k["good"] else "#b4434e"
    return html.Div([
        html.Div(k["label"], className="kpi-label"),
        html.Div(k["value_str"], className="kpi-value"),
        html.Div([
            html.Span(f"{arrow} {abs(k['delta_pct']):.1f}%", className=f"kpi-delta {cls}"),
            html.Span("vs prev period", className="kpi-subtext"),
        ], className="kpi-sub"),
        html.Div(_spark_img(k["spark"], spark_color), className="kpi-spark"),
    ], className="kpi rise")


def _kpi_strip(kpis: list[dict]):
    if not kpis:
        return html.Div()
    return html.Div([_kpi_card(k) for k in kpis], className="kpi-strip")


# ── Top movers facility grid ───────────────────────────────────────────────────

def _top_movers(df: pl.DataFrame, n: int = 8) -> list[dict]:
    """Top facilities by period-over-period change in balance."""
    if df is None or df.is_empty() or "reporting_date" not in df.columns:
        return []
    dates = df["reporting_date"].unique().sort().to_list()
    if not dates:
        return []
    cols = [c for c in ["facility_id", "obligor_name", "obligor_rating", "balance"] if c in df.columns]
    curr = df.filter(pl.col("reporting_date") == dates[-1]).select(cols)
    if curr.is_empty():
        return []
    if len(dates) >= 2:
        prev = (df.filter(pl.col("reporting_date") == dates[-2])
                  .select(["facility_id", "balance"]).rename({"balance": "prev_balance"}))
        joined = curr.join(prev, on="facility_id", how="left").with_columns(
            (pl.col("balance") - pl.col("prev_balance").fill_null(pl.col("balance"))).alias("delta"))
    else:
        joined = curr.with_columns(
            pl.col("balance").alias("prev_balance"), pl.lit(0.0).alias("delta"))
    joined = joined.sort(pl.col("delta").abs(), descending=True).head(n)
    return joined.to_dicts()


def _facility_card(m: dict):
    rating = m.get("obligor_rating") or 0
    status = "ok" if rating <= 13 else "watch" if rating == 14 else "risk"
    ead = (m.get("balance") or 0) / 1e6
    prev = (m.get("prev_balance") or 0) / 1e6
    delta = (m.get("delta") or 0) / 1e6
    dcls = "up" if delta > 0 else "down" if delta < 0 else "flat"
    sign = "+" if delta > 0 else ""
    return html.Div([
        html.Div([
            html.Div([
                html.Span(className=f"status-dot {status}"),
                html.Span(str(m.get("facility_id", "")), className="facility-mini-name"),
            ], style={"display": "flex", "alignItems": "center", "gap": "8px"}),
            html.Span(str(rating), style={"fontFamily": "var(--font-mono)",
                                          "fontSize": "10px", "color": "var(--text-muted)"}),
        ], className="facility-mini-head"),
        html.Div(str(m.get("obligor_name", "")),
                 style={"fontSize": "var(--fs-xs)", "color": "var(--text-secondary)",
                        "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap"}),
        html.Div([
            html.Div([html.Div("EAD", className="lbl"), html.Div(html.B(f"${ead:,.0f}M"))]),
            html.Div([html.Div("Prev", className="lbl"), html.Div(f"${prev:,.0f}M")]),
            html.Div([html.Div("Δ", className="lbl"),
                      html.Div(html.Span(f"{sign}{delta:,.0f}", className=f"chip-delta {dcls}"))]),
        ], className="facility-mini-meta"),
    ], className="facility-mini rise")


# ── Timeline scrubber ───────────────────────────────────────────────────────────

def _short_label(d: str) -> str:
    try:
        return datetime.fromisoformat(d[:10]).strftime("%b %y")
    except Exception:
        return str(d)


def _scrubber_periods(df: pl.DataFrame):
    """Return (date strings, total-exposure values) per reporting period."""
    if df is None or df.is_empty() or "reporting_date" not in df.columns:
        return [], []
    g = (df.group_by("reporting_date").agg(pl.col("balance").sum().alias("v"))
           .sort("reporting_date"))
    return g["reporting_date"].to_list(), g["v"].to_list()


def _apply_scrubber(df: pl.DataFrame, scrub: str | None) -> pl.DataFrame:
    """Filter rows whose reporting_date falls in the scrubber 'start,end' window."""
    if not scrub or df is None or df.is_empty() or "reporting_date" not in df.columns:
        return df
    parts = scrub.split(",")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return df
    start, end = parts
    col = pl.col("reporting_date").cast(pl.Utf8)
    return df.filter((col >= start) & (col <= end))


def _scrubber(dates: list[str], s_idx: int, e_idx: int):
    """Draggable range selector beneath the composition chart (see scrubber.js)."""
    n = len(dates)
    if n < 2:
        return html.Div()
    labels = [_short_label(d) for d in dates]

    def pct(i):
        return f"{(i / (n - 1)) * 100:.2f}%"

    stride = max(1, (n + 5) // 6)  # ~6 ticks so labels don't crowd the narrow slider
    ticks = [
        html.Span(labels[i], className="scrubber-tick", style={"left": pct(i)})
        for i in range(n) if i % stride == 0 or i == n - 1
    ]

    # Inline slider only: date-range label + draggable track (no presets, no month count).
    return html.Div([
        html.Div([html.B(labels[s_idx]), " → ", html.B(labels[e_idx])], className="range"),
        html.Div([
            html.Div(className="scrubber-track"),
            html.Div(className="scrubber-range",
                     style={"left": pct(s_idx), "width": f"{(e_idx - s_idx) / (n - 1) * 100:.2f}%"}),
            html.Div(className="scrubber-handle", style={"left": pct(s_idx)}, **{"data-handle": "start"}),
            html.Div(className="scrubber-handle", style={"left": pct(e_idx)}, **{"data-handle": "end"}),
            html.Div(ticks, className="scrubber-ticks"),
        ], className="scrubber-track-wrap", id="ps-scrubber-trackwrap",
           **{"data-dates": json.dumps(dates), "data-labels": json.dumps(labels),
              "data-start": str(s_idx), "data-end": str(e_idx)}),
    ], className="scrubber", id="ps-scrubber")


# ── Waterfall summary stats ─────────────────────────────────────────────────────

def _waterfall_stats(df, portfolios, portfolio, metric, freq):
    """Build the Run-off / Changes / New summary row beneath the waterfall."""
    if portfolio not in portfolios:
        return []
    filtered = _apply_filters(df, portfolios[portfolio])
    if filtered.is_empty() or metric not in filtered.columns:
        return []
    changes = _compute_period_changes(filtered, freq, metric)
    if changes.is_empty():
        return []
    sums = {"Run-off": 0.0, "Changes": 0.0, "New Origination": 0.0}
    for row in changes.group_by("category").agg(pl.col("value").sum()).iter_rows(named=True):
        sums[row["category"]] = row["value"]
    items = [
        ("Run-off", sums["Run-off"], _WATERFALL_COLORS["Run-off"], "−"),
        ("Changes", sums["Changes"], _WATERFALL_COLORS["Changes"], "+" if sums["Changes"] >= 0 else "−"),
        ("New", sums["New Origination"], _WATERFALL_COLORS["New Origination"], "+"),
    ]
    cells = [
        html.Div([
            html.Div(label, style={"fontSize": "10px", "color": "var(--text-muted)",
                                   "textTransform": "uppercase", "letterSpacing": "0.06em", "fontWeight": "600"}),
            html.Div(f"{sign}${_fmt_m(abs(val))}", className="mono tabular",
                     style={"fontSize": "var(--fs-lg)", "fontWeight": "600", "color": color, "marginTop": "2px"}),
        ])
        for label, val, color, sign in items
    ]
    return [html.Div(cells, style={
        "marginTop": "10px", "paddingTop": "10px", "borderTop": "1px solid var(--border-hair)",
        "display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "12px",
    })]
