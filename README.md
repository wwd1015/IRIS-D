# IRIS-D – Interactive Reporting & Insight Generation System - Dashboard

IRIS-D is a comprehensive portfolio performance dashboard for Corporate Banking and CRE portfolios built with Dash and Python.

## Features

- **Portfolio Management**: Manage Corporate Banking and CRE portfolios with custom filters
- **Interactive Visualizations**: Financial trends charts, vintage analysis, portfolio summaries
- **Custom Metrics**: Create and save custom risk metrics with formula support
- **User Profile System**: Save portfolios and custom metrics per user profile
- **Real-time Analytics**: Auto-refreshing data with save notifications

## Architecture

### 3-Layer Modular Framework

The dashboard is built on a modular 3-layer architecture:

| Layer | Purpose | Location |
|---|---|---|
| **Layer 1 — Global Controls** | Sticky header bar (portfolio selector, theme, profile) | `components/controls.py` |
| **Layer 2 — Toolbar** | Per-tab controls (dropdowns, sliders, toggles) | `components/toolbar.py` |
| **Layer 3 — Content** | Sidebar + main content (cards, charts, tables) | `components/cards.py` |

### Self-Contained Tabs

Each tab is a self-contained module in `src/dashboard/tabs/`:

| Tab | File | Description |
|---|---|---|
| Portfolio Summary | `portfolio_summary.py` | Charts, watchlist, positions panel, portfolio CRUD |
| Holdings | `holdings.py` | Facility table with time-series row expansion |
| Financial Trends | `financial_trend.py` | Period comparison, dynamic filters, details table |
| Portfolio Trends | `portfolio_trend.py` | Benchmark comparison charts |
| Vintage Analysis | `vintage_analysis.py` | Quarterly cohort charts, default rates |
| SIR Analysis | `role_tabs.py` | Special Interest Rate analysis (placeholder) |
| Location Analysis | `role_tabs.py` | CRE geographic map with loan markers |
| Financial Projection | `role_tabs.py` | Forecasting (placeholder) |
| Model Backtesting | `role_tabs.py` | Model validation (placeholder) |

### Shared Components

The `components/` directory contains **only shared framework abstractions** (not tab-specific code):

- `cards.py` — DisplayCard hierarchy (ChartCard, TableCard, MetricCard, FilterCard)
- `controls.py` — GlobalControl hierarchy (header buttons, selectors)
- `toolbar.py` — ToolbarControl presets (DropdownControl, SliderControl, ToggleControl)
- `signals.py` — Cross-layer `dcc.Store` signal IDs
- `layout.py` — Main app shell (header, content area, modals)

### Data Structure

- **Database**: SQLite database (`data/bank_risk.db`) — generated locally via `db_data_generator.py`
- **Data Processing**: Pydantic validation + DataTidy integration
- **Configuration**: YAML configuration (`data/datatidy_config.yaml`) for data processing rules
- **User Profiles**: JSON storage (`data/user_profiles.json`) for user preferences (auto-created)

## Getting Started

### 1. Install dependencies

```bash
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

### 2. Generate the test database

The SQLite database (`data/bank_risk.db`) is **not** included in the repository due to its size. You must generate it locally after cloning:

```bash
python -m src.dashboard.data.db_data_generator
```

This creates `data/bank_risk.db` with ~6,000 synthetic facilities (2,100 Corporate + 900 CRE) and ~10 years of monthly reporting history (~200K+ records). Generation takes about 1–2 minutes.

### 3. Run the application

```bash
python main.py
# → http://127.0.0.1:8050
```

### 4. Run tests

```bash
python -m pytest tests/unit/ -v   # Unit tests (no DB required)
```

## Deployment to Posit Connect

### Prerequisites
- Posit Connect server access
- rsconnect-python package or VS Code Posit Connect extension

### Deployment Steps

1. **Test the application**:
   ```bash
   python -m pytest tests/unit/ -v
   ```

2. **Deploy via command line**:
   ```bash
   rsconnect deploy dash main.py --title "Portfolio Performance Dashboard"
   ```

3. **Or deploy via VS Code**:
   - Install Posit Connect extension
   - Use Command Palette: "Python: Publish to Posit Connect"

### Configuration Files

- `pyproject.toml`: Python dependencies and project configuration (automatically detected by Posit Connect)

## Usage

### Portfolio Management

1. **Default Portfolios**: Corporate Banking and CRE portfolios are pre-configured
2. **Custom Portfolios**: Create portfolios filtered by LOB, industry, or property type
3. **Portfolio Metrics**: View LOB-specific metrics (FCF, DSCR, etc.)

### Custom Metrics

1. Create formulas using column names: `balance > 1000000`
2. Use backticks for spaced columns: `` `free cash flow` / liquidity ``
3. Metrics are saved per user profile

### User Profiles

1. **Guest Mode**: Temporary session without persistence
2. **User Profiles**: Save portfolios and custom metrics
3. **Profile Switching**: Switch between profiles to load saved configurations

## File Structure

```
IRIS-D/
├── main.py                          # Application entry point
├── pyproject.toml                   # Project configuration and dependencies
├── README.md                        # Documentation
├── CLAUDE.md                        # AI context document
├── src/                             # Source code
│   └── dashboard/
│       ├── __init__.py
│       ├── app.py                   # Main Dash application (callbacks, layout)
│       ├── config.py                # Configuration constants
│       ├── auth/                    # Authentication
│       │   └── user_management.py
│       ├── tabs/                    # Self-contained tab modules
│       │   ├── registry.py              # BaseTab, TabContext, register_tab()
│       │   ├── __init__.py              # Auto-imports all tabs
│       │   ├── portfolio_summary.py     # Portfolio summary + sidebar + CRUD
│       │   ├── holdings.py              # Holdings table + time-series
│       │   ├── financial_trend.py       # Financial trends + filters
│       │   ├── portfolio_trend.py       # Portfolio trend charts
│       │   ├── vintage_analysis.py      # Vintage cohort analysis
│       │   └── role_tabs.py             # Role-gated tabs (SIR, Location, etc.)
│       ├── components/              # Shared UI framework only
│       │   ├── cards.py                 # DisplayCard hierarchy
│       │   ├── controls.py              # GlobalControl hierarchy
│       │   ├── toolbar.py               # ToolbarControl presets
│       │   ├── signals.py               # Signal store IDs
│       │   └── layout.py               # App shell & navigation
│       ├── callbacks/              # Callback modules
│       │   ├── __init__.py            # CallbackRegistry (auto-wiring)
│       │   ├── user_callbacks.py      # Login, register, profile-switch
│       │   ├── portfolio_callbacks.py # Portfolio CRUD
│       │   └── time_window_callbacks.py # Time window modal
│       ├── data/                    # Data loading & abstraction
│       │   ├── dataset.py             # Dataset (filtering, caching)
│       │   ├── registry.py            # DatasetRegistry
│       │   ├── sources.py             # DataSource protocol
│       │   ├── loader.py              # load_dataset() facade
│       │   └── db_data_generator.py   # Synthetic data generator
│       └── utils/                   # Shared utilities
│           ├── helpers.py
│           └── logging.py
├── data/                            # Data files
│   ├── bank_risk.db                 # SQLite database (generated locally)
│   ├── datatidy_config.yaml         # Data processing config
│   └── user_profiles.json           # User profiles (auto-created)
├── assets/                          # Static assets
│   ├── style.css                    # CSS styling (glassmorphism dark theme)
│   └── tab_switch_v2.js             # Instant tab switching
├── docs/                            # Documentation
│   └── DEVELOPER_GUIDE.md           # Framework developer reference
└── tests/                           # Test files
    ├── conftest.py                  # Shared fixtures
    ├── unit/                        # Unit tests (no DB needed)
    └── integration/
        └── test_app.py
```

## Testing

```bash
python -m pytest tests/unit/ -v
```

Unit tests use an in-memory data source — no SQLite database required.

## Support

For deployment issues or feature requests, refer to the Posit Connect documentation or contact your system administrator.