"""CLI entrypoint for running the MCP server."""

from .server import mcp

if __name__ == "__main__":
    mcp.run()
