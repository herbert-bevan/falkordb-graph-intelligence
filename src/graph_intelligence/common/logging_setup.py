"""Structured JSON logging to stderr for stdio MCP servers."""

import json
import logging
import sys
import time
from contextlib import contextmanager
from typing import Generator, Optional
from uuid import uuid4


class StderrJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON to stderr."""
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "structured_data"):
            payload.update(record.structured_data)  # type: ignore
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    """Get a logger configured exclusively to stream JSON to stderr."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(StderrJsonFormatter())
        logger.addHandler(handler)

    return logger


_app_logger = get_logger("graph_intelligence")


@contextmanager
def log_operation(tool_name: str) -> Generator[str, None, None]:
    """
    Context manager to log operation lifecycle to stderr in structured JSON.
    Emits duration, status, and error_code if failed.
    Never logs sensitive text, secrets, or raw user queries.
    """
    op_id = uuid4().hex[:8]
    start_time = time.perf_counter()
    status = "SUCCESS"
    error_code: Optional[str] = None

    try:
        yield op_id
    except Exception as exc:
        status = "ERROR"
        error_code = getattr(exc, "error_code", exc.__class__.__name__)
        raise
    finally:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        payload = {
            "op_id": op_id,
            "tool": tool_name,
            "duration_ms": duration_ms,
            "status": status,
        }
        if error_code:
            payload["error_code"] = error_code
        record = _app_logger.makeRecord(
            name=_app_logger.name,
            level=logging.INFO if status == "SUCCESS" else logging.ERROR,
            fn="",
            lno=0,
            msg=f"Operation {tool_name} completed with {status}",
            args=(),
            exc_info=None,
        )
        record.structured_data = payload  # type: ignore
        _app_logger.handle(record)
