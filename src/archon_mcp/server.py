"""FastAPI MCP server for Archon RAG system."""

import os
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from aphex_clients.query import QueryClient

from .models import (
    ToolListResponse,
    ToolCallRequest,
    ToolCallResponse,
    SearchArguments,
    SearchResponse,
    ChunkResult,
    GetDocumentArguments,
    DocumentResponse,
    ListReposResponse,
    RepoInfo,
)
from .tools import ALL_TOOLS

app = FastAPI(title="Archon MCP Server", version="0.1.0")

QUERY_SERVICE_URL = os.getenv("QUERY_SERVICE_URL", "http://query.archon-knowledge-base:8080")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/mcp/tools/list", response_model=ToolListResponse)
async def list_tools():
    """List available MCP tools."""
    return ToolListResponse(tools=ALL_TOOLS)


@app.post("/mcp/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    """Invoke an MCP tool."""
    try:
        if request.name == "archon.search":
            return await handle_search(request.arguments)
        elif request.name == "archon.get_document":
            return await handle_get_document(request.arguments)
        elif request.name == "archon.list_repos":
            return await handle_list_repos(request.arguments)
        else:
            raise HTTPException(status_code=404, detail=f"Tool not found: {request.name}")
    except Exception as e:
        return ToolCallResponse(
            content=[{"type": "text", "text": f"Error: {str(e)}"}],
            isError=True
        )


async def handle_search(arguments: dict) -> ToolCallResponse:
    """Handle archon.search tool invocation."""
    args = SearchArguments(**arguments)
    
    async with QueryClient(base_url=QUERY_SERVICE_URL) as client:
        results = await client.retrieve(query=args.query, k=args.top_k)
    
    chunks = [
        ChunkResult(
            doc_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            source_path=chunk.source,
            repo=chunk.metadata.get("repo", "unknown"),
            content=chunk.content,
            score=chunk.score
        )
        for chunk in results
    ]
    
    if args.repo_filter:
        chunks = [c for c in chunks if c.repo == args.repo_filter]
    
    response = SearchResponse(chunks=chunks)
    
    return ToolCallResponse(
        content=[{"type": "text", "text": response.model_dump_json(indent=2)}]
    )


async def handle_get_document(arguments: dict) -> ToolCallResponse:
    """Handle archon.get_document tool invocation."""
    args = GetDocumentArguments(**arguments)
    
    # TODO: Implement document retrieval from Qdrant or document store
    # For now, return placeholder
    response = DocumentResponse(
        doc_id=args.doc_id,
        repo="unknown",
        file_path="unknown",
        full_content="Document retrieval not yet implemented",
        metadata={}
    )
    
    return ToolCallResponse(
        content=[{"type": "text", "text": response.model_dump_json(indent=2)}]
    )


async def handle_list_repos(arguments: dict) -> ToolCallResponse:
    """Handle archon.list_repos tool invocation."""
    # TODO: Implement repository listing from metadata store
    # For now, return known Archon repos
    repos = [
        RepoInfo(name="ArchonAgent", description="LLM orchestration and model serving", last_updated="2026-01-26T00:00:00Z"),
        RepoInfo(name="ArchonKnowledgeBaseInfrastructure", description="RAG infrastructure and document ingestion", last_updated="2026-01-26T00:00:00Z"),
        RepoInfo(name="AphexPlatformInfrastructure", description="Platform controllers and GitOps automation", last_updated="2026-01-26T00:00:00Z"),
        RepoInfo(name="AphexServiceClients", description="Shared API clients for platform services", last_updated="2026-01-26T00:00:00Z"),
        RepoInfo(name="AphexPipelineResources", description="Tekton task catalog for CI/CD", last_updated="2026-01-26T00:00:00Z"),
        RepoInfo(name="AphexCLI", description="Command-line interface for platform operations", last_updated="2026-01-26T00:00:00Z"),
    ]
    
    response = ListReposResponse(repos=repos)
    
    return ToolCallResponse(
        content=[{"type": "text", "text": response.model_dump_json(indent=2)}]
    )
