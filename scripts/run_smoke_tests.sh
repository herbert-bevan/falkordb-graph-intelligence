#!/usr/bin/env bash
set -e

echo "=== Running Unit Tests ==="
pytest tests/unit -v

echo "=== Running Integration Tests ==="
pytest tests/integration -v

echo "=== Running MCP Smoke Tests ==="
pytest tests/mcp_smoke -v

echo "=== All Tests Passed Successfully ==="
