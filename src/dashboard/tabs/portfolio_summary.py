"""
Portfolio Summary tab – the default landing page.

Shows high-level portfolio metrics, charts, and a positions panel.
This is a fully-implemented tab that serves as a reference for building others.
"""

from dash import html, callback, Input, Output, no_update
from ..tabs.registry import BaseTab, TabContext, register_tab
from ..components.portfolio_summary import create_main_content, create_positions_panel
from ..components.portfolio_management import create_portfolio_sidebar


class PortfolioSummaryTab(BaseTab):
    id = "portfolio-summary"
    label = "Portfolio Summary"
    order = 10
    grid_class = "grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)_340px] gap-4 items-stretch"

    def render_sidebar(self, ctx: TabContext):
        return create_portfolio_sidebar(ctx.selected_portfolio, ctx.available_portfolios)

    def render_content(self, ctx: TabContext):
        # For this tab, "content" is really two panels: main + positions
        return html.Div([
            html.Div(
                id="main-content-container",
                children=create_main_content(
                    ctx.selected_portfolio,
                    ctx.get_filtered_data,
                    ctx.facilities_df,
                    ctx.portfolios,
                ),
            ),
            html.Div(
                id="positions-panel-container",
                children=create_positions_panel(
                    ctx.selected_portfolio,
                    ctx.facilities_df,
                    ctx.portfolios,
                    ctx.get_filtered_data,
                ),
            ),
        ])

    def render(self, ctx: TabContext):
        """Custom 3-column layout for summary."""
        sidebar = self.render_sidebar(ctx)
        content = self.render_content(ctx)
        return html.Div(
            [sidebar, *content.children],
            className=self.grid_class,
        )

    def register_callbacks(self, app):
        @callback(
            Output("main-content-container", "children"),
            Input("universal-portfolio-dropdown", "value"),
            prevent_initial_call=True,
        )
        def update_main_content(selected_portfolio):
            from ..app import portfolios, latest_facilities, facilities_df, get_filtered_data as _gfd
            if not selected_portfolio:
                return no_update
            gfd = lambda p: _gfd(p, portfolios, latest_facilities)
            return create_main_content(selected_portfolio, gfd, facilities_df, portfolios)

        @callback(
            Output("positions-panel-container", "children"),
            Input("universal-portfolio-dropdown", "value"),
            prevent_initial_call=True,
        )
        def update_positions_panel(selected_portfolio):
            from ..app import portfolios, facilities_df, latest_facilities, get_filtered_data as _gfd
            if not selected_portfolio:
                return no_update
            gfd = lambda p: _gfd(p, portfolios, latest_facilities)
            return create_positions_panel(selected_portfolio, facilities_df, portfolios, gfd)


# Auto-register
register_tab(PortfolioSummaryTab())
