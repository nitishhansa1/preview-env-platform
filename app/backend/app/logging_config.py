"""
Structured JSON Logging Configuration
=====================================
Purpose:
  Formats all application logs as single-line JSON objects, making them easy to
  ingest, parse, and search in modern log aggregators (e.g., Loki, CloudWatch, Datadog).
"""

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs JSON strings with standardized fields.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include exception tracebacks if present
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        # Include extra context dictionary if provided
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_object.update(record.extra)

        return json.dumps(log_object)


def setup_logging(log_level: str = "INFO"):
    """
    Configures the root logger with the JSONFormatter and writes to stdout.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Clear existing handlers to avoid duplicate log entries
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Set third-party loggers to a reasonable level to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
