"""
Configuration constants and settings for the Portfolio Performance Dashboard.
"""

import os

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
DEBUG_MODE = os.environ.get('DEBUG', 'False').lower() == 'true'
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', 8050))

# Asset folders
ASSETS_FOLDER = 'assets'