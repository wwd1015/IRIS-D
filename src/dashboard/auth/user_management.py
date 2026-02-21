"""
User management functions for IRIS-D.

All user data (roster, role, portfolios, custom metrics) lives in a single
JSON file (``user_profiles.json``).  Each top-level key is a username whose
value contains ``role``, ``portfolios``, ``custom_metrics``, etc.
"""

import json
import logging
import os

from .. import config

logger = logging.getLogger(__name__)

# Global variable for current user (set to first profile entry on load)
current_user = None


# ── Profile persistence ──────────────────────────────────────────────────

def load_profiles() -> dict:
    """Load all user profiles from JSON file."""
    if os.path.exists(config.PROFILES_FILE):
        try:
            with open(config.PROFILES_FILE, "r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load profiles from '%s': %s", config.PROFILES_FILE, exc)
            return {}
    return {}


def save_profiles(profiles_data: dict) -> None:
    """Save all user profiles to file."""
    os.makedirs(os.path.dirname(config.PROFILES_FILE) or ".", exist_ok=True)
    with open(config.PROFILES_FILE, "w") as f:
        json.dump(profiles_data, f, indent=2)
    logger.debug("Saved profiles for %d user(s)", len(profiles_data))


# ── Roster (user list + roles) ───────────────────────────────────────────

def load_roster() -> list[dict]:
    """Return list of ``{name, role}`` dicts from profiles."""
    profiles = load_profiles()
    return [
        {"name": name, "role": data.get("role", "BA")}
        for name, data in profiles.items()
    ]


def add_user_to_roster(name: str, role: str) -> None:
    """Add a new user to the profiles file."""
    profiles = load_profiles()
    if name not in profiles:
        profiles[name] = {
            "role": role,
            "portfolios": {},
            "custom_metrics": {},
        }
        save_profiles(profiles)
        logger.debug("Added user '%s' (%s) to profiles", name, role)


# ── Current user ─────────────────────────────────────────────────────────

def get_current_user() -> str:
    """Get the current user. Defaults to first profile entry."""
    global current_user
    if current_user is None:
        profiles = load_profiles()
        current_user = next(iter(profiles), "Unknown")
    return current_user


def set_current_user(username: str) -> None:
    """Set the current user."""
    global current_user
    current_user = username


def get_current_user_role() -> str:
    """Get the current user's role."""
    user = get_current_user()
    profiles = load_profiles()
    if user in profiles:
        return profiles[user].get("role", "BA")
    return "BA"


# ── User data (portfolios & metrics) ─────────────────────────────────────

def get_user_data(username: str) -> dict:
    """Get user-specific data (portfolios and custom metrics)."""
    profiles = load_profiles()
    if username in profiles:
        return profiles[username]
    return {"portfolios": {}, "custom_metrics": {}}


def save_user_data(username: str, portfolios_data: dict, custom_metrics_data: dict) -> None:
    """Save user-specific data (preserves role and other fields)."""
    profiles = load_profiles()
    if username not in profiles:
        profiles[username] = {"role": "BA"}
    profiles[username].update({
        "portfolios": portfolios_data,
        "custom_metrics": custom_metrics_data,
    })
    save_profiles(profiles)
    logger.debug("Saved user data for '%s'", username)


def get_last_active_portfolio(username: str) -> str | None:
    """Return the last active portfolio name for a user, or None."""
    profiles = load_profiles()
    return profiles.get(username, {}).get("last_active_portfolio")


def set_last_active_portfolio(username: str, portfolio_name: str) -> None:
    """Record which portfolio the user last activated."""
    profiles = load_profiles()
    if username not in profiles:
        profiles[username] = {"role": "BA"}
    profiles[username]["last_active_portfolio"] = portfolio_name
    save_profiles(profiles)
    logger.debug("Set last active portfolio for '%s' to '%s'", username, portfolio_name)
