"""Integration tests for seed loading and idempotency."""

import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from graph_intelligence.common.config import get_settings
from graph_intelligence.common.errors import DatabaseUnavailable
from graph_intelligence.common.falkordb_client import GraphStore
from graph_intelligence.seed.seed_company_graph import seed_company_graph
from scripts.verify_seed import verify_seed


def test_seed_idempotency_and_verification():
    settings = get_settings()
    test_graph = settings.FALKORDB_GRAPH_TEST

    try:
        store = GraphStore(graph_name=test_graph)
        store.delete_graph()

        # First seed
        counts_1 = seed_company_graph(test_graph)
        assert counts_1["company_nodes"] == 31
        assert counts_1["user_nodes"] == 2
        assert counts_1["relationships"] == 53

        # Verify seed
        assert verify_seed(test_graph) is True

        # Second seed (idempotency check)
        counts_2 = seed_company_graph(test_graph)
        assert counts_2["company_nodes"] == 31
        assert counts_2["user_nodes"] == 2
        assert counts_2["relationships"] == 53

        # Verify counts remain identical
        assert verify_seed(test_graph) is True
    except DatabaseUnavailable as exc:
        pytest.skip(f"FalkorDB instance not reachable: {exc}")
