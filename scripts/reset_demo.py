"""Destructive reset script for demo or test graphs."""

import sys
import argparse
from graph_intelligence.common.config import get_settings
from graph_intelligence.common.falkordb_client import GraphStore

def main():
    parser = argparse.ArgumentParser(description="Destructively reset a FalkorDB demo or test graph.")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive graph deletion")
    parser.add_argument("--graph", type=str, default=None, help="Target graph name (defaults to FALKORDB_GRAPH)")
    args = parser.parse_args()

    if not args.yes:
        print("ERROR: Destructive reset requires --yes flag to confirm.", file=sys.stderr)
        sys.exit(1)

    settings = get_settings()
    target_graph = args.graph or settings.FALKORDB_GRAPH

    # Safety check: must end with _demo or _test
    if not (target_graph.endswith("_demo") or target_graph.endswith("_test")):
        print(f"ERROR: Graph name '{target_graph}' does not end in '_demo' or '_test'. Aborting for safety.", file=sys.stderr)
        sys.exit(1)

    print(f"Resetting graph '{target_graph}'...")
    store = GraphStore(graph_name=target_graph)
    store.delete_graph()
    print(f"Graph '{target_graph}' successfully cleared.")

if __name__ == "__main__":
    main()
