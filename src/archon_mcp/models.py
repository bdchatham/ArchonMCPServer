"""MCP protocol models and schemas."""

from dataclasses import dataclass, field
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


# --- Enhanced Tool Data Models ---
# Domain models for enhanced MCP tools (graph queries, ARN-enriched search, ARN resolution).
# These use Python dataclasses per the enhanced-tools design spec.


@dataclass
class EnhancedSearchResult:
    """Search result with ARN metadata for graph traversal.

    Extends the existing search result structure with ARN metadata fields
    while maintaining backward compatibility with existing fields.
    """

    content: str
    source: str
    score: float
    chunk_index: int
    repo: str

    arn: str
    related_arns: list[str] = field(default_factory=list)
    symbol_name: str | None = None
    symbol_kind: str | None = None
    package: str = ""


@dataclass
class GraphQLError:
    """GraphQL error structure per the GraphQL specification."""

    message: str
    locations: list[dict] | None = None
    path: list[str | int] | None = None
    extensions: dict | None = None


@dataclass
class GraphQueryInput:
    """Input for the archon.graph tool."""

    query: str
    variables: dict | None = None


@dataclass
class GraphQueryOutput:
    """Output from the archon.graph tool."""

    data: dict | None
    errors: list[GraphQLError] | None = None


@dataclass
class ResolveInput:
    """Input for the archon.resolve tool."""

    arn: str


@dataclass
class ResolveOutput:
    """Output from the archon.resolve tool."""

    success: bool
    file_path: str | None = None
    line_number: int | None = None
    error: str | None = None


@dataclass
class ResolveResult:
    """Internal result from ARN resolution via the Code Graph."""

    found: bool
    file_path: str | None = None
    line_number: int | None = None


@dataclass
class ARNValidationResult:
    """Result of ARN format validation."""

    valid: bool
    error: str | None = None
