# IRIS-D – Interactive Research & Insight Generation System - Dashboard

IRIS-D is a portfolio performance dashboard for Corporate Banking and CRE portfolios built with Dash (Plotly) and Python, designed for deployment on Posit Connect.

## Features

- **Portfolio Management**: Default and custom portfolios with hierarchical filters (LOB, industry, property type)
- **Interactive Visualizations**: Time-series bar charts, period-over-period waterfall charts, click-to-detail drill-down
- **Custom Metrics**: Formula builder with IF/THEN/ELSE logic, saved per user profile
- **User Profiles**: Named profiles with saved portfolios, custom metrics, and last-active portfolio memory
- **Time Window Control**: Global date range filtering with performance warnings for large datasets

## Architecture

### 3-Layer Modular Framework

| Layer | Purpose | Location |
|---|---|---|
| **Layer 1 — Global Controls** | Sticky header (portfolio selector, time window, theme, profile) | `components/controls.py` |
| **Layer 2 — Toolbar** | Per-tab controls (dropdowns, sliders, toggles) | `components/toolbar.py` |
| **Layer 3 — Content** | Sidebar + main content grid (cards, charts, tables) | `components/cards.py` |

### Tabs

Each tab is a self-contained module in `src/dashboard/tabs/` with auto-discovery:

| Tab | File | Description |
|---|---|---|
| Portfolio Summary | `portfolio_summary.py` | Time-series bar chart + period-over-period waterfall chart with click-detail |
| Financial Trends | `financial_trend.py` | Period comparison with dynamic filters and details table |
| Portfolio Trends | `portfolio_trend.py` | Benchmark comparison charts |
| SIR Analysis | `role_tabs.py` | Rating distribution analysis (role-gated) |
| Location Analysis | `role_tabs.py` | CRE geographic analysis (role-gated) |
| Financial Projection | `role_tabs.py` | Forecasting placeholder (role-gated) |
| Model Backtesting | `role_tabs.py` | Model validation placeholder (role-gated) |

### Data Layer

- **Polars** for all DataFrames (Pandas only at the SQL boundary)
- **Dataset abstraction** with portfolio filtering and result caching
- **DatasetRegistry** for global named dataset access
- **SQLite** backend (`data/bank_risk.db`) — generated locally, not in repo

## Getting Started

### 1. Install dependencies

```bash
pip install -e .
```

### 2. Generate the test database

```bash
python -m src.dashboard.data.db_data_generator
```

Creates `data/bank_risk.db` with synthetic facilities and ~10 years of monthly reporting history.

### 3. Run the application

```bash
python main.py
# → http://127.0.0.1:8050
```

### 4. Run tests

```bash
python -m pytest tests/unit/ -v   # No DB required
```

## File Structure

```
IRIS-D/
├── main.py                          # Local dev entry point
├── app.py                           # Posit Connect WSGI entry point
├── pyproject.toml                   # Project config & dependencies
├── src/
│   └── dashboard/
│       ├── app.py                   # Slim orchestrator (~100 lines)
│       ├── app_state.py             # AppState singleton — all mutable state
│       ├── config.py                # Settings dataclass
│       ├── auth/
│       │   └── user_management.py   # User profiles & role-based access
│       ├── callbacks/               # Callback modules grouped by concern
│       │   ├── __init__.py          # CallbackRegistry — auto-wires all layers
│       │   ├── user_callbacks.py
│       │   ├── portfolio_callbacks.py
│       │   ├── time_window_callbacks.py
│       │   └── custom_metric_callbacks.py
│       ├── tabs/                    # Self-contained tab modules
│       │   ├── registry.py          # BaseTab, TabContext, register_tab()
│       │   ├── __init__.py          # Auto-discovers & imports all non-_ tabs
│       │   ├── _template.py         # Annotated starter template
│       │   ├── portfolio_summary.py
│       │   ├── financial_trend.py
│       │   ├── portfolio_trend.py
│       │   └── role_tabs.py         # Role-gated tabs (SIR, Location, Projection, Backtesting)
│       ├── components/              # Shared UI framework
│       │   ├── cards.py             # DisplayCard hierarchy
│       │   ├── controls.py          # GlobalControl hierarchy (L1 header)
│       │   ├── toolbar.py           # ToolbarControl presets (L2)
│       │   ├── signals.py           # Signal bus (dcc.Store IDs)
│       │   ├── layout.py            # Main app shell
│       │   └── mixins/
│       │       └── click_detail.py  # Click-to-detail chart drill-down
│       ├── data/
│       │   ├── dataset.py           # Dataset abstraction
│       │   ├── registry.py          # DatasetRegistry
│       │   ├── sources.py           # DataSource protocol + implementations
│       │   ├── loader.py            # load_dataset() facade
│       │   ├── models.py            # Pydantic FacilityRecord
│       │   └── db_data_generator.py
│       └── utils/
│           ├── helpers.py           # Plotly theme, modal styles, formatters
│           ├── custom_metrics.py    # Formula parsing (tokens → Polars expr)
│           └── logging.py           # Structured console output
├── data/
│   ├── bank_risk.db                 # SQLite database (generated locally)
│   └── user_profiles.json           # User preferences (auto-created)
├── assets/
│   ├── style.css                    # CSS (glassmorphism dark theme)
│   └── tab_switch_v2.js             # Instant tab switching
├── docs/
│   └── DEVELOPER_GUIDE.md           # Framework developer reference
└── tests/
    ├── conftest.py
    ├── unit/                        # Unit tests (no DB needed)
    └── integration/
```

## Deployment

```bash
rsconnect deploy dash main.py --title "Portfolio Performance Dashboard"
```

See `docs/DEVELOPER_GUIDE.md` for the full framework reference.
