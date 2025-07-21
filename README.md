# Portfolio Performance Dashboard

A comprehensive portfolio performance dashboard for Corporate Banking and CRE portfolios built with Dash and Python.

## Features

- **Portfolio Management**: Manage Corporate Banking and CRE portfolios with custom filters
- **Interactive Visualizations**: Financial trends charts, vintage analysis, portfolio summaries
- **Custom Metrics**: Create and save custom risk metrics with formula support
- **User Profile System**: Save portfolios and custom metrics per user profile
- **Real-time Analytics**: Auto-refreshing data with save notifications

## Architecture

### Core Components

- **Dashboard**: Multi-tab interface (Portfolio Summary, Holdings, Financial Trends, Vintage Analysis)
- **Portfolio System**: Default and custom portfolio management with LOB-specific metrics
- **Custom Metrics**: Formula-based metric creation with backtick column support
- **User Profiles**: Profile-based data persistence using JSON storage

### Data Structure

Required data files in `data/` directory:
- `facilities.csv`: Core facility data with Corporate Banking and CRE metrics
- `user_profiles.json`: User profile and custom data storage (auto-created)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
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
   rsconnect deploy dash app.py --title "Portfolio Performance Dashboard"
   ```

3. **Or deploy via VS Code**:
   - Install Posit Connect extension
   - Use Command Palette: "Python: Publish to Posit Connect"

### Configuration Files

- `requirements.txt`: Python dependencies (automatically detected by Posit Connect)

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
portfolio_performance_dashboard/
├── app.py                    # Main application
├── requirements.txt          # Dependencies
├── test_app.py              # Test suite
├── README.md                # Documentation
├── data/                    # Data files
│   ├── facilities.csv       # Core facility data
│   └── user_profiles.json   # User profiles (auto-created)
└── assets/                  # Static assets
    └── style.css
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