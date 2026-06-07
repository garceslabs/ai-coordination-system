"""Structured JSON logging utilities for the coordination system."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable


_RESERVED_LOG_KEYS = frozenset({
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "id", "levelname", "levelno", "lineno", "message",
    "module", "msecs", "msg", "name", "pathname", "process",
    "processName", "relativeCreated", "stack_info", "thread", "threadName",
})


class StructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_KEYS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a logger pre-configured with structured JSON output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def timed(logger: logging.Logger | None = None) -> Callable:
    """Decorator that logs method name and wall-clock duration on exit."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _log = logger or logging.getLogger(func.__module__)
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = round(time.perf_counter() - start, 4)
                _log.info(f"{func.__name__} completed", extra={"duration_seconds": elapsed})
                return result
            except Exception:
                elapsed = round(time.perf_counter() - start, 4)
                _log.error(f"{func.__name__} failed", extra={"duration_seconds": elapsed}, exc_info=True)
                raise
        return wrapper
    return decorator
