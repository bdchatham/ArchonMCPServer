"""CLI entrypoint for running the MCP server."""

import os
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from .server import mcp


async def health(request):
    return JSONResponse({"status": "healthy"})


# Create Starlette app with health endpoint and MCP server
app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=mcp.streamable_http_app(json_response=True, stateless_http=True, streamable_http_path="/mcp")),
    ]
)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
