"""Schema definitions, label allowlists, and relationship rules."""

from typing import Set, Tuple, Dict, List

# Allowed node labels
COMPANY_LABELS: Set[str] = {
    "Company",
    "Team",
    "Person",
    "Project",
    "Service",
    "Feature",
    "Incident",
    "Decision",
    "Document",
}

MEMORY_LABELS: Set[str] = {
    "User",
    "Session",
    "SessionSummary",
    "Task",
}

ALL_LABELS: Set[str] = COMPANY_LABELS | MEMORY_LABELS

# Entity labels that can be referenced/linked by SessionSummary or searched by company tools
SEARCHABLE_COMPANY_LABELS: Set[str] = {
    "Service",
    "Feature",
    "Incident",
    "Decision",
    "Document",
    "Person",
    "Team",
    "Project",
}

# (relationship_type, from_label, to_label) allowlist
ALLOWED_RELATIONSHIPS: Set[Tuple[str, str, str]] = {
    ("BELONGS_TO", "Team", "Company"),
    ("MEMBER_OF", "Person", "Team"),
    ("OWNS", "Person", "Service"),
    ("PART_OF", "Service", "Project"),
    ("DEPENDS_ON", "Service", "Service"),
    ("IMPLEMENTS", "Service", "Feature"),
    ("AFFECTS", "Incident", "Service"),
    ("AFFECTS", "Decision", "Service"),
    ("MADE_FOR", "Decision", "Project"),
    ("SUPPORTED_BY", "Decision", "Document"),
    ("RESPONDS_TO", "Decision", "Incident"),
    ("DESCRIBES", "Document", "Service"),
    ("DESCRIBES", "Document", "Feature"),
    ("DESCRIBES", "Document", "Incident"),
    ("DESCRIBES", "Document", "Decision"),
    ("OWNS_MEMORY", "User", "SessionSummary"),
    ("FROM_SESSION", "SessionSummary", "Session"),
    ("ABOUT_PROJECT", "SessionSummary", "Project"),
    ("MENTIONS_ENTITY", "SessionSummary", "Service"),
    ("MENTIONS_ENTITY", "SessionSummary", "Incident"),
    ("MENTIONS_ENTITY", "SessionSummary", "Decision"),
    ("MENTIONS_ENTITY", "SessionSummary", "Feature"),
    ("MENTIONS_ENTITY", "SessionSummary", "Document"),
    ("MENTIONS_ENTITY", "SessionSummary", "Person"),
    ("MENTIONS_ENTITY", "SessionSummary", "Team"),
    ("SUPERSEDES", "SessionSummary", "SessionSummary"),
    ("HAS_TASK", "SessionSummary", "Task"),
}

# Valid sources for nodes/edges
ALLOWED_SOURCES: Set[str] = {
    "seed",
    "structured_ingestion",
    "llm_mcp_write",
}


def is_valid_label(label: str) -> bool:
    """Check if label is in allowed labels."""
    return label in ALL_LABELS


def is_company_label(label: str) -> bool:
    """Check if label is purely a company label (not memory/user)."""
    return label in COMPANY_LABELS


def is_valid_relationship(rel_type: str, from_label: str, to_label: str) -> bool:
    """Validate that (rel_type, from_label, to_label) is explicitly allowed."""
    return (rel_type, from_label, to_label) in ALLOWED_RELATIONSHIPS


def validate_relationship_type(rel_type: str) -> bool:
    """Check if relationship type is recognized anywhere in allowed relationships."""
    return any(t == rel_type for t, _, _ in ALLOWED_RELATIONSHIPS)
