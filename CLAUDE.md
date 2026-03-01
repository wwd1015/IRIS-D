# CLAUDE.md — Project Context for IRIS-D

## Project Overview

**IRIS-D** (Interactive Reporting & Insight Generation System – Dashboard) is a portfolio performance dashboard for **Corporate Banking** and **Commercial Real Estate (CRE)** portfolios. It is built with **Dash** (Plotly) and **Python**, and is designed for deployment on **Posit Connect**.

## Tech Stack

- **Framework**: Dash (Plotly) for interactive web-based dashboards
- **Language**: Python 3.8+
- **Data**: Polars (primary), Pandas (SQL boundary only), NumPy, SQLAlchemy (SQLite backend at `data/bank_risk.db`)
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
│       │   ├── portfolio_callbacks.py # Portfolio CRUD (create, select, update, delete)
│       │   ├── time_window_callbacks.py # Time window modal, apply, reset, perf warning
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
│       │   ├── layout.py              # Main app shell (header, content, modals)
│       │   └── mixins/                # Reusable chart interaction mixins
│       │       └── click_detail.py    # Click-to-detail: drill-down table on chart click
│       ├── data/              # Data loading & generation
│       │   ├── dataset.py             # Dataset abstraction (filtering, caching, introspection)
│       │   ├── registry.py            # DatasetRegistry — named dataset access
│       │   ├── sources.py             # DataSource protocol + SqliteDataSource + InMemoryDataSource
│       │   ├── loader.py              # load_dataset() + load_facilities_data() façade
│       │   ├── models.py              # Pydantic FacilityRecord + FacilityDataset
│       │   └── db_data_generator.py
│       └── utils/             # Utility functions
│           ├── helpers.py
│           └── logging.py             # configure_logging() — structured console output
├── data/
│   ├── bank_risk.db           # SQLite database (generated locally, not in repo)
│   ├── datatidy_config.yaml   # Data processing rules
│   └── user_profiles.json     # User preferences (auto-created)
├── assets/
│   ├── style.css              # CSS styling (glassmorphism dark theme)
│   └── tab_switch_v2.js       # Instant tab switching (JS mousedown + fetch interceptor)
├── docs/
│   └── DEVELOPER_GUIDE.md     # Framework developer reference
└── tests/
    ├── conftest.py            # Shared fixtures (minimal_df, app_state, tab_context)
    ├── test_prototype.py
    ├── unit/
    │   ├── test_models.py
    │   ├── test_app_state.py
    │   ├── test_registry.py
    │   ├── test_data_sources.py
    │   └── test_dataset.py
    └── integration/
        └── test_app.py
```

## Architecture

The dashboard uses a **3-layer modular framework**:

| Layer | Purpose | Key File |
|---|---|---|
| **Layer 1 — Global Controls** | Sticky header (portfolio selector, time window, theme, profile) | `components/controls.py` |
| **Layer 2 — Toolbar** | Per-tab controls (dropdowns, sliders, toggles) | `components/toolbar.py` |
| **Layer 3 — Content** | Sidebar + main content grid (cards, charts, tables) | `components/cards.py` |

### State Management

All mutable state lives in `app_state.py` as a module-level `AppState` singleton:

```python
from .app_state import app_state

ctx = app_state.make_tab_context("Corporate Banking")
df  = app_state.get_filtered_data("CRE")
app_state.set_time_window("2024-01-31", "2026-01-31")  # global time window
app_state.load_user_portfolios(username)   # on login/switch
app_state.save_user_data(username)         # on portfolio CRUD / autosave
```

**Time window:** `make_tab_context()` passes time-windowed `facilities_df` to tabs. `get_filtered_data()` returns the latest snapshot within the window. Default: last 2 years.

### Data Layer

The data layer uses **Polars** for all DataFrames and is built around the **Dataset** abstraction:

```python
from .data.sources import SqliteDataSource, InMemoryDataSource, set_default_source
from .data.dataset import Dataset
from .data.registry import DatasetRegistry

# In tests — swap to in-memory, no DB required:
set_default_source(InMemoryDataSource(my_df))  # accepts pandas or polars

# Access a registered dataset:
ds = DatasetRegistry.get("facilities")
df = ds.get_filtered("Corporate Banking", portfolios)  # cached
ds.invalidate_cache()  # after portfolio CRUD
```

**Key types:**
- `DataSource` protocol (`sources.py`) — pluggable source returning `pl.DataFrame`
- `Dataset` (`dataset.py`) — named dataset with full/latest snapshots, portfolio filtering with cache
- `DatasetRegistry` (`registry.py`) — global registry of named `Dataset` instances
- `load_dataset()` (`loader.py`) — builds a Dataset from the active source and registers it

### Adding a New Dataset

The Dataset abstraction is generic — adding a new data type (e.g. loans, collateral) requires no filter code changes:

1. **Add a loader** that returns a `pl.DataFrame` (or use the existing `DataSource`):

```python
# In loader.py or a new module
def load_loans_data() -> pl.DataFrame:
    engine = create_engine("sqlite:///data/bank_risk.db")
    pdf = pd.read_sql("SELECT * FROM loans ORDER BY loan_id, report_date", engine)
    return pl.from_pandas(pdf)
```

2. **Build and register** the Dataset in `AppState.initialize()`:

```python
# In app_state.py → initialize()
loans_df = load_loans_data()
loans_latest = loans_df.sort("report_date").group_by("loan_id").tail(1)
loans_ds = Dataset(
    name="loans",
    full_df=loans_df,
    latest_df=loans_latest,
    id_column="loan_id",
    date_column="report_date",
)
DatasetRegistry.register(loans_ds)
```

3. **Access from any tab** — portfolio filters apply identically:

```python
# In a tab's render or callback
ds = DatasetRegistry.get("loans")
filtered = ds.get_filtered(portfolio_name, app_state.portfolios)  # cached
all_dates = ds.full_df["report_date"].unique().sort()
categories = ds.get_segmentation_columns()
```

4. **Optionally expose via AppState** for convenience:

```python
# In app_state.py
@property
def loans_df(self) -> pl.DataFrame:
    return DatasetRegistry.get("loans").full_df
```

The `Dataset` class handles:
- **Portfolio filtering** via the same `{"filters": [...]}` criteria format
- **Result caching** (keyed by portfolio name, auto-invalidated on portfolio CRUD)
- **Column introspection** (`get_segmentation_columns()`, `get_unique_values()`)
- **Legacy format migration** (old flat criteria auto-converted)

### Adding a New Tab

1. Copy `tabs/_template.py` to a new file (e.g. `tabs/my_analysis.py`)
2. Rename the class, set `id`, `label`, `order`
3. Implement `render_content()` (and optionally `get_toolbar_controls`, `get_cards`, `render_sidebar`, `register_callbacks`)
4. Uncomment `register_tab(MyAnalysisTab())` at the bottom
5. That's it — auto-discovery handles the rest

### Click-to-Detail (Chart Drill-Down)

Any chart can gain click-to-detail drill-down via `components/mixins/click_detail.py`:

```python
from ..components.mixins.click_detail import chart_with_detail_layout, register_detail_callback

# 1. In render_content — replace dcc.Graph with the wrapper:
chart_with_detail_layout("my-chart", figure=fig, height=400)

# 2. In register_callbacks — wire up the detail function:
register_detail_callback(
    app, "my-chart", detail_fn=my_detail_fn,
    extra_states=[State("universal-portfolio-dropdown", "value")],
)

# 3. Implement detail_fn — return a pl.DataFrame for the clicked element:
def my_detail_fn(click_point, curve_name, x_value, portfolio):
    # click_point: clickData["points"][0], curve_name: from customdata or curveNumber
    # Return None to hide the panel
    return filtered_df
```

**Behavior:** Click a bar/point → detail table slides in below with matching rows, clicked element highlighted (others dimmed to 25% opacity). Click same element again → toggle hide. Close button → hide. Switching to a different element updates the table and highlight.

**Important:** Set `customdata` on chart traces to pass the trace name reliably:
```python
fig.add_trace(go.Bar(x=..., y=..., name="Segment A",
                     customdata=[["Segment A"] for _ in x_values]))
```

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

# Generate test database (required after first clone)
python -m src.dashboard.data.db_data_generator

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
- Role gating uses `required_roles: list[str] | None` (plural). Enforced client-side (nav hidden) AND server-side (`route_tabs` falls back to first accessible tab).
- Structured logging via `utils/logging.py` — replace `print()` with `logging.getLogger(__name__)`.
- Tests use `InMemoryDataSource` fixture — no SQLite DB needed for unit tests.
- See `docs/DEVELOPER_GUIDE.md` for full framework reference.

## Git Workflow

- Current active branch: `main`
- Remote: `origin`
