"""
Tab registry system for IRIS-D.

This module provides a plugin-style tab registration system that makes it trivial
to add new analysis tabs without modifying the core framework code.

To create a new tab:
  1. Create a new file in src/dashboard/tabs/ (e.g. my_tab.py)
  2. Subclass BaseTab and implement the required methods
  3. Call register_tab(MyTab()) at module level
  4. Import the module in this __init__.py

That's it — the tab will automatically appear in navigation and routing.
"""

from .registry import BaseTab, register_tab, get_all_tabs, get_tab

__all__ = ["BaseTab", "register_tab", "get_all_tabs", "get_tab"]
