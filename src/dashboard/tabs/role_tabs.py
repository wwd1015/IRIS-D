"""
Role-gated tabs – SIR Analysis, Location Analysis, Financial Projection, Model Backtesting.

These are role-specific tabs that only appear for certain user roles.
Location Analysis has full CRE map implementation; others are placeholders.
"""

from __future__ import annotations

from dash import html, dcc
import plotly.graph_objects as go
import pandas as pd
import sqlite3
from ..tabs.registry import BaseTab, register_tab


def _placeholder_content(icon: str, title: str, description: str):
    """Shared helper for placeholder tab content."""
    return html.Div([
        html.Div([
            html.H3(title, className="text-sm font-semibold text-ink-700 dark:text-slate-300"),
            html.Div(description, className="text-xs text-ink-500 dark:text-slate-400")
        ], className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-ink-700"),
        html.Div([
            html.Div([
                html.Div(icon, style={"fontSize": "48px", "marginBottom": "16px"}),
                html.H4("Ready for Implementation", className="text-lg font-medium text-ink-600 dark:text-slate-300 mb-2"),
                html.P(description, className="text-ink-500 dark:text-slate-400 text-sm max-w-md"),
                html.P("Subclass BaseTab in src/dashboard/tabs/ to implement.",
                      className="text-ink-400 dark:text-slate-500 text-xs mt-2 font-mono")
            ], className="text-center py-20")
        ], className="p-6")
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden main-content")



# ── SIR Analysis ───────────────────────────────────────────────────────────────

class SIRAnalysisTab(BaseTab):
    id = "sir-analysis"
    label = "SIR Analysis"
    order = 60
    required_roles = ["SAG"]

    def render_content(self, ctx):
        return _placeholder_content("📐", "SIR Analysis", "Special Interest Rate Analysis")


# ── Location Analysis (fully implemented) ─────────────────────────────────────

class LocationAnalysisTab(BaseTab):
    id = "location-analysis"
    label = "Location Analysis"
    order = 70
    required_roles = ["CRE SCO"]

    def get_toolbar_controls(self, ctx):
        from ..components.toolbar import DropdownControl
        cre_portfolios = {k: v for k, v in ctx.portfolios.items()
                         if k == "CRE" or (v and v.get("lob") == "CRE")}
        opts = [{"label": p, "value": p} for p in cre_portfolios]
        default = ctx.selected_portfolio if ctx.selected_portfolio in cre_portfolios else (opts[0]["value"] if opts else None)
        return [
            DropdownControl(
                id="location-portfolio-dropdown", label="CRE Portfolio",
                options=opts, value=default, order=10, width="min-w-[200px]",
            ),
        ]

    def render_content(self, ctx):
        return _create_location_analysis_content(ctx.selected_portfolio, ctx.portfolios)


# ── Financial Projection ──────────────────────────────────────────────────────

class FinancialProjectionTab(BaseTab):
    id = "financial-projection"
    label = "Financial Projection"
    order = 80
    required_roles = ["Corp SCO"]

    def render_content(self, ctx):
        return _placeholder_content("🔮", "Financial Projection", "Financial forecasting and projection analysis")


# ── Model Backtesting ─────────────────────────────────────────────────────────

class ModelBacktestingTab(BaseTab):
    id = "model-backtesting"
    label = "Model Backtesting"
    order = 90
    required_roles = ["BA"]

    def render_content(self, ctx):
        return _placeholder_content("🧪", "Model Backtesting", "Model validation and backtesting analysis")


# Auto-register all
register_tab(SIRAnalysisTab())
register_tab(LocationAnalysisTab())
register_tab(FinancialProjectionTab())
register_tab(ModelBacktestingTab())


# =============================================================================
# Location Analysis – private rendering helpers
# (merged from components/location_analysis.py)
# =============================================================================



def _get_cre_location_data(selected_portfolio, portfolios):
    """Get CRE loan data with coordinates for mapping"""
    print(f"DEBUG: Loading location data for portfolio: {selected_portfolio}")
    print(f"DEBUG: Available portfolios: {list(portfolios.keys())}")
    
    conn = sqlite3.connect('data/bank_risk.db')
    
    try:
        query = """
            SELECT facility_id, obligor_name, balance, msa, latitude, longitude, 
                   cre_property_type, dscr, ltv, property_value
            FROM raw_facilities 
            WHERE lob = 'CRE' 
            AND latitude IS NOT NULL 
            AND longitude IS NOT NULL
        """
        
        params = []
        
        if selected_portfolio != 'CRE' and selected_portfolio in portfolios:
            portfolio_config = portfolios[selected_portfolio]
            print(f"DEBUG: Portfolio config for {selected_portfolio}: {portfolio_config}")
            if portfolio_config.get('property_type'):
                query += " AND cre_property_type IN ({})".format(','.join(['?' for _ in portfolio_config['property_type']]))
                params.extend(portfolio_config['property_type'])
            if portfolio_config.get('obligors'):
                query += " AND obligor_name IN ({})".format(','.join(['?' for _ in portfolio_config['obligors']]))
                params.extend(portfolio_config['obligors'])
        
        print(f"DEBUG: Executing query: {query}")
        print(f"DEBUG: Query params: {params}")
        
        df = pd.read_sql_query(query, conn, params=params)
        print(f"DEBUG: Loaded {len(df)} CRE loans with coordinates")
        return df
        
    except Exception as e:
        print(f"ERROR: Error loading CRE location data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()
    finally:
        conn.close()


def _create_location_map(selected_portfolio, portfolios):
    """Create interactive map with CRE loan locations"""
    df = _get_cre_location_data(selected_portfolio, portfolios)
    
    if df.empty:
        return go.Figure().add_annotation(
            text="No CRE loan data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font_size=16
        )
    
    hover_text = []
    for _, row in df.iterrows():
        hover_text.append(
            f"<b>{row['obligor_name']}</b><br>"
            f"Balance: ${row['balance']:,.0f}<br>"
            f"MSA: {row['msa']}<br>"
            f"Property Type: {row['cre_property_type']}<br>"
            f"Property Value: ${row['property_value']:,.0f}<br>"
            f"LTV: {row['ltv']:.1%}<br>"
            f"DSCR: {row['dscr']:.2f}"
        )
    
    fig = go.Figure()
    
    balance_normalized = ((df['balance'] - df['balance'].min()) / 
                         (df['balance'].max() - df['balance'].min()) * 45 + 5)
    
    fig.add_trace(go.Scattermapbox(
        lat=df['latitude'],
        lon=df['longitude'],
        mode='markers',
        marker=dict(
            size=balance_normalized,
            color=df['balance'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(
                title=dict(text="Loan Balance ($)", font=dict(size=10)),
                tickfont=dict(size=9),
                tickformat='$,.0f',
                len=0.3,
                thickness=10,
                x=0.5,
                xanchor='center',
                y=0.02,
                yanchor='bottom',
                orientation='h'
            ),
            opacity=0.7,
            sizemode='diameter'
        ),
        text=hover_text,
        hovertemplate='%{text}<extra></extra>',
        name='CRE Loans'
    ))
    
    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            center=dict(lat=39.5, lon=-98.35),
            zoom=3
        ),
        height=600,
        margin=dict(r=0, t=0, l=0, b=0),
        showlegend=False
    )
    
    return fig


def _create_location_analysis_content(selected_portfolio, portfolios=None):
    """Create Location Analysis content with interactive map"""
    if portfolios is None:
        portfolios = {}
        
    df = _get_cre_location_data(selected_portfolio, portfolios)
    
    return html.Div([
        
        # Statistics - Value Box Style
        html.Div([
            html.Div([
                # Total Balance
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span("💰", className="text-2xl"),
                            html.Div([
                                html.H3(f"${df['balance'].sum():,.0f}", className="text-xl font-bold text-white mb-0"),
                                html.P("Total Balance", className="text-sm text-purple-100 mb-0")
                            ], className="ml-3")
                        ], className="flex items-center")
                    ], className="p-4")
                ], className="bg-purple-500 rounded-lg shadow-md"),
                
                # Total Loans
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span("🏢", className="text-2xl"),
                            html.Div([
                                html.H3(f"{len(df)}", className="text-xl font-bold text-white mb-0"),
                                html.P("Total Loans", className="text-sm text-purple-100 mb-0")
                            ], className="ml-3")
                        ], className="flex items-center")
                    ], className="p-4")
                ], className="bg-purple-500 rounded-lg shadow-md"),
                
                # Markets
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span("🌎", className="text-2xl"),
                            html.Div([
                                html.H3(f"{df['msa'].nunique()}" if not df.empty else "0", className="text-xl font-bold text-white mb-0"),
                                html.P("Markets (MSAs)", className="text-sm text-purple-100 mb-0")
                            ], className="ml-3")
                        ], className="flex items-center")
                    ], className="p-4")
                ], className="bg-purple-500 rounded-lg shadow-md"),
                
                # Average Loan Size
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span("📊", className="text-2xl"),
                            html.Div([
                                html.H3(f"${df['balance'].mean():,.0f}" if not df.empty else "$0", className="text-xl font-bold text-white mb-0"),
                                html.P("Avg Loan Size", className="text-sm text-purple-100 mb-0")
                            ], className="ml-3")
                        ], className="flex items-center")
                    ], className="p-4")
                ], className="bg-purple-500 rounded-lg shadow-md")
                
            ], className="grid grid-cols-4 gap-4 mb-2")
        ], className="p-4 pb-2"),
        
        # Interactive Map
        html.Div([
            dcc.Graph(
                id='location-map',
                figure=_create_location_map(selected_portfolio, portfolios),
                config={'displayModeBar': True, 'scrollZoom': True}
            )
        ], className="px-4 pb-4")
        
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden main-content")
