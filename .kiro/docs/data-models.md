# Data Models

## MCP Protocol Models

### Tool

Tool definition advertised to MCP clients.

```python
class Tool(BaseModel):
    name: str
    description: str
    inputSchema: dict
```

**Example:**
```json
{
  "name": "archon.search",
  "description": "Search across internal Archon/Aphex documentation...",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "top_k": {"type": "number"}
    },
    "required": ["query"]
  }
}
```

### ToolListResponse

Response from `/mcp/tools/list` endpoint.

```python
class ToolListResponse(BaseModel):
    tools: List[Tool]
```

### ToolCallRequest

Request to invoke a tool via `/mcp/tools/call`.

```python
class ToolCallRequest(BaseModel):
    name: str
    arguments: dict
```

**Example:**
```json
{
  "name": "archon.search",
  "arguments": {
    "query": "deployment process",
    "top_k": 5
  }
}
```

### ToolCallResponse

Response from tool invocation.

```python
class ToolCallResponse(BaseModel):
    content: List[dict]
    isError: bool = False
```

**Example (Success):**
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"chunks\": [...]}"
    }
  ],
  "isError": false
}
```

**Example (Error):**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Error: Tool not found"
    }
  ],
  "isError": true
}
```

## Tool-Specific Models

### SearchArguments

Arguments for `archon.search` tool.

```python
class SearchArguments(BaseModel):
    query: str
    top_k: Optional[int] = 5
    repo_filter: Optional[str] = None
```

**Validation:**
- `query`: Non-empty string
- `top_k`: Positive integer, default 5
- `repo_filter`: Optional repository name (e.g., "ArchonAgent")

### ChunkResult

Single search result with provenance.

```python
class ChunkResult(BaseModel):
    doc_id: str
    chunk_id: str
    source_path: str
    repo: str
    content: str
    score: float
```

**Example:**
```json
{
  "doc_id": "abc123",
  "chunk_id": "chunk456",
  "source_path": "ArchonAgent/.kiro/docs/architecture.md",
  "repo": "ArchonAgent",
  "content": "vLLM v0.14.1-cu130 is used for model serving...",
  "score": 0.92
}
```

**Fields:**
- `doc_id`: Unique document identifier in Qdrant
- `chunk_id`: Unique chunk identifier within document
- `source_path`: Relative path from repository root
- `repo`: Repository name
- `content`: Text content of chunk
- `score`: Relevance score (0.0-1.0, higher is better)

### SearchResponse

Response from `archon.search` tool.

```python
class SearchResponse(BaseModel):
    chunks: List[ChunkResult]
```

**Example:**
```json
{
  "chunks": [
    {
      "doc_id": "abc123",
      "chunk_id": "chunk456",
      "source_path": "ArchonAgent/.kiro/docs/architecture.md",
      "repo": "ArchonAgent",
      "content": "...",
      "score": 0.92
    }
  ]
}
```

### GetDocumentArguments

Arguments for `archon.get_document` tool.

```python
class GetDocumentArguments(BaseModel):
    doc_id: str
```

### DocumentResponse

Response from `archon.get_document` tool.

```python
class DocumentResponse(BaseModel):
    doc_id: str
    repo: str
    file_path: str
    full_content: str
    metadata: dict
```

**Example:**
```json
{
  "doc_id": "abc123",
  "repo": "ArchonAgent",
  "file_path": ".kiro/docs/architecture.md",
  "full_content": "# Architecture\n\n...",
  "metadata": {}
}
```

### RepoInfo

Repository information.

```python
class RepoInfo(BaseModel):
    name: str
    description: str
    last_updated: str
```

**Example:**
```json
{
  "name": "ArchonAgent",
  "description": "LLM orchestration and model serving",
  "last_updated": "2026-01-26T00:00:00Z"
}
```

### ListReposResponse

Response from `archon.list_repos` tool.

```python
class ListReposResponse(BaseModel):
    repos: List[RepoInfo]
```

## Data Flow

### Search Flow

```
SearchArguments → QueryClient.retrieve() → ChunkResult[] → SearchResponse → ToolCallResponse
```

1. Client sends `ToolCallRequest` with `SearchArguments`
2. Server parses arguments and validates
3. Server calls `QueryClient.retrieve(query, k)`
4. Query Service returns chunks from Qdrant
5. Server transforms to `ChunkResult` format
6. Server applies `repo_filter` if specified
7. Server wraps in `SearchResponse` and `ToolCallResponse`

### Document Retrieval Flow (TODO)

```
GetDocumentArguments → Qdrant query → DocumentResponse → ToolCallResponse
```

Currently returns placeholder response.

## Validation Rules

**SearchArguments:**
- `query` must be non-empty string
- `top_k` must be positive integer (1-100 recommended)
- `repo_filter` must match existing repository name (not enforced)

**GetDocumentArguments:**
- `doc_id` must be valid UUID or document identifier

**ToolCallRequest:**
- `name` must match one of: `archon.search`, `archon.get_document`, `archon.list_repos`
- `arguments` must match tool's inputSchema

**Source**
- `src/archon_mcp/models.py` - Pydantic model definitions
- `src/archon_mcp/tools.py` - Tool schemas
- `src/archon_mcp/server.py` - Data transformations
