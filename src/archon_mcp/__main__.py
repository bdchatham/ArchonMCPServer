"""CLI entrypoint for running the MCP server."""

import os
import uvicorn
from .server import app


def main():
    """Run the MCP server."""
    port = int(os.getenv("PORT", "8090"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
