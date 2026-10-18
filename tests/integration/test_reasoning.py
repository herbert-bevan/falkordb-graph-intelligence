"""Integration tests for Track 1 reasoning service."""

import pytest
from graph_intelligence.common.config import get_settings
from graph_intelligence.common.errors import DatabaseUnavailable
from graph_intelligence.reasoning.service import ReasoningService
from graph_intelligence.seed.seed_company_graph import seed_company_graph


@pytest.fixture(scope="module")
def reasoning_service():
    settings = get_settings()
    test_graph = settings.FALKORDB_GRAPH_TEST
    try:
        seed_company_graph(test_graph)
        return ReasoningService(graph_name=test_graph)
    except DatabaseUnavailable as exc:
        pytest.skip(f"FalkorDB instance not reachable: {exc}")


def test_find_service_dependencies(reasoning_service):
    res = reasoning_service.find_service_dependencies("PaymentService", direction="dependencies")
    assert res["ok"] is True
    assert res["matched_service"]["name"] == "PaymentService"
    dep_names = {c["service_name"] for c in res["connections"]}
    assert "LedgerService" in dep_names
    assert "RiskEngine" in dep_names
    assert "NotificationService" in dep_names


def test_analyze_change_impact_paymentservice(reasoning_service):
    res = reasoning_service.analyze_change_impact(
        target="PaymentService",
        target_type="Service",
        change_description="Update retry exponential backoff",
    )
    assert res["ok"] is True
    assert res["target"]["name"] == "PaymentService"

    # Dependents (API Gateway)
    dep_names = [d["service_name"] for d in res["dependents"]]
    assert "API Gateway" in dep_names

    # Dependencies (Ledger, RiskEngine, Notification)
    dependency_names = [d["service_name"] for d in res["dependencies"]]
    assert "LedgerService" in dependency_names
    assert "RiskEngine" in dependency_names
    assert "NotificationService" in dependency_names

    # Features
    feature_names = [f["name"] for f in res["features"]]
    assert "Idempotent Payment Processing" in feature_names
    assert "Bounded Retry Policy" in feature_names

    # Decisions
    decision_names = [d["name"] for d in res["decisions"]]
    assert any("ADR-014" in dn for dn in decision_names)
    assert any("ADR-021" in dn for dn in decision_names)
    assert any("ADR-027" in dn for dn in decision_names)

    # Incidents
    incident_codes = [i.get("code") for i in res["incidents"]]
    assert "INC-PAY-042" in incident_codes
    assert "INC-PAY-019" in incident_codes

    # Owners
    owner_names = [o["name"] for o in res["owners"]]
    assert "Maya Chen" in owner_names


def test_find_graph_path(reasoning_service):
    res = reasoning_service.find_graph_path("API Gateway", "LedgerService", max_hops=4)
    assert res["ok"] is True
    assert res["found"] is True
    assert res["length"] == 2
    node_names = [n["name"] for n in res["nodes"]]
    assert node_names == ["API Gateway", "PaymentService", "LedgerService"]
