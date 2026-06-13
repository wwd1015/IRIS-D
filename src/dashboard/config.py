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


# Color palettes — accents from the IRIS-D Redesign design system.
# ``warmBlue`` is the default; the design's alternates + the legacy warm
# editorial tones remain selectable via the runtime accent picker.
# Change ``accent_color`` in UISettings to switch the default.
COLOR_PALETTES: dict[str, dict[str, str]] = {
    "ledger": {  # Ledger oxblood — IRIS Redesign v2 default
        "400": "#96384a", "500": "#7d2230", "600": "#6a1c29", "700": "#581723",
        "glow": "125, 34, 48",
    },
    "warmBlue": {
        "400": "#6B8AFF", "500": "#4B6BFB", "600": "#3B5BDB", "700": "#2B4BC7",
        "glow": "75, 107, 251",  # RGB for rgba()
    },
    "emerald": {
        "400": "#34D399", "500": "#10B981", "600": "#059669", "700": "#047857",
        "glow": "16, 185, 129",
    },
    "amber": {
        "400": "#FBBF24", "500": "#F59E0B", "600": "#D97706", "700": "#B45309",
        "glow": "245, 158, 11",
    },
    "rose": {
        "400": "#FB7185", "500": "#E11D48", "600": "#BE123C", "700": "#9F1239",
        "glow": "225, 29, 72",
    },
    "violet": {
        "400": "#A78BFA", "500": "#7C3AED", "600": "#6D28D9", "700": "#5B21B6",
        "glow": "124, 58, 237",
    },
    "slate": {
        "400": "#94A3B8", "500": "#64748B", "600": "#475569", "700": "#334155",
        "glow": "100, 116, 139",
    },
    # Warm editorial tones (previous redesign) — still selectable
    "terracotta": {
        "400": "#d97757", "500": "#c96442", "600": "#b85538", "700": "#a0472e",
        "glow": "201, 100, 66",
    },
    "sage": {
        "400": "#6DA58B", "500": "#4D8B6F", "600": "#3D7A5F", "700": "#2D6A4F",
        "glow": "77, 139, 111",
    },
}

# Legacy aliases — keep backward compat for saved user prefs
COLOR_PALETTES["blue"] = COLOR_PALETTES["warmBlue"]
COLOR_PALETTES["coral"] = COLOR_PALETTES["terracotta"]
COLOR_PALETTES["stone"] = COLOR_PALETTES["slate"]


@dataclass(frozen=True)
class UISettings:
    """UI and asset configuration."""
    assets_folder: str = "assets"
    default_theme: str = "light"  # Ledger is paper-first
    accent_color: str = field(
        default_factory=lambda: os.environ.get("ACCENT_COLOR", "ledger")
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
