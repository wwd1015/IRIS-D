#!/usr/bin/env python3
"""
PyInstaller entry point for IRIS-D standalone executable.

Starts the Dash server and opens the dashboard in the default browser.
This file is only used as the entry point for the packaged build —
the normal dev workflow (``python main.py``) is unchanged.
"""

import os
import shutil
import sys
import threading
import time
import webbrowser


def _seed_user_data() -> None:
    """Copy bundled user_profiles.json to the writable user-data directory
    on first run so the app starts with default profiles."""
    from src.dashboard.config import _is_frozen, _bundle_dir, _user_data_dir

    if not _is_frozen():
        return

    user_dir = _user_data_dir()
    target = os.path.join(user_dir, "user_profiles.json")
    if os.path.exists(target):
        return  # already seeded

    bundled = os.path.join(_bundle_dir(), "data", "user_profiles.json")
    if os.path.exists(bundled):
        os.makedirs(user_dir, exist_ok=True)
        shutil.copy2(bundled, target)


def _open_browser(host: str, port: int) -> None:
    """Open the dashboard in the default browser after a short delay."""
    time.sleep(2.0)
    webbrowser.open(f"http://{host}:{port}")


def main() -> None:
    # Logging first — before any dashboard imports that may log
    from src.dashboard.utils.logging import configure_logging
    configure_logging()

    # Seed writable user data from bundle on first run
    _seed_user_data()

    from src.dashboard.app import app
    from src.dashboard.config import HOST, PORT

    print("=" * 60)
    print("  IRIS-D — Interactive Research & Insight Generation System")
    print(f"  Dashboard: http://{HOST}:{PORT}")
    print("  Press Ctrl+C to stop")
    print("=" * 60)

    threading.Thread(target=_open_browser, args=(HOST, PORT), daemon=True).start()
    app.run(host=HOST, port=PORT)


if __name__ == "__main__":
    main()
