"""Unit tests for schema and relationship rules."""

from graph_intelligence.common.schema import (
    ALL_LABELS,
    COMPANY_LABELS,
    MEMORY_LABELS,
    is_company_label,
    is_valid_label,
    is_valid_relationship,
    validate_relationship_type,
)


def test_allowed_labels():
    assert "Company" in COMPANY_LABELS
    assert "Service" in COMPANY_LABELS
    assert "SessionSummary" in MEMORY_LABELS
    assert "User" in MEMORY_LABELS
    assert is_valid_label("Service")
    assert is_valid_label("SessionSummary")
    assert not is_valid_label("UnknownLabel")


def test_company_vs_memory_isolation():
    assert is_company_label("Service")
    assert is_company_label("Incident")
    assert not is_company_label("SessionSummary")
    assert not is_company_label("User")


def test_allowed_relationships():
    assert is_valid_relationship("DEPENDS_ON", "Service", "Service")
    assert is_valid_relationship("OWNS", "Person", "Service")
    assert is_valid_relationship("OWNS_MEMORY", "User", "SessionSummary")
    assert is_valid_relationship("SUPERSEDES", "SessionSummary", "SessionSummary")

    # Disallowed relationships
    assert not is_valid_relationship("OWNS", "Service", "Person")
    assert not is_valid_relationship("OWNS_MEMORY", "Service", "SessionSummary")
    assert not is_valid_relationship("DEPENDS_ON", "User", "Service")


def test_validate_relationship_type():
    assert validate_relationship_type("DEPENDS_ON")
    assert validate_relationship_type("AFFECTS")
    assert not validate_relationship_type("RANDOM_REL")
