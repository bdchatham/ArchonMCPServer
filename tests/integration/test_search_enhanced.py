"""Integration tests for the enhanced archon.search tool handler.

Tests exercise the search() function end-to-end with mocked QueryClient
to verify ARN metadata enrichment, repo filtering, empty results, and
backward compatibility with existing response fields.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class MockChunk:
    """Lightweight stand-in for vector-store chunk objects.

    The search handler uses ``getattr(chunk, field, default)`` to extract
    fields, so we simply set attributes from keyword arguments.
    """

    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


def _make_chunk(**overrides: object) -> MockChunk:
    """Build a MockChunk with sensible defaults, overridden by *overrides*."""
    defaults = {
        "content": "def hello(): ...",
        "source": "ArchonAgent/src/main.py",
        "score": 0.95,
        "chunk_index": 0,
        "arn": "arn:archon:code:personal-work/ArchonAgent/src/main.py#hello",
        "related_arns": ["arn:archon:code:personal-work/ArchonAgent/src/utils.py#greet"],
        "symbol_name": "hello",
        "symbol_kind": "function",
        "package": "ArchonAgent",
    }
    defaults.update(overrides)
    return MockChunk(**defaults)


def _mock_query_client(chunks: list[MockChunk]) -> MagicMock:
    """Return a mock that replaces ``QueryClient`` as an async context manager."""
    client_instance = AsyncMock()
    client_instance.retrieve = AsyncMock(return_value=chunks)

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=client_instance)
    context_manager.__aexit__ = AsyncMock(return_value=False)

    constructor = MagicMock(return_value=context_manager)
    return constructor


class TestSearchWithARNMetadata:
    """Verify that search results include ARN metadata fields."""

    @pytest.mark.asyncio
    async def test_arn_metadata_present_in_results(self) -> None:
        chunks = [_make_chunk()]
        mock_constructor = _mock_query_client(chunks)

        with patch("archon_mcp.server.QueryClient", mock_constructor):
            from archon_mcp.server import search

            result = await search(query="hello function")

        assert "chunks" in result
        assert len(result["chunks"]) == 1

        chunk = result["chunks"][0]
        assert chunk["arn"] == "arn:archon:code:personal-work/ArchonAgent/src/main.py#hello"
        assert chunk["related_arns"] == ["arn:archon:code:personal-work/ArchonAgent/src/utils.py#greet"]
        assert chunk["symbol_name"] == "hello"
        assert chunk["symbol_kind"] == "function"
        assert chunk["package"] == "ArchonAgent"

    @pytest.mark.asyncio
    async def test_multiple_results_all_enriched(self) -> None:
        chunks = [
            _make_chunk(
                content="class Foo: ...",
                source="ArchonAgent/src/foo.py",
                arn="arn:archon:code:personal-work/ArchonAgent/src/foo.py#Foo",
                symbol_name="Foo",
                symbol_kind="class",
            ),
            _make_chunk(
                content="class Bar: ...",
                source="ArchonAgent/src/bar.py",
                arn="arn:archon:code:personal-work/ArchonAgent/src/bar.py#Bar",
                symbol_name="Bar",
                symbol_kind="class",
            ),
        ]
        mock_constructor = _mock_query_client(chunks)

        with patch("archon_mcp.server.QueryClient", mock_constructor):
            from archon_mcp.server import search

            result = await search(query="class definitions")

        assert len(result["chunks"]) == 2
        for chunk in result["chunks"]:
            assert "arn" in chunk
            assert "related_arns" in chunk
            assert "symbol_name" in chunk
            assert "symbol_kind" in chunk
            assert "package" in chunk


class TestSearchRepoFiltering:
    """Verify repo filtering works correctly with ARN-enriched results."""

    @pytest.mark.asyncio
    async def test_repo_filter_includes_matching(self) -> None:
        chunks = [
            _make_chunk(source="ArchonAgent/src/a.py", package="ArchonAgent"),
            _make_chunk(source="AphexCLI/src/b.py", package="AphexCLI"),
        ]
        mock_constructor = _mock_query_client(chunks)

        with patch("archon_mcp.server.QueryClient", mock_constructor):
            from archon_mcp.server import search

            result = await search(query="test", repo_filter="ArchonAgent")

        assert len(result["chunks"]) == 1
        assert result["chunks"][0]["repo"] == "ArchonAgent"

    @pytest.mark.asyncio
    async def test_repo_filter_excludes_non_matching(self) -> None:
        chunks = [_make_chunk(source="AphexCLI/src/b.py")]
        mock_constructor = _mock_query_client(chunks)

        with patch("archon_mcp.server.QueryClient", mock_constructor):
            from archon_mcp.server import search

            result = await search(query="test", repo_filter="ArchonAgent")

        assert len(result["chunks"]) == 0


class TestSearchEmptyResults:
    """Verify empty result handling."""

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_chunks(self) -> None:
        mock_constructor = _mock_query_client([])

        with patch("archon_mcp.server.QueryClient", mock_constructor):
            from archon_mcp.server import search

            result = await search(query="nonexistent topic")

        assert result["chunks"] == []
        assert result["query"] == "nonexistent topic"


class TestSearchBackwardCompatibility:
    """Verify existing response fields remain present and correct."""

    @pytest.mark.asyncio
    async def test_existing_fields_preserved(self) -> None:
        chunks = [
            _make_chunk(
                content="original content",
                source="ArchonAgent/src/handler.py",
                score=0.88,
                chunk_index=3,
            )
        ]
        mock_constructor = _mock_query_client(chunks)

        with patch("archon_mcp.server.QueryClient", mock_constructor):
            from archon_mcp.server import search

            result = await search(query="handler")

        chunk = result["chunks"][0]
        assert chunk["content"] == "original content"
        assert chunk["source"] == "ArchonAgent/src/handler.py"
        assert chunk["score"] == 0.88
        assert chunk["chunk_index"] == 3
        assert chunk["repo"] == "ArchonAgent"

    @pytest.mark.asyncio
    async def test_query_echoed_in_response(self) -> None:
        mock_constructor = _mock_query_client([_make_chunk()])

        with patch("archon_mcp.server.QueryClient", mock_constructor):
            from archon_mcp.server import search

            result = await search(query="my search query")

        assert result["query"] == "my search query"

    @pytest.mark.asyncio
    async def test_missing_arn_metadata_defaults_gracefully(self) -> None:
        bare_chunk = MockChunk(
            content="bare content",
            source="Repo/file.py",
            score=0.5,
            chunk_index=0,
        )
        mock_constructor = _mock_query_client([bare_chunk])

        with patch("archon_mcp.server.QueryClient", mock_constructor):
            from archon_mcp.server import search

            result = await search(query="bare")

        chunk = result["chunks"][0]
        assert chunk["arn"] == ""
        assert chunk["related_arns"] == []
        assert chunk["symbol_name"] is None
        assert chunk["symbol_kind"] is None
        assert chunk["package"] == ""

    @pytest.mark.asyncio
    async def test_service_unavailable_returns_error_with_empty_chunks(self) -> None:
        mock_constructor = MagicMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(side_effect=ConnectionError("refused"))
        mock_constructor.return_value = ctx

        with patch("archon_mcp.server.QueryClient", mock_constructor):
            from archon_mcp.server import search

            result = await search(query="anything")

        assert "error" in result
        assert result["chunks"] == []
