"""Structured logging, shared across the project.

Any part of the codebase that needs to log should use get_logger(__name__) rather
than calling print or creating its own logger by hand.
"""

from __future__ import annotations

import logging

from rich.logging import RichHandler

from quantbox.utils.config import settings

_CONFIGURED = False


def _configure_root_logger() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger, ready to use.

    Example:
        from quantbox.utils.logging import get_logger
        log = get_logger(__name__)
        log.info("Collection started")
    """
    _configure_root_logger()
    return logging.getLogger(name)
