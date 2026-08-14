"""
HospitalOps AI — Structured logging configuration.
"""

import logging
import sys
from typing import Literal


def configure_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
) -> None:
    """
    Configure application-wide logging.

    Outputs structured log records to stdout.
    Uses a format that is both human-readable in development
    and parseable by log aggregation systems in production.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicate output
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
