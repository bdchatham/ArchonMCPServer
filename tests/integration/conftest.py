"""Conftest that stubs external dependencies unavailable in the test environment.

``archon_mcp.server`` imports ``mcp``, ``starlette``, and ``aphex_clients``
at module level. These packages are only available inside the container image,
so we inject lightweight stubs into ``sys.modules`` *before* any test imports
the server module.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


def _ensure_stub(dotted_name: str) -> types.ModuleType:
    """Insert a stub module for *dotted_name* (and all parent packages) into ``sys.modules``."""
    parts = dotted_name.split(".")
    for i in range(1, len(parts) + 1):
        partial = ".".join(parts[:i])
        if partial not in sys.modules:
            mod = types.ModuleType(partial)
            sys.modules[partial] = mod
    return sys.modules[dotted_name]


def _install_stubs() -> None:
    """Pre-populate ``sys.modules`` with stubs for missing runtime dependencies."""

    _ensure_stub("mcp")
    _ensure_stub("mcp.server")
    _ensure_stub("mcp.server.fastmcp")

    fast_mcp_mod = sys.modules["mcp.server.fastmcp"]
    mock_mcp_class = MagicMock(name="FastMCP")
    mock_mcp_instance = MagicMock(name="FastMCP()")
    mock_mcp_instance.tool.return_value = lambda fn: fn
    mock_mcp_instance.custom_route.return_value = lambda fn: fn
    mock_mcp_class.return_value = mock_mcp_instance
    fast_mcp_mod.FastMCP = mock_mcp_class  # type: ignore[attr-defined]

    _ensure_stub("starlette")
    _ensure_stub("starlette.requests")
    _ensure_stub("starlette.responses")
    starlette_req = sys.modules["starlette.requests"]
    starlette_resp = sys.modules["starlette.responses"]
    starlette_req.Request = MagicMock(name="Request")  # type: ignore[attr-defined]
    starlette_resp.JSONResponse = MagicMock(name="JSONResponse")  # type: ignore[attr-defined]

    _ensure_stub("aphex_clients")
    _ensure_stub("aphex_clients.query")
    aphex_query_mod = sys.modules["aphex_clients.query"]
    aphex_query_mod.QueryClient = MagicMock(name="QueryClient")  # type: ignore[attr-defined]


_install_stubs()
