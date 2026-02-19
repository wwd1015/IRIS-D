"""
Role-gated tabs – SIR Analysis, Location Analysis, Financial Projection, Model Backtesting.

These are role-specific tabs that only appear for certain user roles.
Each is a clean placeholder ready for future implementation.
"""

from dash import html
from ..tabs.registry import BaseTab, TabContext, register_tab


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


def _placeholder_sidebar(title: str, ctx: TabContext, extra_text: str = ""):
    """Shared helper for placeholder tab sidebars."""
    return html.Section([
        html.Header([
            html.H2(title, className="text-sm font-semibold")
        ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700 flex items-center justify-between"),
        html.Div([
            html.Div([
                html.Label("Portfolio:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                html.Div(ctx.selected_portfolio, className="text-sm font-semibold text-primary-400 mb-4"),
            ]),
            html.P(extra_text or f"Configure {title.lower()} parameters.",
                   className="text-xs text-ink-500 dark:text-slate-400")
        ], className="p-4 flex-1 overflow-auto")
    ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden flex flex-col min-h-[640px]")


# ── SIR Analysis ───────────────────────────────────────────────────────────────

class SIRAnalysisTab(BaseTab):
    id = "sir-analysis"
    label = "SIR Analysis"
    order = 60
    required_role = "SAG"

    def render_sidebar(self, ctx):
        return _placeholder_sidebar("SIR Analysis", ctx, "Special Interest Rate risk analysis.")

    def render_content(self, ctx):
        return _placeholder_content("📐", "SIR Analysis", "Special Interest Rate Analysis")


# ── Location Analysis ─────────────────────────────────────────────────────────

class LocationAnalysisTab(BaseTab):
    id = "location-analysis"
    label = "Location Analysis"
    order = 70
    required_role = "CRE SCO"

    def render_sidebar(self, ctx):
        return _placeholder_sidebar("Location Analysis", ctx, "Geographic analysis for CRE portfolios.")

    def render_content(self, ctx):
        return _placeholder_content("🗺️", "Location Analysis", "Geographic distribution and concentration analysis")


# ── Financial Projection ──────────────────────────────────────────────────────

class FinancialProjectionTab(BaseTab):
    id = "financial-projection"
    label = "Financial Projection"
    order = 80
    required_role = "Corp SCO"

    def render_sidebar(self, ctx):
        return _placeholder_sidebar("Financial Projection", ctx, "Forecast future portfolio metrics.")

    def render_content(self, ctx):
        return _placeholder_content("🔮", "Financial Projection", "Financial forecasting and projection analysis")


# ── Model Backtesting ─────────────────────────────────────────────────────────

class ModelBacktestingTab(BaseTab):
    id = "model-backtesting"
    label = "Model Backtesting"
    order = 90
    required_role = "BA"

    def render_sidebar(self, ctx):
        return _placeholder_sidebar("Model Backtesting", ctx, "Validate model performance against historical data.")

    def render_content(self, ctx):
        return _placeholder_content("🧪", "Model Backtesting", "Model validation and backtesting analysis")


# Auto-register all
register_tab(SIRAnalysisTab())
register_tab(LocationAnalysisTab())
register_tab(FinancialProjectionTab())
register_tab(ModelBacktestingTab())
