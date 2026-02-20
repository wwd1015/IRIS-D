"""
User management functions for IRIS-D (Interactive Reporting & Insight Generation System - Dashboard).
Handles user profiles, authentication, and data persistence.
"""

import json
import logging
import os
from datetime import datetime

from .. import config

logger = logging.getLogger(__name__)

# Global variable for current user
current_user = config.DEFAULT_USER


def load_profiles():
    """Load user profiles from file"""
    if os.path.exists(config.PROFILES_FILE):
        try:
            with open(config.PROFILES_FILE, "r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load profiles from '%s': %s", config.PROFILES_FILE, exc)
            return {}
    return {}

def save_profiles(profiles_data):
    """Save user profiles to file"""
    os.makedirs(os.path.dirname(config.PROFILES_FILE), exist_ok=True)
    with open(config.PROFILES_FILE, "w") as f:
        json.dump(profiles_data, f, indent=2)
    logger.debug("Saved profiles for %d user(s)", len(profiles_data))

def get_user_data(username):
    """Get user-specific data (portfolios and custom metrics)"""
    profiles = load_profiles()
    if username in profiles:
        return profiles[username]
    return {'portfolios': {}, 'custom_metrics': {}}

def save_user_data(username, portfolios_data, custom_metrics_data):
    """Save user-specific data while preserving existing fields like role"""
    profiles = load_profiles()
    if username in profiles:
        # Preserve existing data like role, created date
        profiles[username].update({
            'portfolios': portfolios_data,
            'custom_metrics': custom_metrics_data,
            'last_saved': datetime.now().isoformat()
        })
    else:
        # New user
        profiles[username] = {
            'portfolios': portfolios_data,
            'custom_metrics': custom_metrics_data,
            'last_saved': datetime.now().isoformat()
        }
    save_profiles(profiles)
    logger.debug("Saved user data for '%s'", username)

def get_current_user_role():
    """Get the current user's role"""
    if current_user == 'Guest':
        return 'Guest'
    
    user_data = get_user_data(current_user)
    return user_data.get('role', 'BA')  # Default to BA if role not found

def set_current_user(username):
    """Set the current user"""
    global current_user
    current_user = username

def get_current_user():
    """Get the current user"""
    return current_user