#!/usr/bin/env python3
"""
Posit Connect compatible entry point for IRIS-D (Interactive Research & Insight Generation System - Dashboard).
This file provides WSGI-compatible application instance for deployment.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the Dash app
from src.dashboard.app import app

# Expose the Flask server for WSGI deployment
server = app.server

# For local development
if __name__ == '__main__':
    # Use environment variables for Posit Connect compatibility
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 8050))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(debug=debug, host=host, port=port)