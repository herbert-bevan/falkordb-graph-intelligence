"""Unit tests verifying demo_data.json schema integrity and counts."""

from graph_intelligence.common.schema import (
    COMPANY_LABELS,
    MEMORY_LABELS,
    is_valid_relationship,
)
from graph_intelligence.seed.seed_company_graph import load_demo_data


def test_demo_data_counts():
    data = load_demo_data()
    company_nodes = data.get("company_nodes", [])
    user_nodes = data.get("user_nodes", [])
    relationships = data.get("relationships", [])

    assert len(company_nodes) == 31, f"Expected 31 company nodes, got {len(company_nodes)}"
    assert len(user_nodes) == 2, f"Expected 2 user nodes, got {len(user_nodes)}"
    assert len(relationships) == 53, f"Expected 53 relationships, got {len(relationships)}"


def test_demo_data_schema_labels_and_edges():
    data = load_demo_data()
    node_labels = {}

    for n in data.get("company_nodes", []):
        assert n["label"] in COMPANY_LABELS, f"Invalid company label {n['label']}"
        node_labels[n["id"]] = n["label"]

    for u in data.get("user_nodes", []):
        assert u["label"] in MEMORY_LABELS, f"Invalid user label {u['label']}"
        node_labels[u["id"]] = u["label"]

    for r in data.get("relationships", []):
        rel_type = r["type"]
        from_id = r["from_id"]
        to_id = r["to_id"]

        assert from_id in node_labels, f"Relationship from_id '{from_id}' not found in nodes"
        assert to_id in node_labels, f"Relationship to_id '{to_id}' not found in nodes"

        from_label = node_labels[from_id]
        to_label = node_labels[to_id]
        assert is_valid_relationship(rel_type, from_label, to_label), (
            f"Invalid relationship ({from_label})-[:{rel_type}]->({to_label})"
        )
