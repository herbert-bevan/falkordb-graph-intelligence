"""Input validation, bounds enforcement, and secret scanning."""

import re
import math
from typing import Any, List, Optional
from graph_intelligence.common.errors import ValidationError

# Regex patterns for secret detection
SECRET_PATTERNS = [
    re.compile(r"password\s*[:=]", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[:=]", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{15,}", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"-----BEGIN[ A-Z0-9_-]*PRIVATE KEY-----"),
    re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"),
    re.compile(r"\bglpat-[a-zA-Z0-9\-]{20,}\b"),
]

# High entropy token regex (32+ continuous alphanumeric characters that look like keys/hashes)
HIGH_ENTROPY_TOKEN_PATTERN = re.compile(r"\b[A-Za-z0-9+/=_-]{32,}\b")


def _shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy for a string."""
    if not s:
        return 0.0
    probabilities = [n / len(s) for n in {c: s.count(c) for c in set(s)}.values()]
    return -sum(p * math.log2(p) for p in probabilities)


def scan_for_secrets(text: Optional[str]) -> None:
    """
    Scan string for secret-like tokens or sensitive patterns.
    Raises ValidationError if a suspected secret is found.
    """
    if not text:
        return

    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise ValidationError("Payload contains sensitive or secret-like pattern")

    # Check high entropy words
    for token in HIGH_ENTROPY_TOKEN_PATTERN.findall(text):
        if len(token) >= 32 and _shannon_entropy(token) > 4.2:
            raise ValidationError("Payload contains high-entropy secret-like token")


def validate_text_length(text: Optional[str], field_name: str, max_chars: int) -> None:
    """Validate character length for text fields."""
    if text and len(text) > max_chars:
        raise ValidationError(f"{field_name} exceeds maximum length of {max_chars} characters")


def validate_list_size(items: Optional[List[Any]], field_name: str, max_items: int) -> None:
    """Validate item count in lists."""
    if items and len(items) > max_items:
        raise ValidationError(f"{field_name} exceeds maximum count of {max_items} items")


def validate_int_range(val: int, field_name: str, min_val: int, max_val: int) -> int:
    """Validate and clamp or reject integer ranges."""
    if val < min_val or val > max_val:
        raise ValidationError(f"{field_name} must be between {min_val} and {max_val}, got {val}")
    return val
