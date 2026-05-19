# Logging utilities
"""
ClientIQ — Structured Logging
Uses loguru for rich, structured log output with file rotation.
"""

import sys
import os
from loguru import logger
from backend.utils.config import settings


def setup_logger() -> None:
    """Configure loguru logger with console and file handlers."""
    # Remove default handler
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Console output
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True,
    )

    # File output with rotation
    os.makedirs("logs", exist_ok=True)
    logger.add(
        settings.log_file,
        format=log_format,
        level=settings.log_level,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,  # thread-safe
    )

    logger.info("ClientIQ logger initialized | env={}", settings.app_env)


# Initialize on import
setup_logger()

__all__ = ["logger"]