"""Structured logging with loguru. JSON to file + human to stdout.

Every helios module imports get_logger(__name__) instead of logging.getLogger.
This gives us:
  * JSON sink to /var/log/helios/helios.jsonl (one line per event, audit-grade)
  * Human-readable sink to stdout (for live ops + container logs)
  * Trade decisions get tagged extras so we can grep audit logs by client_order_id
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from loguru import logger as _logger

_CONFIGURED = False


def configure_logging(
    level: str = "INFO",
    json_path: str | Path | None = None,
) -> None:
    """Idempotent. Called once at process boot."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _logger.remove()

    # Human-readable stdout
    _logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        backtrace=True,
        diagnose=False,  # don't dump locals — secrets risk
    )

    # JSON audit sink
    if json_path is None:
        json_path = os.getenv("HELIOS_LOG_JSON", "logs/helios.jsonl")
    if json_path:
        p = Path(json_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        _logger.add(
            p,
            level="DEBUG",
            serialize=True,
            rotation="100 MB",
            retention=30,
            enqueue=True,  # async-safe
        )

    _CONFIGURED = True


def get_logger(name: str) -> Any:
    if not _CONFIGURED:
        configure_logging()
    return _logger.bind(module=name)
