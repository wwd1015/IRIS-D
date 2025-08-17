# Portfolio Performance Dashboard

A comprehensive portfolio performance dashboard for Corporate Banking and CRE portfolios built with Dash and Python.

## Features

- **Portfolio Management**: Manage Corporate Banking and CRE portfolios with custom filters
- **Interactive Visualizations**: Financial trends charts, vintage analysis, portfolio summaries
- **Custom Metrics**: Create and save custom risk metrics with formula support
- **User Profile System**: Save portfolios and custom metrics per user profile
- **Real-time Analytics**: Auto-refreshing data with save notifications

## Architecture

### Modern Python Package Structure

The application follows a modern Python package structure with clear separation of concerns:

- **Entry Point**: `main.py` serves as the application entry point
- **Core Application**: Located in `src/dashboard/`
- **Modular Components**: Organized into logical modules (auth, components, data, utils)
- **Asset Management**: CSS and static files in `assets/` directory

### Core Components

- **Dashboard**: Multi-tab interface with role-based navigation (Portfolio Summary, Holdings, Financial Trends, Vintage Analysis, SIR Analysis, etc.)
- **Portfolio System**: Default and custom portfolio management with LOB-specific metrics
- **User Management**: Role-based access control (Corp SCO, CRE SCO, SAG, BA)
- **Custom Metrics**: Formula-based metric creation with backtick column support
- **Data Integration**: SQLite database with DataTidy processing pipeline

### Data Structure

The application uses an integrated data pipeline:
- **Database**: SQLite database (`data/bank_risk.db`) with facility data
- **Data Processing**: DataTidy integration for data validation and cleaning
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

## Technical Details

### Data Processing
- Pandas for data manipulation
- Time-series analysis for vintage cohorts
- Dynamic filtering based on portfolio criteria

### Visualization
- Plotly for interactive charts
- Dash for web interface
- Responsive design with custom CSS

### Performance
- Auto-save every 30 seconds
- Efficient data filtering and aggregation
- Client-side interactivity

## File Structure

```
bank_risk_dashboard/
├── main.py                          # Application entry point
├── pyproject.toml                   # Project configuration and dependencies
├── README.md                       # Documentation
├── src/                            # Source code
│   └── dashboard/
│       ├── __init__.py
│       ├── app.py                  # Main Dash application
│       ├── config.py               # Configuration
│       ├── auth/                   # Authentication modules
│       │   ├── __init__.py
│       │   └── user_management.py
│       ├── components/             # UI components
│       │   ├── __init__.py
│       │   ├── layout.py
│       │   ├── portfolio_summary.py
│       │   ├── portfolio_trend.py
│       │   ├── holdings.py
│       │   ├── vintage_analysis.py
│       │   ├── financial_trends.py
│       │   ├── sir_analysis.py
│       │   ├── location_analysis.py
│       │   ├── financial_projection.py
│       │   ├── model_backtesting.py
│       │   └── portfolio_management.py
│       ├── data/                   # Data processing modules
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   └── db_data_generator.py
│       └── utils/                  # Utility functions
│           └── __init__.py
├── data/                           # Data files
│   ├── bank_risk.db               # SQLite database
│   ├── datatidy_config.yaml       # Data processing config
│   └── user_profiles.json         # User profiles (auto-created)
├── assets/                         # Static assets
│   └── style.css                  # CSS styling
└── tests/                         # Test files
    ├── unit/
    ├── integration/
    │   └── test_app.py
    └── test_prototype.py
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