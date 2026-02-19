# CLAUDE.md — Project Context for IRIS-D

## Project Overview

**IRIS-D** (Interactive Reporting & Insight Generation System – Dashboard) is a portfolio performance dashboard for **Corporate Banking** and **Commercial Real Estate (CRE)** portfolios. It is built with **Dash** (Plotly) and **Python**, and is designed for deployment on **Posit Connect**.

## Tech Stack

- **Framework**: Dash (Plotly) for interactive web-based dashboards
- **Language**: Python 3.8+
- **Data**: Pandas, NumPy, SQLAlchemy (SQLite backend at `data/bank_risk.db`)
- **Validation**: Pydantic
- **Config**: PyYAML
- **Styling**: Custom CSS (`assets/style.css`) — dark-themed glassmorphism design
- **Production Server**: Gunicorn
- **Build System**: setuptools via `pyproject.toml`

## Project Structure

```
IRIS-D/
├── main.py                    # Local dev entry point
├── app.py                     # Posit Connect WSGI entry point
├── pyproject.toml             # Project config & dependencies
├── requirements.txt           # Flexible deps for backward compat
├── src/
│   └── dashboard/
│       ├── app.py             # Main Dash application (callbacks, layout assembly)
│       ├── config.py          # Constants & settings (DB paths, host, port)
│       ├── auth/              # User management & role-based access
│       │   └── user_management.py
│       ├── components/        # UI tab components
│       │   ├── layout.py              # Main layout & navigation
│       │   ├── portfolio_summary.py   # Portfolio summary tab
│       │   ├── portfolio_trend.py     # Portfolio trend tab
│       │   ├── holdings.py            # Holdings tab
│       │   ├── vintage_analysis.py    # Vintage analysis tab
│       │   ├── financial_trends.py    # Financial trends tab
│       │   ├── sir_analysis.py        # SIR analysis tab
│       │   ├── location_analysis.py   # Location/map analysis tab
│       │   ├── financial_projection.py
│       │   ├── model_backtesting.py
│       │   └── portfolio_management.py
│       ├── data/              # Data loading & generation
│       │   ├── loader.py
│       │   └── db_data_generator.py
│       └── utils/             # Utility functions
├── data/
│   ├── bank_risk.db           # SQLite database (facility data)
│   ├── datatidy_config.yaml   # Data processing rules
│   └── user_profiles.json     # User preferences (auto-created)
├── assets/
│   └── style.css              # CSS styling (glassmorphism dark theme)
└── tests/
    ├── test_prototype.py
    └── integration/
        └── test_app.py
```

## How to Run

```bash
# Install (editable mode)
pip install -e .

# Run locally
python main.py
# → Runs at http://127.0.0.1:8050 by default

# Deploy to Posit Connect
rsconnect deploy dash main.py --title "Portfolio Performance Dashboard"
```

## Key Concepts

- **Portfolios**: The app manages two default portfolios (Corporate Banking, CRE). Users can also create custom portfolios filtered by LOB, industry, or property type.
- **Tabs**: The dashboard has multiple tabs — Portfolio Summary, Holdings, Financial Trends, Vintage Analysis, SIR Analysis, Location Analysis, Financial Projection, Model Backtesting, and Portfolio Management.
- **User Profiles**: Stored in `data/user_profiles.json`. Supports guest mode and named profiles with saved portfolios and custom metrics.
- **Custom Metrics**: Users can create formula-based metrics using column names (backtick syntax for spaced names, e.g., `` `free cash flow` / liquidity ``).
- **Roles**: Role-based access control — Corp SCO, CRE SCO, SAG, BA.

## Environment Variables

| Variable | Default     | Description                      |
|----------|-------------|----------------------------------|
| `HOST`   | `127.0.0.1` | Server bind address              |
| `PORT`   | `8050`      | Server port                      |
| `DEBUG`  | `False`     | Enable Dash debug mode           |

## Development Notes

- The main application logic (callbacks, layout assembly) lives in `src/dashboard/app.py` — this is a large file (~110k bytes).
- CSS uses a dark glassmorphism theme with premium styling.
- The data layer uses SQLite via SQLAlchemy. The database file is at `data/bank_risk.db`.
- Configuration constants are centralized in `src/dashboard/config.py`.
- Auto-save runs every 30 seconds for user profiles.

## Git Workflow

- Current active branch: `dev_layout_test`
- Remote: `origin`
