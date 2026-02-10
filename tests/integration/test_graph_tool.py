"""Integration tests for the archon.graph tool handler.

Tests exercise the graph() function end-to-end with mocked GraphClient
to verify node lookup, name search, relationship traversal, invalid
query handling, and service unavailability.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from archon_mcp.clients.exceptions import (
    GraphQLValidationError,
    ServiceUnavailableError,
)
from archon_mcp.models import GraphQLError, GraphQueryOutput


def _mock_graph_client(execute_side_effect: object) -> MagicMock:
    """Return a mock that replaces ``GraphClient`` as an async context manager.

    *execute_side_effect* is either a return value or an exception class/instance
    to be used as the ``side_effect`` of the ``execute`` coroutine.
    """
    client_instance = AsyncMock()

    if isinstance(execute_side_effect, BaseException) or (
        isinstance(execute_side_effect, type) and issubclass(execute_side_effect, BaseException)
    ):
        client_instance.execute = AsyncMock(side_effect=execute_side_effect)
    else:
        client_instance.execute = AsyncMock(return_value=execute_side_effect)

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=client_instance)
    context_manager.__aexit__ = AsyncMock(return_value=False)

    return MagicMock(return_value=context_manager)


class TestGraphNodeLookup:
    """Verify direct ARN lookup via the graph tool."""

    @pytest.mark.asyncio
    async def test_node_lookup_returns_data(self) -> None:
        expected_data = {
            "node": {
                "arn": "arn:archon:code:ws/pkg/src/main.py#hello",
                "kind": "FUNCTION",
                "name": "hello",
            }
        }
        output = GraphQueryOutput(data=expected_data)
        mock_constructor = _mock_graph_client(output)

        with patch("archon_mcp.server.GraphClient", mock_constructor):
            from archon_mcp.server import graph

            result = await graph(
                query='{ node(arn: "arn:archon:code:ws/pkg/src/main.py#hello") { arn kind name } }'
            )

        assert result["data"] == expected_data
        assert result["errors"] is None

    @pytest.mark.asyncio
    async def test_node_lookup_not_found_returns_null_data(self) -> None:
        output = GraphQueryOutput(data={"node": None})
        mock_constructor = _mock_graph_client(output)

        with patch("archon_mcp.server.GraphClient", mock_constructor):
            from archon_mcp.server import graph

            result = await graph(
                query='{ node(arn: "arn:archon:code:ws/pkg/missing.py") { arn } }'
            )

        assert result["data"] == {"node": None}
        assert result["errors"] is None


class TestGraphSearchNodes:
    """Verify name-based node search via the graph tool."""

    @pytest.mark.asyncio
    async def test_search_nodes_returns_matches(self) -> None:
        expected_data = {
            "searchNodes": [
                {"arn": "arn:archon:code:ws/pkg/a.py#Foo", "name": "Foo", "kind": "CLASS"},
                {"arn": "arn:archon:code:ws/pkg/b.py#FooBar", "name": "FooBar", "kind": "CLASS"},
            ]
        }
        output = GraphQueryOutput(data=expected_data)
        mock_constructor = _mock_graph_client(output)

        with patch("archon_mcp.server.GraphClient", mock_constructor):
            from archon_mcp.server import graph

            result = await graph(
                query="query($name: String!) { searchNodes(name: $name) { arn name kind } }",
                variables={"name": "Foo"},
            )

        assert result["data"] == expected_data
        assert len(result["data"]["searchNodes"]) == 2


class TestGraphRelationshipTraversal:
    """Verify relationship traversal via the graph tool."""

    @pytest.mark.asyncio
    async def test_traverse_returns_connected_nodes(self) -> None:
        expected_data = {
            "traverse": {
                "nodes": [
                    {"arn": "arn:archon:code:ws/pkg/a.py#Foo", "name": "Foo"},
                    {"arn": "arn:archon:code:ws/pkg/b.py#Bar", "name": "Bar"},
                ],
                "edges": [
                    {"source": "arn:archon:code:ws/pkg/a.py#Foo", "target": "arn:archon:code:ws/pkg/b.py#Bar", "type": "IMPORTS"},
                ],
            }
        }
        output = GraphQueryOutput(data=expected_data)
        mock_constructor = _mock_graph_client(output)

        with patch("archon_mcp.server.GraphClient", mock_constructor):
            from archon_mcp.server import graph

            result = await graph(
                query='{ traverse(startArn: "arn:archon:code:ws/pkg/a.py#Foo", edgeTypes: [IMPORTS], depth: 1) { nodes { arn name } edges { source target type } } }'
            )

        assert result["data"]["traverse"]["nodes"] is not None
        assert len(result["data"]["traverse"]["edges"]) == 1


class TestGraphInvalidQuery:
    """Verify error handling for invalid GraphQL queries."""

    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self) -> None:
        from archon_mcp.server import graph

        result = await graph(query="")

        assert result["data"] is None
        assert result["errors"] is not None
        assert "required" in result["errors"][0]["message"].lower()

    @pytest.mark.asyncio
    async def test_whitespace_only_query_returns_error(self) -> None:
        from archon_mcp.server import graph

        result = await graph(query="   ")

        assert result["data"] is None
        assert result["errors"] is not None

    @pytest.mark.asyncio
    async def test_validation_error_returns_descriptive_message(self) -> None:
        error = GraphQLValidationError(message="Cannot query field 'bad' on type 'Query'")
        mock_constructor = _mock_graph_client(error)

        with patch("archon_mcp.server.GraphClient", mock_constructor):
            from archon_mcp.server import graph

            result = await graph(query="{ bad }")

        assert result["data"] is None
        assert result["errors"] is not None
        assert "Invalid GraphQL query" in result["errors"][0]["message"]
        assert "Cannot query field" in result["errors"][0]["message"]

    @pytest.mark.asyncio
    async def test_graphql_errors_serialized_in_response(self) -> None:
        output = GraphQueryOutput(
            data=None,
            errors=[
                GraphQLError(
                    message="Field 'unknown' not found",
                    locations=[{"line": 1, "column": 3}],
                    path=["node"],
                )
            ],
        )
        mock_constructor = _mock_graph_client(output)

        with patch("archon_mcp.server.GraphClient", mock_constructor):
            from archon_mcp.server import graph

            result = await graph(query="{ node { unknown } }")

        assert result["data"] is None
        assert result["errors"] is not None
        assert result["errors"][0]["message"] == "Field 'unknown' not found"
        assert result["errors"][0]["locations"] == [{"line": 1, "column": 3}]
        assert result["errors"][0]["path"] == ["node"]


class TestGraphServiceUnavailability:
    """Verify graceful handling when the Code Graph service is down."""

    @pytest.mark.asyncio
    async def test_service_unavailable_returns_error(self) -> None:
        error = ServiceUnavailableError(service_name="Code Graph", details="Connection refused")
        mock_constructor = _mock_graph_client(error)

        with patch("archon_mcp.server.GraphClient", mock_constructor):
            from archon_mcp.server import graph

            result = await graph(query="{ node(arn: \"...\") { arn } }")

        assert result["data"] is None
        assert result["errors"] is not None
        assert "unavailable" in result["errors"][0]["message"].lower()

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_error(self) -> None:
        error = RuntimeError("unexpected internal failure")
        mock_constructor = _mock_graph_client(error)

        with patch("archon_mcp.server.GraphClient", mock_constructor):
            from archon_mcp.server import graph

            result = await graph(query="{ node(arn: \"...\") { arn } }")

        assert result["data"] is None
        assert result["errors"] is not None
        assert "Unexpected error" in result["errors"][0]["message"]
