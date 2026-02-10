"""MCP server for Archon RAG system."""

import os
from mcp.server.fastmcp import FastMCP
from aphex_clients.query import QueryClient
from archon_mcp.clients import (
    GraphClient,
    GraphQLValidationError,
    ResolveClient,
    ServiceUnavailableError,
    validate_arn,
)
from starlette.requests import Request
from starlette.responses import JSONResponse

QUERY_SERVICE_URL = os.getenv("QUERY_SERVICE_URL", "http://query.archon-knowledge-base:8080")
GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL", "http://graph.archon-knowledge-base:8080")
PORT = int(os.getenv("PORT", "3000"))

mcp = FastMCP("Archon Knowledge Base", host="0.0.0.0", port=PORT, stateless_http=True)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse({"status": "healthy"})


@mcp.tool()
async def search(query: str, top_k: int = 5, repo_filter: str = "") -> dict:
    """Search across Archon/Aphex documentation with ARN metadata.

    Returns ranked chunks with provenance and ARN metadata for graph traversal:
    - content: The chunk text
    - source: File path (e.g., "ArchonAgent/src/orchestrator/main.py")
    - score: Relevance score
    - arn: ARN of the documented symbol/file
    - related_arns: ARNs referenced in this chunk
    - symbol_name: Name of the documented symbol (if applicable)
    - symbol_kind: Kind of symbol (function, class, etc.)
    - package: Package name

    Use before answering anything that depends on internal architecture, patterns, or conventions.
    Use the ARN to navigate to the Code Graph for relationship traversal.
    """
    try:
        async with QueryClient(base_url=QUERY_SERVICE_URL) as client:
            results = await client.retrieve(query=query, k=top_k)
    except Exception as exc:
        return {
            "error": "Vector store service unavailable",
            "message": str(exc),
            "chunks": [],
        }

    chunks = [_build_enriched_chunk(chunk) for chunk in results]

    if repo_filter:
        chunks = [c for c in chunks if c["repo"] == repo_filter]

    return {"chunks": chunks, "query": query}


def _build_enriched_chunk(chunk: object) -> dict:
    """Transform a vector-store chunk into a response dict with ARN metadata."""
    source = getattr(chunk, "source", "")
    return {
        "content": getattr(chunk, "content", ""),
        "source": source,
        "score": getattr(chunk, "score", 0.0),
        "chunk_index": getattr(chunk, "chunk_index", 0),
        "repo": source.split("/")[0] if "/" in source else "unknown",
        "arn": getattr(chunk, "arn", ""),
        "related_arns": getattr(chunk, "related_arns", []),
        "symbol_name": getattr(chunk, "symbol_name", None),
        "symbol_kind": getattr(chunk, "symbol_kind", None),
        "package": getattr(chunk, "package", ""),
    }


@mcp.tool()
async def graph(query: str, variables: dict | None = None) -> dict:
    """Execute GraphQL queries against the Code Graph.

    Proxies queries to the Code Graph service for relationship traversal.
    """
    if not query or not query.strip():
        return {
            "data": None,
            "errors": [{"message": "Query string is required and cannot be empty"}],
        }

    try:
        async with GraphClient(base_url=GRAPH_SERVICE_URL) as client:
            result = await client.execute(query=query, variables=variables or {})
            return {
                "data": result.data,
                "errors": [_serialize_graphql_error(e) for e in result.errors] if result.errors else None,
            }
    except GraphQLValidationError as exc:
        return {
            "data": None,
            "errors": [{"message": f"Invalid GraphQL query: {exc.message}"}],
        }
    except ServiceUnavailableError as exc:
        return {
            "data": None,
            "errors": [{"message": "Code Graph service unavailable", "details": str(exc)}],
        }
    except Exception as exc:
        return {
            "data": None,
            "errors": [{"message": f"Unexpected error: {exc}"}],
        }


def _serialize_graphql_error(error: object) -> dict:
    """Convert a GraphQLError dataclass into a plain dict for JSON serialization."""
    result: dict = {"message": getattr(error, "message", "Unknown error")}
    for optional_field in ("locations", "path", "extensions"):
        value = getattr(error, optional_field, None)
        if value is not None:
            result[optional_field] = value
    return result


@mcp.tool()
async def resolve(arn: str) -> dict:
    """Resolve an ARN to its file location.

    Validates ARN format and queries the Code Graph for location information.
    """
    validation_result = validate_arn(arn)
    if not validation_result.valid:
        return {
            "success": False,
            "error": f"Invalid ARN format: {validation_result.error}",
        }

    try:
        async with ResolveClient(base_url=GRAPH_SERVICE_URL) as client:
            result = await client.resolve(arn=arn)

            if result.found:
                return {
                    "success": True,
                    "filePath": result.file_path,
                    "lineNumber": result.line_number,
                }
            return {
                "success": False,
                "error": f"Resource not found for ARN: {arn}",
            }
    except ServiceUnavailableError as exc:
        return {
            "success": False,
            "error": f"Code Graph service unavailable: {exc}",
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Resolution failed: {exc}",
        }


@mcp.tool()
def get_document(doc_id: str) -> dict:
    """Fetch full document text for a doc_id.
    
    Use when you need complete context for edits or detailed understanding.
    """
    return {
        "doc_id": doc_id,
        "message": "Document retrieval not yet implemented"
    }


@mcp.tool()
def list_repos() -> dict:
    """List available repositories in the Archon knowledge base."""
    repos = [
        {"name": "ArchonAgent", "description": "LLM orchestration and model serving"},
        {"name": "ArchonKnowledgeBaseInfrastructure", "description": "RAG infrastructure"},
        {"name": "AphexPlatformInfrastructure", "description": "Platform controllers"},
        {"name": "AphexServiceClients", "description": "Shared API clients"},
        {"name": "AphexPipelineResources", "description": "Tekton task catalog"},
        {"name": "AphexCLI", "description": "Command-line interface"},
    ]
    return {"repos": repos}
