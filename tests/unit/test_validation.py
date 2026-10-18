"""Unit tests for input validation and secret scanning."""

import pytest
from graph_intelligence.common.errors import ValidationError
from graph_intelligence.common.validation import (
    scan_for_secrets,
    validate_int_range,
    validate_list_size,
    validate_text_length,
)


def test_scan_for_secrets_detects_patterns():
    # Passwords
    with pytest.raises(ValidationError):
        scan_for_secrets("Here is the config: password=SuperSecret123!")

    # API keys
    with pytest.raises(ValidationError):
        scan_for_secrets("api_key: abcdef1234567890abcdef1234567890")

    # Bearer tokens
    with pytest.raises(ValidationError):
        scan_for_secrets("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz")

    # OpenAI sk tokens
    with pytest.raises(ValidationError):
        scan_for_secrets("sk-abcdefghijklmnopqrstuvwxyz1234567890")

    # Private key
    with pytest.raises(ValidationError):
        scan_for_secrets("-----BEGIN RSA PRIVATE KEY-----")


def test_scan_for_secrets_clean_input():
    # Normal architecture discussion should not raise
    scan_for_secrets("We chose three Python MCP servers over a shared FalkorDB graph.")
    scan_for_secrets(None)
    scan_for_secrets("")


def test_validate_text_length():
    validate_text_length("Short text", "field", 100)
    with pytest.raises(ValidationError):
        validate_text_length("A" * 121, "title", 120)


def test_validate_list_size():
    validate_list_size(["a", "b"], "list", 5)
    with pytest.raises(ValidationError):
        validate_list_size([str(i) for i in range(25)], "keywords", 20)


def test_validate_int_range():
    assert validate_int_range(3, "depth", 1, 4) == 3
    with pytest.raises(ValidationError):
        validate_int_range(5, "depth", 1, 4)
    with pytest.raises(ValidationError):
        validate_int_range(0, "depth", 1, 4)
