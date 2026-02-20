"""
Centralised logging configuration for IRIS-D.

Call :func:`configure_logging` once at startup (e.g. in ``main.py``) to
set up structured console output for the whole application.  Individual
modules then just call ``logging.getLogger(__name__)`` as usual.

Usage::

    from src.dashboard.utils.logging import configure_logging
    configure_logging(level="DEBUG")
"""

from __future__ import annotations

import logging
import sys


_FORMATS = {
    "simple": "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    "verbose": "%(asctime)s  %(levelname)-8s  [%(name)s:%(lineno)d]  %(message)s",
}

_DEFAULT_LEVEL = "INFO"
_DEFAULT_FORMAT = "simple"


def configure_logging(
    level: str = _DEFAULT_LEVEL,
    fmt: str = _DEFAULT_FORMAT,
    stream=sys.stdout,
) -> None:
    """Configure the root logger with a consistent format.

    Parameters
    ----------
    level:
        Standard logging level string: "DEBUG", "INFO", "WARNING", "ERROR".
    fmt:
        Format preset key — "simple" (default) or "verbose".
    stream:
        Output stream (default ``sys.stdout``).
    """
    level_int = getattr(logging, level.upper(), logging.INFO)
    fmt_str = _FORMATS.get(fmt, _FORMATS[_DEFAULT_FORMAT])

    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(fmt_str, datefmt="%Y-%m-%d %H:%M:%S"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level_int)

    # Silence noisy third-party loggers
    for noisy in ("werkzeug", "urllib3", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).debug("Logging configured — level=%s", level.upper())


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper for ``logging.getLogger(name)``."""
    return logging.getLogger(name)
