"""CLI entrypoint for running the MCP server."""

import os
from .server import mcp

if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
