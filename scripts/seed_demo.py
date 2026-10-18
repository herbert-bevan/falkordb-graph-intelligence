"""Seed demo script."""

import sys
from graph_intelligence.common.config import get_settings
from graph_intelligence.seed.seed_company_graph import seed_company_graph

def main():
    settings = get_settings()
    print(f"Seeding demo graph '{settings.FALKORDB_GRAPH}'...")
    try:
        counts = seed_company_graph(settings.FALKORDB_GRAPH)
        print(f"Seed complete: {counts['company_nodes']} company nodes, {counts['user_nodes']} users, {counts['relationships']} relationships.")
    except Exception as exc:
        print(f"Seeding failed: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
