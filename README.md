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

- **Database**: SQLite database (`data/bank_risk.db`) with facility data
- **Data Processing**: Pydantic validation + DataTidy integration
- **Configuration**: YAML configuration (`data/datatidy_config.yaml`) for data processing rules
- **User Profiles**: JSON storage (`data/user_profiles.json`) for user preferences (auto-created)

## Installation

```bash
# Install dependencies
pip install -e .

# Or install in development mode with dev dependencies
pip install -e ".[dev]"

# Run the application
python main.py
```

## Deployment to Posit Connect

### Prerequisites
- Posit Connect server access
- rsconnect-python package or VS Code Posit Connect extension

### Deployment Steps

1. **Test the application**:
   ```bash
   python test_app.py
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
│       ├── data/                    # Data processing
│       │   ├── loader.py
│       │   └── db_data_generator.py
│       └── utils/                   # Shared utilities
│           └── helpers.py
├── data/                            # Data files
│   ├── bank_risk.db                 # SQLite database
│   ├── datatidy_config.yaml         # Data processing config
│   └── user_profiles.json           # User profiles (auto-created)
├── assets/                          # Static assets
│   └── style.css                    # CSS styling (glassmorphism dark theme)
├── docs/                            # Documentation
│   └── DEVELOPER_GUIDE.md           # Framework developer reference
└── tests/                           # Test files
    ├── test_prototype.py
    └── integration/
        └── test_app.py
```

## Testing

Run the test suite to validate functionality:

```bash
python test_app.py
```

Tests include:
- Dependency verification
- Data file validation
- Portfolio functionality
- Custom metrics system
- User profile management
- Application import

## Support

For deployment issues or feature requests, refer to the Posit Connect documentation or contact your system administrator.