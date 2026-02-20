# CLAUDE.md — Project Context for IRIS-D

## Project Overview

**IRIS-D** (Interactive Reporting & Insight Generation System – Dashboard) is a portfolio performance dashboard for **Corporate Banking** and **Commercial Real Estate (CRE)** portfolios. It is built with **Dash** (Plotly) and **Python**, and is designed for deployment on **Posit Connect**.

## Tech Stack

- **Framework**: Dash (Plotly) for interactive web-based dashboards
- **Language**: Python 3.8+
- **Data**: Pandas, NumPy, SQLAlchemy (SQLite backend at `data/bank_risk.db`)
- **Validation**: Pydantic
- **Config**: PyYAML
- **Styling**: Custom CSS (`assets/style.css`) — dark-themed glassmorphism design with Tailwind utility classes
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
│       ├── tabs/              # Tab implementations (self-contained per tab)
│       │   ├── registry.py            # BaseTab, TabContext, register_tab()
│       │   ├── __init__.py            # Auto-imports all tab modules
│       │   ├── portfolio_summary.py   # Portfolio summary (charts, watchlist, sidebar, CRUD)
│       │   ├── holdings.py            # Holdings tab (table, time-series expansion)
│       │   ├── financial_trend.py     # Financial trends (details table, filters)
│       │   ├── portfolio_trend.py     # Portfolio trend (benchmark charts)
│       │   ├── vintage_analysis.py    # Vintage analysis (cohort charts)
│       │   └── role_tabs.py           # Role-gated tabs (SIR, Location, Projection, Backtesting)
│       ├── components/        # Shared UI framework (NOT tab-specific)
│       │   ├── cards.py               # DisplayCard hierarchy (ChartCard, TableCard, MetricCard)
│       │   ├── controls.py            # GlobalControl hierarchy (L1 header controls)
│       │   ├── toolbar.py             # ToolbarControl presets (L2 dropdowns, sliders)
│       │   ├── signals.py             # Cross-layer dcc.Store signal IDs
│       │   └── layout.py             # Main app shell (header, content, modals)
│       ├── data/              # Data loading & generation
│       │   ├── loader.py
│       │   └── db_data_generator.py
│       └── utils/             # Utility functions
│           └── helpers.py
├── data/
│   ├── bank_risk.db           # SQLite database (facility data)
│   ├── datatidy_config.yaml   # Data processing rules
│   └── user_profiles.json     # User preferences (auto-created)
├── assets/
│   └── style.css              # CSS styling (glassmorphism dark theme)
├── docs/
│   └── DEVELOPER_GUIDE.md     # Framework developer reference
└── tests/
    ├── test_prototype.py
    └── integration/
        └── test_app.py
```

## Architecture

The dashboard uses a **3-layer modular framework**:

| Layer | Purpose | Key File |
|---|---|---|
| **Layer 1 — Global Controls** | Sticky header (portfolio selector, theme toggle, profile) | `components/controls.py` |
| **Layer 2 — Toolbar** | Per-tab controls (dropdowns, sliders, toggles) | `components/toolbar.py` |
| **Layer 3 — Content** | Sidebar + main content grid (cards, charts, tables) | `components/cards.py` |

Each tab is **self-contained** in `tabs/`. Tab-specific rendering helpers live *inside* the tab file as private `_` functions. Only shared framework abstractions live in `components/`.

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
- **Tabs**: Portfolio Summary, Holdings, Financial Trends, Portfolio Trends, Vintage Analysis, SIR Analysis, Location Analysis, Financial Projection, Model Backtesting.
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

- The main application logic (callbacks, layout assembly) lives in `src/dashboard/app.py`.
- Tab files in `tabs/` are self-contained: each tab file includes its own rendering helpers (private `_` functions) plus the `BaseTab` subclass, toolbar controls, and callbacks.
- `components/` contains **only shared framework code** (cards, controls, toolbar, signals, layout). It does NOT contain any tab-specific rendering logic.
- CSS uses a dark glassmorphism theme with premium styling.
- The data layer uses SQLite. The database file is at `data/bank_risk.db`.
- Configuration constants are centralized in `src/dashboard/config.py`.
- Auto-save runs every 30 seconds for user profiles.
- See `docs/DEVELOPER_GUIDE.md` for full framework reference.

## Git Workflow

- Current active branch: `dev_layout_test`
- Remote: `origin`
