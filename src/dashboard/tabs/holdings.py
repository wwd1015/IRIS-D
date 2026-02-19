"""
Holdings tab – detailed facility-level data view with filters.

Shows filterable table of individual facilities with expandable rows
for time-series data.
"""

from dash import html, dcc
from ..tabs.registry import BaseTab, TabContext, register_tab


class HoldingsTab(BaseTab):
    id = "holdings"
    label = "Holdings"
    order = 20

    def render_sidebar(self, ctx: TabContext):
        return html.Section([
            html.Header([
                html.H2("Holdings", className="text-sm font-semibold")
            ], className="px-4 py-3 border-b border-slate-200 dark:border-ink-700 flex items-center justify-between"),
            html.Div([
                html.Div([
                    html.Label("Portfolio:", className="block text-xs font-medium mb-1 text-ink-600 dark:text-slate-300"),
                    html.Div(ctx.selected_portfolio, className="text-sm font-semibold text-primary-400 mb-4"),
                ]),
                html.P("Filter and explore individual facility records.", 
                       className="text-xs text-ink-500 dark:text-slate-400")
            ], className="p-4 flex-1 overflow-auto")
        ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden flex flex-col min-h-[640px]")

    def render_content(self, ctx: TabContext):
        return html.Div([
            html.Div([
                html.Div([
                    html.H3("Holdings", className="text-sm font-semibold text-ink-700 dark:text-slate-300"),
                    html.Div("Facility-level detail view", className="text-xs text-ink-500 dark:text-slate-400")
                ], className="flex-1"),
            ], className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-ink-700"),
            html.Div([
                html.Div([
                    html.Div("🏗️", style={"fontSize": "48px", "marginBottom": "16px"}),
                    html.H4("Ready for Implementation", className="text-lg font-medium text-ink-600 dark:text-slate-300 mb-2"),
                    html.P("This tab's content can be implemented by adding rendering logic to the HoldingsTab class.",
                          className="text-ink-500 dark:text-slate-400 text-sm max-w-md"),
                    html.P("See src/dashboard/tabs/portfolio_summary.py for a reference implementation.",
                          className="text-ink-400 dark:text-slate-500 text-xs mt-2 font-mono")
                ], className="text-center py-20")
            ], className="p-6")
        ], className="bg-white dark:bg-ink-800 rounded-xl shadow-soft border border-slate-200 dark:border-ink-700 overflow-hidden main-content")


register_tab(HoldingsTab())
