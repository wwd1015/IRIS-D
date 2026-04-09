"""
Configuration constants and settings for IRIS-D.

Settings are grouped into three dataclasses (DatabaseSettings, AppSettings,
UISettings) and assembled into a single ``Settings`` object that reads
environment-variable overrides automatically.

Usage::

    from . import config
    print(config.DATABASE_PATH)   # backward-compat flat attribute
    print(config.settings.app.debug)  # new structured access
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field


# =============================================================================
# FROZEN-MODE PATH RESOLUTION (PyInstaller)
# =============================================================================

def _is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def _bundle_dir() -> str:
    """Root of the PyInstaller bundle (read-only extracted files)."""
    return getattr(sys, "_MEIPASS", os.path.abspath("."))


def _user_data_dir() -> str:
    """Persistent writable directory for user data in frozen mode."""
    return os.path.join(os.path.expanduser("~"), ".iris-d")


def _default_db_path() -> str:
    env = os.environ.get("DATABASE_PATH")
    if env:
        return env
    if _is_frozen():
        return os.path.join(_bundle_dir(), "data", "bank_risk.db")
    return "data/bank_risk.db"


def _default_profiles_path() -> str:
    env = os.environ.get("PROFILES_FILE")
    if env:
        return env
    if _is_frozen():
        return os.path.join(_user_data_dir(), "user_profiles.json")
    return "data/user_profiles.json"


# =============================================================================
# GROUPED SETTINGS DATACLASSES
# =============================================================================


@dataclass(frozen=True)
class DatabaseSettings:
    """Settings that control data persistence."""
    path: str = field(default_factory=_default_db_path)
    profiles_file: str = field(default_factory=_default_profiles_path)
    source_type: str = field(
        default_factory=lambda: os.environ.get("DATA_SOURCE_TYPE", "sqlite")
    )

    def __post_init__(self) -> None:
        import logging
        if self.source_type == "sqlite" and not os.path.exists(self.path):
            logging.getLogger(__name__).warning(
                "Database not found at '%s'. Run db_data_generator.py first.", self.path
            )


@dataclass(frozen=True)
class AppSettings:
    """Runtime application settings."""
    host: str = field(default_factory=lambda: os.environ.get("HOST", "127.0.0.1"))
    port: int = field(
        default_factory=lambda: int(os.environ.get("PORT", "8050"))
    )
    debug: bool = field(
        default_factory=lambda: os.environ.get("DEBUG", "False").lower() == "true"
    )
    default_user: str = "John Smith"

    def __post_init__(self) -> None:
        if not (1 <= self.port <= 65535):
            raise ValueError(f"PORT must be between 1 and 65535, got {self.port}")


# Color palettes — warm editorial tones inspired by Claude design system.
# Change ``accent_color`` in UISettings to switch.
COLOR_PALETTES: dict[str, dict[str, str]] = {
    "terracotta": {
        "400": "#d97757", "500": "#c96442", "600": "#b85538", "700": "#a0472e",
        "glow": "201, 100, 66",  # RGB for rgba()
    },
    "sage": {
        "400": "#6DA58B", "500": "#4D8B6F", "600": "#3D7A5F", "700": "#2D6A4F",
        "glow": "77, 139, 111",
    },
    "stone": {
        "400": "#87867f", "500": "#5e5d59", "600": "#4d4c48", "700": "#3d3d3a",
        "glow": "94, 93, 89",
    },
    "clay": {
        "400": "#c9856a", "500": "#b5725a", "600": "#a06050", "700": "#8b5045",
        "glow": "181, 114, 90",
    },
}

# Legacy alias — keep backward compat for saved user prefs referencing "blue"
COLOR_PALETTES["blue"] = COLOR_PALETTES["terracotta"]
COLOR_PALETTES["coral"] = COLOR_PALETTES["terracotta"]
COLOR_PALETTES["slate"] = COLOR_PALETTES["stone"]


@dataclass(frozen=True)
class UISettings:
    """UI and asset configuration."""
    assets_folder: str = "assets"
    default_theme: str = "dark"
    accent_color: str = field(
        default_factory=lambda: os.environ.get("ACCENT_COLOR", "terracotta")
    )


@dataclass(frozen=True)
class SnowflakeSettings:
    """Connection settings for Snowflake data source."""
    account: str = field(
        default_factory=lambda: os.environ.get("SNOWFLAKE_ACCOUNT", "")
    )
    warehouse: str = field(
        default_factory=lambda: os.environ.get("SNOWFLAKE_WAREHOUSE", "")
    )
    database: str = field(
        default_factory=lambda: os.environ.get("SNOWFLAKE_DATABASE", "")
    )
    schema: str = field(
        default_factory=lambda: os.environ.get("SNOWFLAKE_SCHEMA", "")
    )
    role: str = field(
        default_factory=lambda: os.environ.get("SNOWFLAKE_ROLE", "")
    )
    authenticator: str = field(
        default_factory=lambda: os.environ.get("SNOWFLAKE_AUTHENTICATOR", "externalbrowser")
    )
    query: str = field(
        default_factory=lambda: os.environ.get(
            "SNOWFLAKE_QUERY",
            "SELECT * FROM raw_facilities ORDER BY facility_id, reporting_date",
        )
    )


@dataclass(frozen=True)
class Settings:
    """Top-level settings container — one instance at module load time."""
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    app: AppSettings = field(default_factory=AppSettings)
    ui: UISettings = field(default_factory=UISettings)
    snowflake: SnowflakeSettings = field(default_factory=SnowflakeSettings)


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

settings = Settings()


# =============================================================================
# FLAT CONSTANTS (backward-compatible aliases)
# =============================================================================

# Default portfolios (data, not a setting)
DEFAULT_PORTFOLIOS = {
    "Entire Commercial": {"filters": []},
}

# Flat aliases — kept so existing imports don't need changing
DATABASE_PATH: str = settings.db.path
PROFILES_FILE: str = settings.db.profiles_file

HOST: str = settings.app.host
PORT: int = settings.app.port
DEBUG_MODE: bool = settings.app.debug
DEFAULT_USER: str = settings.app.default_user


ASSETS_FOLDER: str = settings.ui.assets_folder
DATA_SOURCE_TYPE: str = settings.db.source_type
