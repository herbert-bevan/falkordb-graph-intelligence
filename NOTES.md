# Implementation Notes & Platform Deviations

*Deviations from the master specification and platform-specific observations are recorded here.*

- Environment: Python 3.14.0 on Windows (x86_64).
- MCP SDK: Pinned to `mcp>=1.30.0,<2` to use `from mcp.server.fastmcp import FastMCP`, matching the specification architecture (FastMCP was renamed in mcp 2.x).
- FalkorDB Header Parsing: In `falkordb` Python SDK (v1.8.0), `QueryResult.header` returns elements as `[col_type, col_name]`; adapted in `GraphStore.query()` to extract the column name at index 1 and decode bytes to UTF-8.
- Phase 0 API Spike: Verified against FalkorDB Cloud on `atlaspay_test`. `MERGE`, parameters, variable-length matching `[r IN relationships(p) | type(r)]`, `[n IN nodes(p) | n.id]`, and index creation all passed with native Cypher support.
- Shortest Path: FalkorDB returned `ResponseError: FalkorDB does not currently support undirected shortestPath traversals`; adapted `find_graph_path` to use the BFS fallback in Python with bounded 1-hop neighbor queries as explicitly specified in Phase 0 fallback table.
