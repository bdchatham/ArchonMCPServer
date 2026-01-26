"""CLI entrypoint for running the MCP server."""

import uvicorn
from .server import app


def main():
    """Run the MCP server."""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8090,
        log_level="info"
    )


if __name__ == "__main__":
    main()
