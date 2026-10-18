"""Check FalkorDB connection script."""

import sys
from graph_intelligence.common.config import get_settings
from graph_intelligence.common.falkordb_client import GraphStore

def main():
    settings = get_settings()
    print(f"Connecting to FalkorDB at {settings.FALKORDB_HOST}:{settings.FALKORDB_PORT} (SSL={settings.FALKORDB_SSL})...")
    store = GraphStore(graph_name=settings.FALKORDB_GRAPH)
    try:
        ok = store.ping()
        if ok:
            print(f"Successfully connected to FalkorDB on graph '{settings.FALKORDB_GRAPH}'! [RETURN 1 = OK]")
            sys.exit(0)
        else:
            print("Ping returned unexpected result.", file=sys.stderr)
            sys.exit(1)
    except Exception as exc:
        print(f"Connection failed: {exc}", file=sys.stderr)
        print("Please check your .env credentials.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
