"""ID generation and ISO-8601 timestamp utilities."""

from datetime import datetime, timezone
from uuid import uuid4


def new_id(prefix: str) -> str:
    """Generate a prefixed random ID."""
    clean_prefix = prefix.rstrip("_")
    return f"{clean_prefix}_{uuid4().hex[:12]}"


def utcnow_iso() -> str:
    """Generate a timezone-aware UTC ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).isoformat()
