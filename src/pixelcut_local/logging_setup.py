"""Structured rotating logging setup for PixelCut Local."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
import sys

from pixelcut_local.storage.paths import get_logs_dir


class SecretFilter(logging.Filter):
    """Filter that obscures sensitive values such as pairing tokens or keys."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # Redact token patterns if any accidentally leak into messages
        if "token=" in msg.lower() or "token:" in msg.lower() or "pairing_code" in msg.lower():
            # Replace token value representation
            record.msg = "[REDACTED_SECURITY_TOKEN_IN_LOG]"
            record.args = ()
        return True


def setup_logging(level: int = logging.INFO, log_filename: str = "pixelcut.log") -> logging.Logger:
    """Configure rotating file logging and console logging.

    Rotating file retains up to 5 backups of 5MB each.
    """
    root_logger = logging.getLogger()
    # Avoid duplicate handlers on re-initialization
    if getattr(root_logger, "_pixelcut_configured", False):
        return root_logger

    root_logger.setLevel(level)

    log_format = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(log_format)
    console_handler.addFilter(SecretFilter())
    root_logger.addHandler(console_handler)

    # Rotating File Handler
    try:
        logs_dir = get_logs_dir()
        log_file_path = logs_dir / log_filename
        file_handler = RotatingFileHandler(
            filename=str(log_file_path),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(log_format)
        file_handler.addFilter(SecretFilter())
        root_logger.addHandler(file_handler)
    except Exception as exc:
        print(f"Warning: Failed to setup rotating file logger: {exc}", file=sys.stderr)

    root_logger._pixelcut_configured = True
    return root_logger
