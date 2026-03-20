"""
Centralised logging configuration for the trading bot.

Log levels:
  - Console : INFO  (human-readable, coloured where supported)
  - File    : DEBUG (full detail including raw API payloads)

Usage
-----
    from bot.logging_config import get_logger
    logger = get_logger(__name__)
"""

import logging
import logging.handlers
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
LOG_DIR = Path(os.environ.get("BOT_LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / "trading_bot.log"

# ── Formatters ─────────────────────────────────────────────────────────────────
FILE_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
)
CONSOLE_FORMAT = "%(asctime)s  %(levelname)-8s  %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False  # guard against repeated setup


def configure_logging(log_level_console: int = logging.INFO) -> None:
    """
    Configure root logger once.  Call this at application startup.

    Parameters
    ----------
    log_level_console:
        Minimum level shown on stdout (default INFO). The log file always
        captures DEBUG and above.
    """
    global _configured
    if _configured:
        return
    _configured = True

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # capture everything; handlers filter

    # ── File handler (rotating, 5 MB × 3 backups) ─────────────────────────────
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(fh)

    # ── Console handler ────────────────────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setLevel(log_level_console)
    ch.setFormatter(logging.Formatter(CONSOLE_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(ch)

    # Quieten the noisy requests/urllib3 loggers in console
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, ensuring global config is applied."""
    configure_logging()
    return logging.getLogger(name)
