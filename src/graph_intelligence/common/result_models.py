"""Envelope response models and standard error codes."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    UNKNOWN_ENTITY = "UNKNOWN_ENTITY"
    UNAUTHORIZED_SCOPE = "UNAUTHORIZED_SCOPE"
    INVALID_RELATIONSHIP = "INVALID_RELATIONSHIP"
    MALFORMED_RECORD = "MALFORMED_RECORD"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    DEPTH_LIMIT = "DEPTH_LIMIT"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    NO_MATCH = "NO_MATCH"


def ok_response(**kwargs: Any) -> Dict[str, Any]:
    """Construct a standardized success envelope."""
    payload: Dict[str, Any] = {"ok": True}
    payload.update(kwargs)
    return payload


def error_response(error_code: ErrorCode | str, message: str, **kwargs: Any) -> Dict[str, Any]:
    """Construct a standardized error envelope."""
    code_val = error_code.value if isinstance(error_code, ErrorCode) else str(error_code)
    payload: Dict[str, Any] = {
        "ok": False,
        "error_code": code_val,
        "message": message,
    }
    payload.update(kwargs)
    return payload
