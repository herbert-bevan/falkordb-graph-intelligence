"""Unit tests verifying that NO MCP tool accepts user_id in its schema."""

from graph_intelligence.company_brain.mcp_server import mcp as brain_mcp
from graph_intelligence.memory.mcp_server import mcp as memory_mcp
from graph_intelligence.reasoning.mcp_server import mcp as reasoning_mcp


def test_tool_counts():
    assert len(reasoning_mcp._tool_manager._tools) == 4
    assert len(memory_mcp._tool_manager._tools) == 5
    assert len(brain_mcp._tool_manager._tools) == 5


def test_no_user_id_in_any_tool_schema():
    servers = [reasoning_mcp, memory_mcp, brain_mcp]
    for server in servers:
        for tool_name, tool in server._tool_manager._tools.items():
            params = getattr(tool, "parameters", {}) or {}
            props = params.get("properties", {})
            assert "user_id" not in props, f"Tool '{tool_name}' in server '{server.name}' exposes user_id in parameters!"
            required = params.get("required", [])
            assert "user_id" not in required, f"Tool '{tool_name}' in server '{server.name}' lists user_id as required!"
