"""Structured logging configuration for flood-sentinel."""

import logging
import sys
from typing import Optional


DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
) -> logging.Logger:
    """Set up and return a configured logger with standard stream handler."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """Convenience getter for a configured logger."""
    return setup_logger(name)
