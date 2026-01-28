"""MCP server for Archon RAG system."""

import os
from mcp.server.fastmcp import FastMCP
from aphex_clients.query import QueryClient
from starlette.requests import Request
from starlette.responses import JSONResponse

QUERY_SERVICE_URL = os.getenv("QUERY_SERVICE_URL", "http://query.archon-knowledge-base:8080")
PORT = int(os.getenv("PORT", "3000"))

mcp = FastMCP("Archon Knowledge Base", host="0.0.0.0", port=PORT)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse({"status": "healthy"})


@mcp.tool()
async def search(query: str, top_k: int = 5, repo_filter: str = "") -> dict:
    """Search across Archon/Aphex documentation.
    
    Returns ranked chunks with provenance (source, repo, content, score).
    Use before answering questions about internal architecture or conventions.
    """
    async with QueryClient(base_url=QUERY_SERVICE_URL) as client:
        results = await client.retrieve(query=query, k=top_k)
    
    chunks = [
        {
            "source": chunk.source,
            "repo": chunk.source.split("/")[0] if "/" in chunk.source else "unknown",
            "content": chunk.content,
            "score": chunk.score,
            "chunk_index": chunk.chunk_index,
        }
        for chunk in results
    ]
    
    if repo_filter:
        chunks = [c for c in chunks if c["repo"] == repo_filter]
    
    return {"chunks": chunks, "query": query}


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
