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
    datatidy_config: str = field(
        default_factory=lambda: os.environ.get("DATATIDY_CONFIG", "data/datatidy_config.yaml")
    )
    profiles_file: str = field(
        default_factory=lambda: os.environ.get("PROFILES_FILE", "data/user_profiles.json")
    )
    roster_file: str = field(
        default_factory=lambda: os.environ.get("ROSTER_FILE", "data/user_roster.parquet")
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


@dataclass(frozen=True)
class UISettings:
    """UI and asset configuration."""
    assets_folder: str = "assets"
    default_theme: str = "dark"


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
    "Corporate Banking": {"lob": "Corporate Banking", "industry": None, "property_type": None},
    "CRE": {"lob": "CRE", "industry": None, "property_type": None},
}

# Flat aliases — kept so existing imports don't need changing
DATABASE_PATH: str = settings.db.path
DATATIDY_CONFIG_PATH: str = settings.db.datatidy_config
PROFILES_FILE: str = settings.db.profiles_file

HOST: str = settings.app.host
PORT: int = settings.app.port
DEBUG_MODE: bool = settings.app.debug
DEFAULT_USER: str = settings.app.default_user
ROSTER_FILE: str = settings.db.roster_file

ASSETS_FOLDER: str = settings.ui.assets_folder
