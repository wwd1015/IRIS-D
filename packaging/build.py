#!/usr/bin/env python3
"""
One-click build script for IRIS-D standalone executable.

Usage:
    python packaging/build.py              # build for current OS (directory mode)
    python packaging/build.py --onefile    # single-file executable (slower startup)
    python packaging/build.py --clean      # remove previous build artifacts first

Produces:
    dist/IRIS-D/          (directory mode — zip and distribute)
    dist/IRIS-D           (onefile mode — single executable)

Requirements:
    pip install pyinstaller
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Tab modules that are imported dynamically via importlib / pkgutil
HIDDEN_IMPORTS = [
    "src.dashboard.tabs.portfolio_summary",
    "src.dashboard.tabs.financial_trend",
    "src.dashboard.tabs.portfolio_trend",
    "src.dashboard.tabs.playground",
    "src.dashboard.tabs.role_tabs",
    # Heavy packages with native extensions or lazy imports
    "polars",
    "pyarrow",
    "plotly",
    "dash",
    "pydantic",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
]

# Packages whose submodules must be collected recursively
COLLECT_SUBMODULES = [
    "dash",
    "plotly",
    "polars",
    "pyarrow",
    "pydantic",
    "src.dashboard",
]

# Packages whose data files must be included
COLLECT_DATA = [
    "dash",
    "plotly",
    "pydantic",
]


def _build_data_args() -> list[str]:
    """Return --add-data flags for bundled resources."""
    sep = os.pathsep
    args: list[str] = []

    # Assets (CSS, JS)
    assets_dir = os.path.join(PROJECT_ROOT, "assets")
    if os.path.isdir(assets_dir):
        args.extend(["--add-data", f"{assets_dir}{sep}assets"])

    # Database (placeholder for demo/offline mode)
    db_file = os.path.join(PROJECT_ROOT, "data", "bank_risk.db")
    if os.path.isfile(db_file):
        args.extend(["--add-data", f"{db_file}{sep}data"])

    # Default user profiles
    profiles = os.path.join(PROJECT_ROOT, "data", "user_profiles.json")
    if os.path.isfile(profiles):
        args.extend(["--add-data", f"{profiles}{sep}data"])

    return args


def build(*, onefile: bool = False, clean: bool = False) -> None:
    name = "IRIS-D"
    launcher = os.path.join(PROJECT_ROOT, "packaging", "launcher.py")
    dist_dir = os.path.join(PROJECT_ROOT, "dist")
    build_dir = os.path.join(PROJECT_ROOT, "build")

    if clean:
        for d in (dist_dir, build_dir):
            if os.path.isdir(d):
                print(f"Cleaning {d}")
                shutil.rmtree(d)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", name,
        "--onefile" if onefile else "--onedir",
        "--noconfirm",
        # Add project root to module search path
        "--paths", PROJECT_ROOT,
    ]

    # Data files
    cmd.extend(_build_data_args())

    # Hidden imports
    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])

    # Collect submodules recursively
    for pkg in COLLECT_SUBMODULES:
        cmd.extend(["--collect-submodules", pkg])

    # Collect data files for packages that need them
    for pkg in COLLECT_DATA:
        cmd.extend(["--collect-data", pkg])

    # macOS: build for native architecture only (universal2 requires fat binaries
    # which most pip-installed packages don't provide)
    # No extra flags needed — PyInstaller auto-detects the native arch.

    cmd.append(launcher)

    print(f"\nBuilding {name} for {platform.system()} ({platform.machine()})...\n")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    # Summary
    if onefile:
        ext = ".exe" if platform.system() == "Windows" else ""
        output = os.path.join(dist_dir, f"{name}{ext}")
    else:
        output = os.path.join(dist_dir, name)
    print(f"\n{'=' * 60}")
    print(f"  Build complete!")
    print(f"  Output: {output}")
    if not onefile:
        print(f"  Zip this directory for distribution via Google Drive.")
    print(f"{'=' * 60}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build IRIS-D standalone executable")
    parser.add_argument(
        "--onefile", action="store_true",
        help="Produce a single executable (slower startup, simpler to distribute)",
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Remove previous build/dist directories before building",
    )
    args = parser.parse_args()

    # Preflight checks
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("ERROR: PyInstaller is not installed.")
        print("Install it with:  pip install 'iris-d[packaging]'")
        print("            or:   pip install pyinstaller")
        sys.exit(1)

    build(onefile=args.onefile, clean=args.clean)


if __name__ == "__main__":
    main()
