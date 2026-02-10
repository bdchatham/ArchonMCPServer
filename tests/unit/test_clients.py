"""Unit tests for GraphClient and ResolveClient."""

import json

import httpx
import pytest

from archon_mcp.clients.exceptions import (
    GraphQLValidationError,
    ServiceUnavailableError,
)
from archon_mcp.clients.graph_client import GraphClient
from archon_mcp.clients.resolve_client import ResolveClient
from archon_mcp.models import GraphQueryOutput, ResolveResult


# ---------------------------------------------------------------------------
# GraphClient
# ---------------------------------------------------------------------------


class TestGraphClientExecute:
    """Verify GraphClient.execute handles success, validation errors, and connection failures."""

    @pytest.mark.asyncio
    async def test_successful_query(self) -> None:
        response_body = {"data": {"node": {"arn": "arn:archon:code:ws/pkg/f.py"}}}
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=response_body)
        )

        async with GraphClient(base_url="http://graph:8080") as client:
            client._client = httpx.AsyncClient(transport=transport, base_url="http://graph:8080")
            result = await client.execute("{ node(arn: \"...\") { arn } }")

        assert isinstance(result, GraphQueryOutput)
        assert result.data == {"node": {"arn": "arn:archon:code:ws/pkg/f.py"}}
        assert result.errors is None

    @pytest.mark.asyncio
    async def test_graphql_validation_error_raises(self) -> None:
        response_body = {
            "data": None,
            "errors": [{"message": "Cannot query field 'bad'", "locations": [{"line": 1, "column": 3}]}],
        }
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=response_body)
        )

        async with GraphClient(base_url="http://graph:8080") as client:
            client._client = httpx.AsyncClient(transport=transport, base_url="http://graph:8080")
            with pytest.raises(GraphQLValidationError) as exc_info:
                await client.execute("{ bad }")

        assert "Cannot query field" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_connection_error_raises_service_unavailable(self) -> None:
        def raise_connect_error(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        transport = httpx.MockTransport(raise_connect_error)

        async with GraphClient(base_url="http://graph:8080") as client:
            client._client = httpx.AsyncClient(transport=transport, base_url="http://graph:8080")
            with pytest.raises(ServiceUnavailableError) as exc_info:
                await client.execute("{ node(arn: \"...\") { arn } }")

        assert exc_info.value.service_name == "Code Graph"

    @pytest.mark.asyncio
    async def test_non_validation_errors_returned_in_output(self) -> None:
        response_body = {
            "data": None,
            "errors": [{"message": "Internal server error"}],
        }
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=response_body)
        )

        async with GraphClient(base_url="http://graph:8080") as client:
            client._client = httpx.AsyncClient(transport=transport, base_url="http://graph:8080")
            result = await client.execute("{ node(arn: \"...\") { arn } }")

        assert result.data is None
        assert result.errors is not None
        assert result.errors[0].message == "Internal server error"

    @pytest.mark.asyncio
    async def test_variables_sent_in_payload(self) -> None:
        captured_body: dict = {}

        def capture_request(req: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(req.content))
            return httpx.Response(200, json={"data": {}})

        transport = httpx.MockTransport(capture_request)

        async with GraphClient(base_url="http://graph:8080") as client:
            client._client = httpx.AsyncClient(transport=transport, base_url="http://graph:8080")
            await client.execute("query($a: ID!) { node(arn: $a) { arn } }", variables={"a": "test"})

        assert captured_body["variables"] == {"a": "test"}

    @pytest.mark.asyncio
    async def test_context_manager_required(self) -> None:
        client = GraphClient(base_url="http://graph:8080")
        with pytest.raises(RuntimeError, match="async context manager"):
            await client.execute("{ node { arn } }")


# ---------------------------------------------------------------------------
# ResolveClient
# ---------------------------------------------------------------------------


class TestResolveClientResolve:
    """Verify ResolveClient.resolve handles found, not-found, and connection failures."""

    @pytest.mark.asyncio
    async def test_found_resource(self) -> None:
        response_body = {
            "data": {"node": {"file_path": "src/main.py", "line_number": 42}}
        }
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=response_body)
        )

        async with ResolveClient(base_url="http://graph:8080") as client:
            client._client = httpx.AsyncClient(transport=transport, base_url="http://graph:8080")
            result = await client.resolve("arn:archon:code:ws/pkg/src/main.py#func")

        assert isinstance(result, ResolveResult)
        assert result.found is True
        assert result.file_path == "src/main.py"
        assert result.line_number == 42

    @pytest.mark.asyncio
    async def test_not_found_resource(self) -> None:
        response_body = {"data": {"node": None}}
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=response_body)
        )

        async with ResolveClient(base_url="http://graph:8080") as client:
            client._client = httpx.AsyncClient(transport=transport, base_url="http://graph:8080")
            result = await client.resolve("arn:archon:code:ws/pkg/missing.py")

        assert result.found is False
        assert result.file_path is None

    @pytest.mark.asyncio
    async def test_connection_error_raises_service_unavailable(self) -> None:
        def raise_connect_error(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        transport = httpx.MockTransport(raise_connect_error)

        async with ResolveClient(base_url="http://graph:8080") as client:
            client._client = httpx.AsyncClient(transport=transport, base_url="http://graph:8080")
            with pytest.raises(ServiceUnavailableError) as exc_info:
                await client.resolve("arn:archon:code:ws/pkg/path.py")

        assert exc_info.value.service_name == "Code Graph"

    @pytest.mark.asyncio
    async def test_context_manager_required(self) -> None:
        client = ResolveClient(base_url="http://graph:8080")
        with pytest.raises(RuntimeError, match="async context manager"):
            await client.resolve("arn:archon:code:ws/pkg/path.py")
