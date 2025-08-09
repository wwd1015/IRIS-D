from dash import Dash, html, dcc, dash_table
from dash.dependencies import Input, Output
import pandas as pd

"""
app.py — Dash app styled to closely mimic the standalone Financial Trends HTML.
- Custom CSS (no Tailwind) injected via index_string using the same tokens as the static mock.
- Top bar + tabs, filter toolbar, and a card with a wide DataTable.
- Dark-mode toggle can be added later if needed.

Run:
  pip install dash pandas
  python app.py
"""

# ------------------------ Sample Data: Financial Trends ----------------------
ft_rows = [
    {"industry": "Moody's Industry: Automotive", "issuer": "", "analyst": "", "rev_21": "", "rev_20": "", "rev_yoy": "", "gp_21": "", "gp_20": "", "gp_yoy": "", "ebitda_21": "", "ebitda_20": "", "ebitda_yoy": "", "adj_21": "", "adj_20": "", "adj_yoy": "", "lev_21": "", "lev_20": "", "is_group": True},
    {"industry": "Automotive", "issuer": "Allison Transmission Inc", "analyst": "AA", "rev_21": 22206, "rev_20": 19268, "rev_yoy": 0.147, "gp_21": 8300, "gp_20": 7170, "gp_yoy": 0.158, "ebitda_21": 5579, "ebitda_20": 4786, "ebitda_yoy": 0.166, "adj_21": 4629, "adj_20": 5088, "adj_yoy": -0.090, "lev_21": "0.0x", "lev_20": "0.0x", "is_group": False},

    {"industry": "Moody's Industry: Beverage, Food, & Tobacco", "issuer": "", "analyst": "", "rev_21": "", "rev_20": "", "rev_yoy": "", "gp_21": "", "gp_20": "", "gp_yoy": "", "ebitda_21": "", "ebitda_20": "", "ebitda_yoy": "", "adj_21": "", "adj_20": "", "adj_yoy": "", "lev_21": "", "lev_20": "", "is_group": True},
    {"industry": "Beverage, Food, & Tobacco", "issuer": "Dollar Tree Inc", "analyst": "AA", "rev_21": 6678, "rev_20": 8192, "rev_yoy": -0.206, "gp_21": 2304, "gp_20": 2019, "gp_yoy": 0.141, "ebitda_21": 216, "ebitda_20": 732, "ebitda_yoy": -0.704, "adj_21": 246, "adj_20": 732, "adj_yoy": -0.664, "lev_21": "4.0x", "lev_20": "2.3x", "is_group": False},
    {"industry": "Beverage, Food, & Tobacco", "issuer": "J.C. Penney", "analyst": "AA", "rev_21": 9468, "rev_20": 2033, "rev_yoy": 2.759, "gp_21": 7377, "gp_20": 2629, "gp_yoy": 1.810, "ebitda_21": 0, "ebitda_20": 0, "ebitda_yoy": 0.0, "adj_21": 0, "adj_20": 0, "adj_yoy": 0.0, "lev_21": "1.7x", "lev_20": "2.3x", "is_group": False},

    {"industry": "Moody's Industry: Chemicals, Plastics, & Rubber", "issuer": "", "analyst": "", "rev_21": "", "rev_20": "", "rev_yoy": "", "gp_21": "", "gp_20": "", "gp_yoy": "", "ebitda_21": "", "ebitda_20": "", "ebitda_yoy": "", "adj_21": "", "adj_20": "", "adj_yoy": "", "lev_21": "", "lev_20": "", "is_group": True},
    {"industry": "Chemicals, Plastics, & Rubber", "issuer": "DuPont Performance Coatings Inc.", "analyst": "AA", "rev_21": 43238, "rev_20": 51471, "rev_yoy": -0.161, "gp_21": 12256, "gp_20": 14478, "gp_yoy": -0.153, "ebitda_21": 7397, "ebitda_20": 9194, "ebitda_yoy": -0.195, "adj_21": 8647, "adj_20": 0, "adj_yoy": 0.0, "lev_21": "1.4x", "lev_20": "1.9x", "is_group": False},
]
ft_df = pd.DataFrame(ft_rows)

FT_COLUMNS = [
    {"name": "Issuer", "id": "issuer"},
    {"name": "Deal Team Analyst", "id": "analyst"},
    {"name": "Rev Jan 2021", "id": "rev_21", "type": "numeric", "format": {"specifier": ","}},
    {"name": "Rev Jan 2020", "id": "rev_20", "type": "numeric", "format": {"specifier": ","}},
    {"name": "Rev Jan 2021 vs Jan 2020", "id": "rev_yoy", "type": "numeric", "format": {"specifier": "+.1%"}},
    {"name": "GP Jan 2021", "id": "gp_21", "type": "numeric", "format": {"specifier": ","}},
    {"name": "GP Jan 2020", "id": "gp_20", "type": "numeric", "format": {"specifier": ","}},
    {"name": "GP Jan 2021 vs Jan 2020", "id": "gp_yoy", "type": "numeric", "format": {"specifier": "+.1%"}},
    {"name": "EBITDA Jan 2021", "id": "ebitda_21", "type": "numeric", "format": {"specifier": ","}},
    {"name": "EBITDA Jan 2020", "id": "ebitda_20", "type": "numeric", "format": {"specifier": ","}},
    {"name": "EBITDA Jan 2021 vs Jan 2020", "id": "ebitda_yoy", "type": "numeric", "format": {"specifier": "+.1%"}},
    {"name": "Adj EBITDA Jan 2021", "id": "adj_21", "type": "numeric", "format": {"specifier": ","}},
    {"name": "Adj EBITDA Jan 2020", "id": "adj_20", "type": "numeric", "format": {"specifier": ","}},
    {"name": "Adj EBITDA Jan 2021 vs Jan 2020", "id": "adj_yoy", "type": "numeric", "format": {"specifier": "+.1%"}},
    {"name": "Total Lev Jan 2021", "id": "lev_21"},
    {"name": "Total Lev Jan 2020", "id": "lev_20"},
]

# ----------------------------- App Init -------------------------------------
app = Dash(__name__)
server = app.server

# Inject custom CSS matching the static HTML
app.index_string = """
<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'/>
  <meta name='viewport' content='width=device-width, initial-scale=1'/>
  <title>Portfolio Management (DL) – Financial Trends</title>
  <style>
    :root{ --bg:#fbfcfe; --panel:#ffffff; --ink-900:#0f172a; --ink-800:#1e293b; --ink-700:#334155; --ink-600:#475569; --ink-500:#64748b; --line:#e6ebf2; --line-soft:#f1f5f9; --accent:#4f46e5; --badge:#fbbf24; --pos:#0f9d58; --neg:#d93025; --muted:#94a3b8; --shadow:0 2px 8px rgba(15,23,42,.06);} 
    html,body{height:100%} body{margin:0;background:var(--bg);color:var(--ink-800);font:13px/1.4 "Inter","Segoe UI",Roboto,Helvetica,Arial,sans-serif} .wrap{max-width:1600px;margin:0 auto}
    .appbar{position:sticky;top:0;z-index:50;background:#fff;backdrop-filter:saturate(180%) blur(6px);box-shadow:0 1px 0 var(--line)} .row{display:flex;align-items:center;gap:10px} .between{justify-content:space-between} .app-title{color:var(--ink-700)} .chip{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:14px;padding:2px 8px;color:var(--ink-600);background:#fff} .dev{background:var(--badge);color:#fff;border-radius:4px;font-weight:700;font-size:10px;padding:2px 6px}
    .tabs{display:flex;gap:6px;overflow:auto;padding:10px 0;color:var(--ink-600)} .tab{padding:6px 10px;border-radius:6px;white-space:nowrap} .tab.active{background:var(--ink-900);color:#fff}
    .toolbar{background:#fff;border-top:1px solid var(--line);border-bottom:1px solid var(--line);} .toolbar .wrap{padding:10px 16px} .filter{display:flex;gap:8px;flex-wrap:wrap}
    .select{display:flex;align-items:center;gap:8px;border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:6px 10px;min-width:220px} .select small{color:var(--muted);font-size:11px}
    .card{background:#fff;border:1px solid var(--line);box-shadow:var(--shadow);border-radius:12px;overflow:hidden} .card-h{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--line-soft)} .card-h .title{font-weight:600;color:var(--ink-700)}
    .table-wrap{overflow:auto} table{border-collapse:separate;border-spacing:0;min-width:1200px;width:100%}
    thead th{position:sticky;top:0;background:#f8fafc;border-bottom:1px solid var(--line);text-align:left;color:var(--ink-600);font-weight:600;padding:10px 12px}
    .footer{display:flex;justify-content:space-between;align-items:center;color:var(--ink-600);padding:10px 12px;border-top:1px solid var(--line);background:#fff;border-radius:0 0 12px 12px}
    .px{padding-left:16px;padding-right:16px} .py{padding-top:10px;padding-bottom:10px} .avatar{width:28px;height:28px;border-radius:50%;background:#cbd5e1} .logo{width:22px;height:22px;border-radius:6px;background:var(--accent)} .icon{width:16px;height:16px;display:inline-block;background:linear-gradient(180deg,#cbd5e1,#94a3b8);border-radius:4px} .right{margin-left:auto} .muted{color:var(--muted)}
    ::-webkit-scrollbar{height:8px;width:8px}::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:8px}
  </style>
  {%favicon%}
  {%css%}
</head>
<body>
  <div id='root'>{%app_entry%}</div>
  <footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
"""

# ----------------------------- UI ------------------------------------------

def app_bar():
    return html.Header([
        html.Div([
            html.Div([
                html.Div(className="logo"),
                html.Div("Portfolio Management (DL)", className="app-title"),
                html.Div(className="icon", **{"title":"Dropdown"}),
                html.Span("DEV", className="dev"),
                html.Span("Direct Lending", className="chip"),
                html.Span("Loan Funding", className="chip"),
                html.Span("MORE", className="chip"),
            ], className="row"),
            html.Div([
                html.Div(className="icon", **{"title":"Search"}),
                html.Div(className="icon", **{"title":"Notifications"}),
                html.Div(className="avatar"),
            ], className="row")
        ], className="row between wrap px py"),
        html.Nav([
            html.Span("Portfolio Summary (DL)", className="tab"),
            html.Span("Holdings (DL)", className="tab"),
            html.Span("Deal Pipeline (DL)", className="tab"),
            html.Span("Credits (DL)", className="tab"),
            html.Span("Funding Transactions", className="tab"),
            html.Span("Deal Syndication Offering", className="tab"),
            html.Span("All Equity Investors", className="tab"),
            html.Span("All Bank Groups", className="tab"),
            html.Span("Analyst Commentary (DL)", className="tab"),
            html.Span("Financials (DL)", className="tab"),
            html.Span("Financial Trends (DL)", className="tab active"),
            html.Span("Borrowing Base", className="tab"),
            html.Span("Latest Credit Covenants", className="tab"),
            html.Span("RiskCalc", className="tab"),
            html.Span("Reports", className="tab"),
        ], className="tabs wrap")
    ], className="appbar")


def filters_bar():
    return html.Section([
        html.Div([
            html.Div([
                html.Div([html.Small("View"), html.Strong("Moody's Industry")], className="select"),
                html.Div([html.Small("Comparison 1 Time Period"), html.Strong("Prior Period")], className="select"),
                html.Div([html.Small("Comparison 1 Financial Type"), html.Strong("Monthly")], className="select"),
                html.Div([html.Small("Comparison 2 Time Period"), html.Strong("Prior Year and As of Date")], className="select"),
                html.Div([html.Small("Comparison 2 Financial Type"), html.Strong("Monthly")], className="select"),
                html.Div([html.Small("Primary Time Period"), html.Strong("Current Period")], className="select"),
                html.Div([html.Small("Compare Financial Periods"), html.Strong("Year-Start vs Year-End")], className="select"),
                html.Div("Filters are illustrative only", className="right muted"),
            ], className="filter"),
        ], className="wrap px py"),
    ], className="toolbar")


def financial_trends_table():
    return dash_table.DataTable(
        id="ft-table",
        columns=FT_COLUMNS,
        data=ft_df.to_dict("records"),
        page_size=25,
        fixed_rows={"headers": True},
        style_table={"overflowX": "auto", "maxHeight": "60vh"},
        style_header={"backgroundColor": "#f8fafc", "borderBottom": "1px solid #e6ebf2", "fontWeight": 600, "textAlign": "left", "padding": "10px 12px"},
        style_cell={"padding": "10px 12px", "whiteSpace": "nowrap", "borderBottom": "1px solid #f1f5f9", "fontFamily": "Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif", "fontSize": 13},
        style_data_conditional=[
            {"if": {"filter_query": '{is_group} = True'}, "backgroundColor": "#f1f5f9", "fontWeight": 700},
            {"if": {"filter_query": '{rev_yoy} > 0', "column_id": "rev_yoy"}, "color": "#0f9d58"},
            {"if": {"filter_query": '{gp_yoy} > 0', "column_id": "gp_yoy"}, "color": "#0f9d58"},
            {"if": {"filter_query": '{ebitda_yoy} > 0', "column_id": "ebitda_yoy"}, "color": "#0f9d58"},
            {"if": {"filter_query": '{adj_yoy} > 0', "column_id": "adj_yoy"}, "color": "#0f9d58"},
            {"if": {"filter_query": '{rev_yoy} < 0', "column_id": "rev_yoy"}, "color": "#d93025"},
            {"if": {"filter_query": '{gp_yoy} < 0', "column_id": "gp_yoy"}, "color": "#d93025"},
            {"if": {"filter_query": '{ebitda_yoy} < 0', "column_id": "ebitda_yoy"}, "color": "#d93025"},
            {"if": {"filter_query": '{adj_yoy} < 0', "column_id": "adj_yoy"}, "color": "#d93025"},
        ],
        filter_action="native",
        sort_action="native",
        style_as_list_view=True,
    )


app.layout = html.Div([
    dcc.Location(id="url"),
    app_bar(),
    filters_bar(),
    html.Main([
        html.Div([
            html.Div([
                html.Div("Financial Trends (DL)", className="title"),
                html.Div("Unit: Typical Type = Monthly", className="muted"),
            ], className="card-h"),
            html.Div(financial_trends_table(), className="table-wrap"),
            html.Div([
                html.Div("1 of 124"),
                html.Div("100 per page"),
            ], className="footer"),
        ], className="card"),
    ], className="wrap", style={"padding":"14px 16px 32px"}),
])


if __name__ == "__main__":
    app.run(debug=True, port=8051)
