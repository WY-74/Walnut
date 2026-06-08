import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_configured = False


def configure_logging(service_name: str, log_file: str | None = None):
    global _configured

    logger = logging.getLogger()
    if _configured:
        return logging.getLogger(service_name)

    level = logging.INFO

    if log_file is None:
        log_file = os.getenv("LOG_FILE", "logs/walnut.log")
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(processName)s | %(name)s | %(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.propagate = False

    _configured = True
    return logging.getLogger(service_name)
