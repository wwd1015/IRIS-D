#!/usr/bin/env python3
"""
Main entry point for the Portfolio Performance Dashboard application.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.portfo_performance_dashboard.app import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)