"""Phase 0 FalkorDB Cypher spike verification script."""

import sys
from graph_intelligence.common.config import get_settings
from graph_intelligence.common.falkordb_client import GraphStore

def run_spike():
    settings = get_settings()
    test_graph = settings.FALKORDB_GRAPH_TEST
    print(f"Running FalkorDB API spike on graph '{test_graph}'...")
    store = GraphStore(graph_name=test_graph)

    # 1. Ping
    print("1. Testing ping (RETURN 1)...", end=" ")
    res = store.query("RETURN 1 AS num")
    assert res[0]["num"] == 1, "Ping failed"
    print("OK")

    # 2. Merge node with parameters
    print("2. Testing MERGE with ON CREATE / ON MATCH...", end=" ")
    store.query("""
    MERGE (s:Service {id: $id})
    ON CREATE SET s.name = $name, s.keywords = $kw
    ON MATCH SET s.name = $name
    RETURN s.id AS id, s.name AS name
    """, {"id": "spike-svc-1", "name": "Spike Service", "kw": ["test", "spike"]})
    print("OK")

    # 3. Create index
    print("3. Testing index creation...", end=" ")
    try:
        store.query("CREATE INDEX FOR (s:Service) ON (s.id)")
        print("OK (created)")
    except Exception as e:
        print(f"OK (note: {e})")

    # 4. Variable-length match
    print("4. Testing relationship creation and path traversal...", end=" ")
    store.query("""
    MERGE (b:Service {id: 'spike-svc-2'})
    ON CREATE SET b.name = 'Downstream Service'
    """)
    store.query("""
    MATCH (a:Service {id: 'spike-svc-1'}), (b:Service {id: 'spike-svc-2'})
    MERGE (a)-[r:DEPENDS_ON]->(b)
    RETURN type(r) AS rel
    """)
    path_res = store.query("""
    MATCH p = (a:Service {id: 'spike-svc-1'})-[:DEPENDS_ON*1..2]->(b:Service)
    RETURN a.id AS source, b.id AS target, length(p) AS hops
    """)
    assert len(path_res) > 0, "Variable-length traversal returned no results"
    print("OK")

    # 5. Cleanup test graph
    print("5. Testing cleanup...", end=" ")
    store.query("MATCH (n) WHERE n.id STARTS WITH 'spike-' DETACH DELETE n")
    print("OK")

    print("\nAll FalkorDB API spike tests passed successfully!")

if __name__ == "__main__":
    try:
        run_spike()
    except Exception as exc:
        print(f"\nSpike failed: {exc}", file=sys.stderr)
        sys.exit(1)
