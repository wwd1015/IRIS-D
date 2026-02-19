#!/usr/bin/env python3
"""
Main entry point for IRIS-D (Interactive Reporting & Insight Generation System - Dashboard).
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.dashboard.app import app
from src.dashboard.config import HOST, PORT, DEBUG_MODE

if __name__ == '__main__':
    app.run(debug=DEBUG_MODE, host=HOST, port=PORT)