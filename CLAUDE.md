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
├── main.py                    # Local dev entry point (calls configure_logging)
├── app.py                     # Posit Connect WSGI entry point
├── pyproject.toml             # Project config & dependencies
├── requirements.txt           # Flexible deps for backward compat
├── src/
│   └── dashboard/
│       ├── app.py             # Slim orchestrator: init, callback wiring, layout (~100 lines)
│       ├── app_state.py       # AppState singleton — all mutable state, filtering, TabContext
│       ├── config.py          # Settings dataclass (DatabaseSettings, AppSettings, UISettings)
│       ├── auth/              # User management & role-based access
│       │   └── user_management.py
│       ├── callbacks/         # Callback modules grouped by concern
│       │   ├── __init__.py            # CallbackRegistry — auto-wires all 3 layers
│       │   ├── user_callbacks.py      # Login, register, delete-profile, profile-switch
│       │   ├── portfolio_callbacks.py # Portfolio CRUD (create, select, delete)
│       │   └── autosave_callbacks.py  # Auto-save timer + notification banner
│       ├── tabs/              # Tab implementations (self-contained per tab)
│       │   ├── registry.py            # BaseTab, TabContext, register_tab()
│       │   ├── __init__.py            # Auto-discovers & imports all non-_ tab modules
│       │   ├── _template.py           # Annotated starter template for new tabs
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
│       │   ├── signals.py             # Signal bus (PORTFOLIO, USER, THEME, DATE_RANGE, NOTIFICATION)
│       │   └── layout.py              # Main app shell (header, content, modals)
│       ├── data/              # Data loading & generation
│       │   ├── sources.py             # DataSource protocol + SqliteDataSource + InMemoryDataSource
│       │   ├── loader.py              # Thin façade over DataSource
│       │   ├── models.py              # Pydantic FacilityRecord + FacilityDataset
│       │   └── db_data_generator.py
│       └── utils/             # Utility functions
│           ├── helpers.py
│           └── logging.py             # configure_logging() — structured console output
├── data/
│   ├── bank_risk.db           # SQLite database (facility data)
│   ├── datatidy_config.yaml   # Data processing rules
│   └── user_profiles.json     # User preferences (auto-created)
├── assets/
│   └── style.css              # CSS styling (glassmorphism dark theme)
├── docs/
│   └── DEVELOPER_GUIDE.md     # Framework developer reference
└── tests/
    ├── conftest.py            # Shared fixtures (minimal_df, app_state, tab_context)
    ├── test_prototype.py
    ├── unit/
    │   ├── test_models.py
    │   ├── test_app_state.py
    │   ├── test_registry.py
    │   └── test_data_sources.py
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

### State Management

All mutable state lives in `app_state.py` as a module-level `AppState` singleton:

```python
from .app_state import app_state

ctx = app_state.make_tab_context("Corporate Banking")
df  = app_state.get_filtered_data("CRE")
app_state.load_user_portfolios(username)   # on login/switch
app_state.save_user_data(username)         # on portfolio CRUD / autosave
```

### Data Layer

The data layer is pluggable via the `DataSource` protocol (`data/sources.py`):

```python
from .data.sources import SqliteDataSource, InMemoryDataSource, set_default_source

# In tests — swap to in-memory, no DB required:
set_default_source(InMemoryDataSource(my_df))
```

### Adding a New Tab

1. Copy `tabs/_template.py` to a new file (e.g. `tabs/my_analysis.py`)
2. Rename the class, set `id`, `label`, `order`
3. Implement `render_content()` (and optionally `get_toolbar_controls`, `get_cards`, `render_sidebar`, `register_callbacks`)
4. Uncomment `register_tab(MyAnalysisTab())` at the bottom
5. That's it — auto-discovery handles the rest

### Signals

`components/signals.py` defines well-known `dcc.Store` IDs:

| Signal | Value type | Purpose |
|---|---|---|
| `Signal.PORTFOLIO` | `str` | Selected portfolio name |
| `Signal.USER` | `str` | Current username |
| `Signal.THEME` | `str` | `"light"` or `"dark"` |
| `Signal.DATE_RANGE` | `dict` | `{"start": iso, "end": iso}` |
| `Signal.NOTIFICATION` | `dict` | `{"message": str, "level": str}` |
| `Signal.tab_filter(tab_id)` | `dict` | Per-tab toolbar state |

Tabs can register custom signals: `SignalRegistry.register("my-signal-id")`

## How to Run

```bash
# Install (editable mode)
pip install -e .

# Run locally
python main.py
# → Runs at http://127.0.0.1:8050 by default

# Run tests
pytest tests/unit/ -v

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

| Variable | Default | Description |
|---|---|---|
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `8050` | Server port |
| `DEBUG` | `False` | Enable Dash debug mode + verbose logging |
| `DATABASE_PATH` | `data/bank_risk.db` | Path to SQLite database |
| `PROFILES_FILE` | `data/user_profiles.json` | Path to user profiles JSON |

## Development Notes

- `app.py` is now a slim orchestrator (~100 lines). Callbacks live in `callbacks/`.
- `app_state.py` owns all mutable state — no `global` keyword anywhere in callbacks.
- Tab auto-discovery: drop a file in `tabs/` and call `register_tab()` — nothing else to edit.
- `register_tab()` raises `ValueError` on duplicate tab IDs (caught early).
- Structured logging via `utils/logging.py` — replace `print()` with `logging.getLogger(__name__)`.
- Tests use `InMemoryDataSource` fixture — no SQLite DB needed for unit tests.
- See `docs/DEVELOPER_GUIDE.md` for full framework reference.

## Git Workflow

- Current active branch: `main`
- Remote: `origin`
