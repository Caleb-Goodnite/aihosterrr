"""Centralized logging configuration."""

from __future__ import annotations

import logging
import sys

from config import DEBUG


def configure_logging() -> None:
    level = logging.DEBUG if DEBUG else logging.INFO
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
