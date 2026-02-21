"""
User management functions for IRIS-D (Interactive Reporting & Insight Generation System - Dashboard).
Handles user roster, role lookup, and data persistence.
"""

import json
import logging
import os
from datetime import datetime

import pandas as pd

from .. import config

logger = logging.getLogger(__name__)

# Global variable for current user (set to first roster entry on load)
current_user = None


def load_roster():
    """Load user roster from parquet file. Returns list of {name, role} dicts."""
    roster_path = config.settings.db.roster_file
    if os.path.exists(roster_path):
        try:
            df = pd.read_parquet(roster_path)
            return df.to_dict("records")
        except Exception as exc:
            logger.warning("Could not load roster from '%s': %s", roster_path, exc)
    return []


def add_user_to_roster(name, role):
    """Append a user to the roster parquet file."""
    roster_path = config.settings.db.roster_file
    roster = load_roster()
    roster.append({"name": name, "role": role})
    df = pd.DataFrame(roster)
    os.makedirs(os.path.dirname(roster_path), exist_ok=True)
    df.to_parquet(roster_path, index=False)
    logger.debug("Added user '%s' (%s) to roster", name, role)


def get_current_user_role():
    """Get the current user's role from the roster."""
    user = get_current_user()
    roster = load_roster()
    for entry in roster:
        if entry["name"] == user:
            return entry["role"]
    return "BA"  # Default fallback


def set_current_user(username):
    """Set the current user."""
    global current_user
    current_user = username


def get_current_user():
    """Get the current user. Defaults to first roster entry."""
    global current_user
    if current_user is None:
        roster = load_roster()
        current_user = roster[0]["name"] if roster else "Unknown"
    return current_user


# --- Legacy profile persistence (for custom portfolios/metrics) ---

def load_profiles():
    """Load user profiles from JSON file (for portfolio/metric storage)."""
    if os.path.exists(config.PROFILES_FILE):
        try:
            with open(config.PROFILES_FILE, "r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load profiles from '%s': %s", config.PROFILES_FILE, exc)
            return {}
    return {}


def save_profiles(profiles_data):
    """Save user profiles to file."""
    os.makedirs(os.path.dirname(config.PROFILES_FILE), exist_ok=True)
    with open(config.PROFILES_FILE, "w") as f:
        json.dump(profiles_data, f, indent=2)
    logger.debug("Saved profiles for %d user(s)", len(profiles_data))


def get_user_data(username):
    """Get user-specific data (portfolios and custom metrics)."""
    profiles = load_profiles()
    if username in profiles:
        return profiles[username]
    return {'portfolios': {}, 'custom_metrics': {}}


def save_user_data(username, portfolios_data, custom_metrics_data):
    """Save user-specific data."""
    profiles = load_profiles()
    if username in profiles:
        profiles[username].update({
            'portfolios': portfolios_data,
            'custom_metrics': custom_metrics_data,
            'last_saved': datetime.now().isoformat()
        })
    else:
        profiles[username] = {
            'portfolios': portfolios_data,
            'custom_metrics': custom_metrics_data,
            'last_saved': datetime.now().isoformat()
        }
    save_profiles(profiles)
    logger.debug("Saved user data for '%s'", username)
