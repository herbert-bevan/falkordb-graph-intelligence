"""Unit tests for deterministic memory retrieval scoring."""

from graph_intelligence.common.ids import utcnow_iso
from graph_intelligence.memory.retrieval import score_summary


def test_scoring_weights():
    candidate = {
        "id": "sum_test_1",
        "title": "Architecture decision for MCP and FalkorDB",
        "summary": "We decided to use three Python MCP services over a shared FalkorDB graph. Memory saves summaries per user.",
        "keywords": ["falkordb", "mcp", "memory", "architecture"],
        "entity_keys": ["PaymentService"],
        "linked_entities": [{"id": "svc-payment", "name": "PaymentService", "label": "Service"}],
        "project_id": "proj-payment-reliability",
        "project_name": "Payment Reliability",
        "status": "active",
        "created_at": utcnow_iso(),
    }

    # Query with exact entity match (+5), project match (+4), keyword phrase (+3), and token overlap
    score, matched_kws, matched_ents, reason = score_summary(
        candidate=candidate,
        query_text="What did we decide about FalkorDB and MCP memory architecture?",
        query_keywords=["falkordb", "mcp", "memory"],
        query_entities=["PaymentService"],
        query_project="Payment Reliability",
    )

    # Score breakdown:
    # Project: +4
    # Entity: +5
    # Keyword phrases: 3 keywords * 3 = +9
    # Token overlaps: multiple tokens
    # Total should easily exceed 15.0
    assert score > 15.0
    assert "PaymentService" in matched_ents
    assert "falkordb" in matched_kws
    assert "mcp" in matched_kws
    assert "memory" in matched_kws
    assert "project_match(+4.0)" in reason


def test_superseded_penalty():
    candidate_active = {
        "id": "sum_act",
        "title": "Test Title",
        "summary": "Test summary",
        "keywords": ["mcp"],
        "status": "active",
        "created_at": utcnow_iso(),
    }
    candidate_superseded = {
        "id": "sum_sup",
        "title": "Test Title",
        "summary": "Test summary",
        "keywords": ["mcp"],
        "status": "superseded",
        "created_at": utcnow_iso(),
    }

    score_act, _, _, _ = score_summary(candidate_active, "mcp query", ["mcp"], [])
    score_sup, _, _, _ = score_summary(candidate_superseded, "mcp query", ["mcp"], [])

    assert round(score_act - score_sup, 2) == 3.0


def test_unrelated_query_scores_low():
    candidate = {
        "id": "sum_test_2",
        "title": "FalkorDB setup",
        "summary": "Setting up graph and indexes",
        "keywords": ["falkordb", "graph", "database"],
        "status": "active",
        "created_at": "2026-01-01T00:00:00Z",
    }
    # Completely unrelated query
    score, _, _, _ = score_summary(
        candidate=candidate,
        query_text="What is the best Italian pasta recipe?",
        query_keywords=["cooking", "pasta", "recipe"],
        query_entities=[],
    )
    # Score must be below threshold 3.0
    assert score < 3.0
