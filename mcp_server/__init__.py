"""MCP server package — exposes Forensic LLM Wiki capabilities as tools.

The agent-facing surface is in ``mcp_server.tools``. ``mcp_server.server``
wires those tools into a FastMCP server (requires the optional ``mcp``
package). Tests import ``mcp_server.tools`` directly and never need the
MCP SDK installed.
"""

from . import schemas, tools  # noqa: F401

__all__ = ["schemas", "tools"]
