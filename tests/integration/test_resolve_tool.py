"""Integration tests for the archon.resolve tool handler.

Tests exercise the resolve() function end-to-end with mocked ResolveClient
to verify code/doc ARN resolution, invalid ARN handling, not-found handling,
and service unavailability.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from archon_mcp.clients.exceptions import ServiceUnavailableError
from archon_mcp.models import ResolveResult

import archon_mcp.server as _server_mod


def _mock_resolve_client(resolve_side_effect: object) -> MagicMock:
    """Return a mock that replaces ``ResolveClient`` as an async context manager."""
    client_instance = AsyncMock()

    if isinstance(resolve_side_effect, BaseException) or (
        isinstance(resolve_side_effect, type)
        and issubclass(resolve_side_effect, BaseException)
    ):
        client_instance.resolve = AsyncMock(side_effect=resolve_side_effect)
    else:
        client_instance.resolve = AsyncMock(return_value=resolve_side_effect)

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=client_instance)
    context_manager.__aexit__ = AsyncMock(return_value=False)

    return MagicMock(return_value=context_manager)


class TestResolveCodeARN:
    """Verify resolution of code-type ARNs to file locations."""

    @pytest.mark.asyncio
    async def test_code_arn_resolves_to_file_and_line(self) -> None:
        resolve_result = ResolveResult(found=True, file_path="src/main.py", line_number=42)
        mock_constructor = _mock_resolve_client(resolve_result)

        with patch.object(_server_mod, "ResolveClient", mock_constructor):
            result = await _server_mod.resolve(
                arn="arn:archon:code:personal-work/ArchonAgent/src/main.py#hello"
            )

        assert result["success"] is True
        assert result["filePath"] == "src/main.py"
        assert result["lineNumber"] == 42

    @pytest.mark.asyncio
    async def test_code_arn_resolves_without_line_number(self) -> None:
        resolve_result = ResolveResult(found=True, file_path="src/config.py", line_number=None)
        mock_constructor = _mock_resolve_client(resolve_result)

        with patch.object(_server_mod, "ResolveClient", mock_constructor):
            result = await _server_mod.resolve(
                arn="arn:archon:code:personal-work/ArchonAgent/src/config.py"
            )

        assert result["success"] is True
        assert result["filePath"] == "src/config.py"
        assert result["lineNumber"] is None


class TestResolveDocARN:
    """Verify resolution of doc-type ARNs to file locations."""

    @pytest.mark.asyncio
    async def test_doc_arn_resolves_to_file(self) -> None:
        resolve_result = ResolveResult(
            found=True, file_path=".kiro/docs/architecture.md", line_number=10
        )
        mock_constructor = _mock_resolve_client(resolve_result)

        with patch.object(_server_mod, "ResolveClient", mock_constructor):
            result = await _server_mod.resolve(
                arn="arn:archon:doc:personal-work/ArchonAgent/.kiro/docs/architecture.md#overview"
            )

        assert result["success"] is True
        assert result["filePath"] == ".kiro/docs/architecture.md"
        assert result["lineNumber"] == 10


class TestResolveInvalidARN:
    """Verify error handling for malformed ARN strings."""

    @pytest.mark.asyncio
    async def test_empty_arn_returns_format_error(self) -> None:
        result = await _server_mod.resolve(arn="")

        assert result["success"] is False
        assert "Invalid ARN format" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_prefix_returns_format_error(self) -> None:
        result = await _server_mod.resolve(arn="not-an-arn")

        assert result["success"] is False
        assert "arn:archon:" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_type_returns_format_error(self) -> None:
        result = await _server_mod.resolve(arn="arn:archon:unknown:ws/pkg/path.py")

        assert result["success"] is False
        assert "Invalid ARN type" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_resource_path_returns_format_error(self) -> None:
        result = await _server_mod.resolve(arn="arn:archon:code:workspace")

        assert result["success"] is False
        assert "Invalid ARN format" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_arn_never_calls_resolve_client(self) -> None:
        mock_constructor = _mock_resolve_client(ResolveResult(found=False))

        with patch.object(_server_mod, "ResolveClient", mock_constructor):
            await _server_mod.resolve(arn="bad-arn")

        mock_constructor.assert_not_called()


class TestResolveNotFound:
    """Verify handling when a valid ARN does not resolve to a resource."""

    @pytest.mark.asyncio
    async def test_not_found_returns_failure(self) -> None:
        resolve_result = ResolveResult(found=False)
        mock_constructor = _mock_resolve_client(resolve_result)

        with patch.object(_server_mod, "ResolveClient", mock_constructor):
            result = await _server_mod.resolve(
                arn="arn:archon:code:personal-work/ArchonAgent/src/missing.py#gone"
            )

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestResolveServiceUnavailability:
    """Verify graceful handling when the Code Graph service is down."""

    @pytest.mark.asyncio
    async def test_service_unavailable_returns_error(self) -> None:
        error = ServiceUnavailableError(
            service_name="Code Graph", details="Connection refused"
        )
        mock_constructor = _mock_resolve_client(error)

        with patch.object(_server_mod, "ResolveClient", mock_constructor):
            result = await _server_mod.resolve(
                arn="arn:archon:code:personal-work/ArchonAgent/src/main.py#hello"
            )

        assert result["success"] is False
        assert "unavailable" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_failure(self) -> None:
        error = RuntimeError("unexpected internal failure")
        mock_constructor = _mock_resolve_client(error)

        with patch.object(_server_mod, "ResolveClient", mock_constructor):
            result = await _server_mod.resolve(
                arn="arn:archon:code:personal-work/ArchonAgent/src/main.py#hello"
            )

        assert result["success"] is False
        assert "Resolution failed" in result["error"]
