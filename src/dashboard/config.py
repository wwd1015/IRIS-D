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
from dataclasses import dataclass, field


# =============================================================================
# GROUPED SETTINGS DATACLASSES
# =============================================================================


@dataclass(frozen=True)
class DatabaseSettings:
    """Settings that control data persistence."""
    path: str = field(
        default_factory=lambda: os.environ.get("DATABASE_PATH", "data/bank_risk.db")
    )
    profiles_file: str = field(
        default_factory=lambda: os.environ.get("PROFILES_FILE", "data/user_profiles.json")
    )

    def __post_init__(self) -> None:
        import logging
        if not os.path.exists(self.path):
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


# Color palettes — change ``accent_color`` in UISettings to switch.
COLOR_PALETTES: dict[str, dict[str, str]] = {
    "blue": {
        "400": "#6B8AFF", "500": "#4B6BFB", "600": "#3B5BDB", "700": "#2B4BC7",
        "glow": "75, 107, 251",  # RGB for rgba()
    },
    "slate": {
        "400": "#7C8DB5", "500": "#5B6E9E", "600": "#475985", "700": "#364570",
        "glow": "91, 110, 158",
    },
    "sage": {
        "400": "#6DA58B", "500": "#4D8B6F", "600": "#3D7A5F", "700": "#2D6A4F",
        "glow": "77, 139, 111",
    },
    "coral": {
        "400": "#F2836B", "500": "#E8674F", "600": "#D15340", "700": "#B94035",
        "glow": "232, 103, 79",
    },
}


@dataclass(frozen=True)
class UISettings:
    """UI and asset configuration."""
    assets_folder: str = "assets"
    default_theme: str = "dark"
    accent_color: str = field(
        default_factory=lambda: os.environ.get("ACCENT_COLOR", "blue")
    )


@dataclass(frozen=True)
class Settings:
    """Top-level settings container — one instance at module load time."""
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    app: AppSettings = field(default_factory=AppSettings)
    ui: UISettings = field(default_factory=UISettings)


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
