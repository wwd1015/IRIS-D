"""
Configuration constants and settings for the Portfolio Performance Dashboard.
"""

# Default portfolios (constant)
DEFAULT_PORTFOLIOS = {
    'Corporate Banking': {'lob': 'Corporate Banking', 'industry': None, 'property_type': None},
    'CRE': {'lob': 'CRE', 'industry': None, 'property_type': None}
}

# Profile Management System
PROFILES_FILE = 'data/user_profiles.json'

# Database settings
DATABASE_PATH = 'data/bank_risk.db'
DATATIDY_CONFIG_PATH = 'data/datatidy_config.yaml'

# Application settings
DEFAULT_USER = 'Guest'
DEBUG_MODE = True
HOST = '127.0.0.1'
PORT = 8050

# Asset folders
ASSETS_FOLDER = 'assets'