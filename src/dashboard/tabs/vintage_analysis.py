"""
Vintage Analysis tab – cohort-based analysis by origination quarter.

Shows default rate curves and metric trend charts for quarterly
origination cohorts with configurable analysis type and metric selection.
"""

from __future__ import annotations

from dash import html, dcc
import pandas as pd
import plotly.graph_objs as go

from ..tabs.registry import BaseTab, TabContext, register_tab


class VintageAnalysisTab(BaseTab):
    id = "vintage-analysis"
    label = "Vintage Analysis"
    order = 50

    # ── Sidebar ─────────────────────────────────────────────────────────────

    def render_sidebar(self, ctx: TabContext):
        return _create_vintage_analysis_sidebar(
            ctx.selected_portfolio, ctx.facilities_df,
            ctx.portfolios, ctx.selected_portfolio,
        )

    # ── Content ─────────────────────────────────────────────────────────────

    def render_content(self, ctx: TabContext):
        return _create_vintage_analysis_content(ctx.selected_portfolio)


register_tab(VintageAnalysisTab())


# =============================================================================
# Private rendering helpers
# =============================================================================


def _create_vintage_analysis_sidebar(selected_portfolio, facilities_df, portfolios, default_portfolio):
    """Create the vintage analysis sidebar with quarterly cohort controls"""
    
    facilities_df = facilities_df.copy()
    facilities_df['origination_date'] = pd.to_datetime(facilities_df['origination_date'])
    
    quarterly_options = []
    unique_dates = facilities_df['origination_date'].dropna().unique()
    
    for date in sorted(unique_dates):
        date_ts = pd.Timestamp(date)
        quarter_label = f"{date_ts.year}Q{date_ts.quarter}"
        if quarter_label not in [opt['label'] for opt in quarterly_options]:
            quarterly_options.append({'label': quarter_label, 'value': quarter_label})
    
    default_quarters = [opt['value'] for opt in quarterly_options[-3:]] if len(quarterly_options) >= 3 else [opt['value'] for opt in quarterly_options]
    
    return html.Section([
        html.Header([
            html.H2("Vintage Analysis", className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700 flex items-center justify-between"),
        html.Div([
            # Portfolio Selection
            html.Div([
                html.Label("Portfolio:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='vintage-portfolio-dropdown',
                    options=[{'label': portfolio, 'value': portfolio} for portfolio in portfolios.keys()],
                    value=selected_portfolio or default_portfolio,
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-3"),
            
            # Analysis Type Selection
            html.Div([
                html.Label("Analysis Type:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='vintage-analysis-type',
                    options=[
                        {'label': 'Default Rates', 'value': 'default_rates'},
                        {'label': 'Metric Trend', 'value': 'metric_trend'}
                    ],
                    value='default_rates',
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-3"),
            
            # Metric Selection (conditional)
            html.Div([
                html.Label("Metric:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='vintage-metric-dropdown',
                    options=[],
                    value=None,
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-3", id='vintage-metric-selector', style={'display': 'none'}),
            
            # Quarterly Cohort Selection
            html.Div([
                html.Label("Select Quarterly Cohorts:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                dcc.Dropdown(
                    id='vintage-vintage-quarters',
                    options=quarterly_options,
                    value=default_quarters,
                    multi=True,
                    className="text-xs",
                    style={"fontSize": "12px"}
                )
            ], className="mb-3")
            
        ], className="p-4 flex-1 overflow-auto")
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden flex flex-col min-h-[640px]")


def _create_vintage_analysis_content(selected_portfolio):
    """Create the vintage analysis chart content area"""
    return html.Div([
        html.Div([
            dcc.Graph(id='vintage-analysis-chart', config={'displayModeBar': False})
        ], className="chart-card", style={"marginBottom": "20px"}),
    ], className="main-content")


def create_quarterly_cohort_chart(data, selected_quarters, analysis_type='default_rates', metric=None):
    """Create quarterly cohort chart for default rates or metric trends.
    
    Note: Public because it's called from app.py callbacks.
    """
    fig = go.Figure()
    colors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
    
    data = data.copy()
    data['origination_date'] = pd.to_datetime(data['origination_date'])
    data['reporting_date'] = pd.to_datetime(data['reporting_date'])
    
    if analysis_type == 'metric_trend':
        return _create_metric_trend_chart(fig, data, selected_quarters, metric, colors)
    else:
        return _create_default_rates_chart(fig, data, selected_quarters, colors)


def _create_metric_trend_chart(fig, data, selected_quarters, metric, colors):
    """Create metric trend chart for quarterly cohorts"""
    
    actual_max_quarters = 0
    
    for i, quarter in enumerate(selected_quarters):
        year = int(quarter[:4])
        q = int(quarter[5:])
        
        if q == 4:
            quarter_end = pd.Timestamp(year=year+1, month=1, day=1) - pd.Timedelta(days=1)
        else:
            quarter_end = pd.Timestamp(year=year, month=q*3+1, day=1) - pd.Timedelta(days=1)
        
        max_reporting_date = data['reporting_date'].max()
        cohort_max_quarters = ((max_reporting_date.year - year) * 4 + 
                              (max_reporting_date.quarter - q)) + 1
        cohort_max_quarters = max(1, min(cohort_max_quarters, 20))
        actual_max_quarters = max(actual_max_quarters, cohort_max_quarters)
        
        trailing_start_year = year
        trailing_start_q = q - 3
        
        while trailing_start_q <= 0:
            trailing_start_q += 4
            trailing_start_year -= 1
        
        trailing_start = pd.Timestamp(year=trailing_start_year, month=(trailing_start_q-1)*3+1, day=1)
        
        cohort_data = data[
            (data['origination_date'] >= trailing_start) & 
            (data['origination_date'] <= quarter_end)
        ]
        
        if len(cohort_data) == 0:
            continue
            
        cohort_obligors = cohort_data[cohort_data['obligor_rating'] < 17]['obligor_name'].unique()
        cohort_size = len(cohort_obligors)
        
        if cohort_size == 0:
            continue
        
        cohort_quarters = min(cohort_max_quarters, actual_max_quarters)
        quarters_since_orig = list(range(cohort_quarters))
        metric_values = []
        
        for q_idx in range(cohort_quarters):
            target_year = year
            target_q = q + q_idx
            
            while target_q > 4:
                target_q -= 4
                target_year += 1
            
            if target_q == 1:
                quarter_start = pd.Timestamp(year=target_year, month=1, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=3, day=31)
            elif target_q == 2:
                quarter_start = pd.Timestamp(year=target_year, month=4, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=6, day=30)
            elif target_q == 3:
                quarter_start = pd.Timestamp(year=target_year, month=7, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=9, day=30)
            else:
                quarter_start = pd.Timestamp(year=target_year, month=10, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=12, day=31)
            
            quarter_data = data[
                (data['obligor_name'].isin(cohort_obligors)) &
                (data['reporting_date'] >= quarter_start) &
                (data['reporting_date'] <= quarter_end_target) &
                (data['obligor_rating'] < 17)
            ]
            
            if len(quarter_data) > 0 and metric in quarter_data.columns:
                metric_avg = quarter_data[metric].mean()
                metric_values.append(metric_avg)
            else:
                metric_values.append(None)
        
        plot_quarters = list(range(cohort_quarters))
        plot_values = [value if value is not None else None for value in metric_values]
        
        if any(v is not None for v in plot_values):
            fig.add_trace(go.Scatter(
                x=plot_quarters,
                y=plot_values,
                mode='lines+markers',
                name=f'{quarter} (n={cohort_size})',
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(color=colors[i % len(colors)], size=6),
                hovertemplate=f'<b>{quarter}</b><br>' +
                            'Quarters Since Cohort: %{x}<br>' +
                            f'{metric.replace("_", " ").title()}: %{{y:.2f}}<br>' +
                            f'Cohort Size: {cohort_size}<extra></extra>'
            ))
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=40, r=20, t=20, b=100),
        font=dict(size=12, color='rgba(255,255,255,0.7)'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        autosize=True,
        hovermode='x unified',
        xaxis=dict(
            title="Quarters Since Cohort Quarter",
            tickmode='linear',
            tick0=0,
            dtick=1,
            range=[0, max(1, actual_max_quarters-1)],
            showgrid=False,
            color='rgba(255,255,255,0.5)'
        ),
        yaxis=dict(
            title=f"{metric.replace('_', ' ').title()}" if metric else "Metric Value",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.06)',
            color='rgba(255,255,255,0.5)'
        )
    )
    
    return fig


def _create_default_rates_chart(fig, data, selected_quarters, colors):
    """Create default rates chart for quarterly cohorts"""
    
    actual_max_quarters = 0
    
    for i, quarter in enumerate(selected_quarters):
        year = int(quarter[:4])
        q = int(quarter[5:])
        
        if q == 4:
            quarter_end = pd.Timestamp(year=year+1, month=1, day=1) - pd.Timedelta(days=1)
        else:
            quarter_end = pd.Timestamp(year=year, month=q*3+1, day=1) - pd.Timedelta(days=1)
        
        max_reporting_date = data['reporting_date'].max()
        cohort_max_quarters = ((max_reporting_date.year - year) * 4 + 
                              (max_reporting_date.quarter - q)) + 1
        cohort_max_quarters = max(1, min(cohort_max_quarters, 20))
        actual_max_quarters = max(actual_max_quarters, cohort_max_quarters)
        
        trailing_start_year = year
        trailing_start_q = q - 3
        
        while trailing_start_q <= 0:
            trailing_start_q += 4
            trailing_start_year -= 1
        
        trailing_start = pd.Timestamp(year=trailing_start_year, month=(trailing_start_q-1)*3+1, day=1)
        
        cohort_data = data[
            (data['origination_date'] >= trailing_start) & 
            (data['origination_date'] <= quarter_end)
        ]
        
        if len(cohort_data) == 0:
            continue
        
        cohort_obligors = cohort_data[cohort_data['obligor_rating'] < 17]['obligor_name'].unique()
        cohort_size = len(cohort_obligors)
        
        if cohort_size == 0:
            continue
        
        cohort_quarters = min(cohort_max_quarters, actual_max_quarters)
        quarters_since_orig = list(range(cohort_quarters))
        default_rates = []
        
        for q_idx in range(cohort_quarters):
            target_year = year
            target_q = q + q_idx
            
            while target_q > 4:
                target_q -= 4
                target_year += 1
            
            if target_q == 1:
                quarter_start = pd.Timestamp(year=target_year, month=1, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=3, day=31)
            elif target_q == 2:
                quarter_start = pd.Timestamp(year=target_year, month=4, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=6, day=30)
            elif target_q == 3:
                quarter_start = pd.Timestamp(year=target_year, month=7, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=9, day=30)
            else:
                quarter_start = pd.Timestamp(year=target_year, month=10, day=1)
                quarter_end_target = pd.Timestamp(year=target_year, month=12, day=31)
            
            quarter_data = data[
                (data['obligor_name'].isin(cohort_obligors)) &
                (data['reporting_date'] >= quarter_start) &
                (data['reporting_date'] <= quarter_end_target)
            ]
            
            if len(quarter_data) > 0:
                defaults = len(quarter_data[quarter_data['obligor_rating'] == 17]['obligor_name'].unique())
                default_rate = (defaults / cohort_size) * 100
                default_rates.append(default_rate)
            else:
                default_rates.append(0)
        
        fig.add_trace(go.Scatter(
            x=quarters_since_orig,
            y=default_rates,
            mode='lines+markers',
            name=f'{quarter} (n={cohort_size})',
            line=dict(color=colors[i % len(colors)], width=3),
            marker=dict(color=colors[i % len(colors)], size=6),
            hovertemplate=f'<b>{quarter}</b><br>' +
                        'Quarters Since Cohort: %{x}<br>' +
                        'Default Rate: %{y:.2f}%<br>' +
                        f'Cohort Size: {cohort_size}<extra></extra>'
        ))
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=40, r=20, t=20, b=100),
        font=dict(size=12, color='rgba(255,255,255,0.7)'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        autosize=True,
        hovermode='x unified',
        xaxis=dict(
            title="Quarters Since Cohort Quarter",
            tickmode='linear',
            tick0=0,
            dtick=1,
            range=[0, max(1, actual_max_quarters-1)],
            showgrid=False,
            color='rgba(255,255,255,0.5)'
        ),
        yaxis=dict(
            title="Cumulative Default Rate (%)",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.06)',
            color='rgba(255,255,255,0.5)'
        )
    )
    
    return fig
