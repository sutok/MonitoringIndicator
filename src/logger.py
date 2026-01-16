"""Logging configuration module."""

import logging
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "monitoring_indicator",
    log_file: Optional[str] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Set up and configure logger.

    Args:
        name: Logger name.
        log_file: Path to log file. If None, logs only to console.
        level: Logging level.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Format
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = TimedRotatingFileHandler(
            log_path,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Default logger instance
logger = setup_logger()
