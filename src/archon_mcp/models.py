"""MCP protocol models and schemas."""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


class Tool(BaseModel):
    """MCP tool definition."""
    name: str
    description: str
    inputSchema: dict


class ToolListResponse(BaseModel):
    """Response for tools/list endpoint."""
    tools: List[Tool]


class ToolCallRequest(BaseModel):
    """Request to invoke a tool."""
    name: str
    arguments: dict


class ToolCallResponse(BaseModel):
    """Response from tool invocation."""
    content: List[dict]
    isError: bool = False


class SearchArguments(BaseModel):
    """Arguments for archon.search tool."""
    query: str = Field(..., description="Search query text")
    top_k: Optional[int] = Field(5, description="Number of results to return")
    repo_filter: Optional[str] = Field(None, description="Filter to specific repository")


class ChunkResult(BaseModel):
    """Search result chunk with provenance."""
    doc_id: str
    chunk_id: str
    source_path: str
    repo: str
    content: str
    score: float


class SearchResponse(BaseModel):
    """Response from archon.search."""
    chunks: List[ChunkResult]


class GetDocumentArguments(BaseModel):
    """Arguments for archon.get_document tool."""
    doc_id: str = Field(..., description="Document ID from search results")


class DocumentResponse(BaseModel):
    """Response from archon.get_document."""
    doc_id: str
    repo: str
    file_path: str
    full_content: str
    metadata: dict


class RepoInfo(BaseModel):
    """Repository information."""
    name: str
    description: str
    last_updated: str


class ListReposResponse(BaseModel):
    """Response from archon.list_repos."""
    repos: List[RepoInfo]
