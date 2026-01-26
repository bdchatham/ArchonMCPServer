# API

## MCP Protocol Endpoints

ArchonMCPServer implements the Model Context Protocol (MCP) over HTTP.

### Base URL

**Local:** `http://localhost:8090`

**Kubernetes:** `http://mcp-server.archon-knowledge-base:8090`

## Health Check

### GET /health

Health check endpoint for liveness and readiness probes.

**Response:**
```json
{
  "status": "healthy"
}
```

**Status Codes:**
- `200 OK` - Server is healthy

## MCP Tool Discovery

### POST /mcp/tools/list

List all available MCP tools with their schemas.

**Request Body:** None

**Response:**
```json
{
  "tools": [
    {
      "name": "archon.search",
      "description": "Search across internal Archon/Aphex documentation...",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "top_k": {"type": "number"},
          "repo_filter": {"type": "string"}
        },
        "required": ["query"]
      }
    }
  ]
}
```

## MCP Tool Invocation

### POST /mcp/tools/call

Invoke an MCP tool with arguments.

**Request Body:**
```json
{
  "name": "archon.search",
  "arguments": {
    "query": "How do I deploy a service?",
    "top_k": 5
  }
}
```

**Response:**
```json
{
  "content": [{"type": "text", "text": "{...}"}],
  "isError": false
}
```

## Tool: archon.search

Search across internal documentation with ranked results and provenance.

**Arguments:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query text |
| `top_k` | number | No | 5 | Number of results to return |
| `repo_filter` | string | No | - | Filter to specific repository |

**Response Schema:**
```json
{
  "chunks": [
    {
      "doc_id": "string",
      "chunk_id": "string",
      "source_path": "string",
      "repo": "string",
      "content": "string",
      "score": "number"
    }
  ]
}
```

## Tool: archon.get_document

Fetch full document text for a doc_id.

**Arguments:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_id` | string | Yes | Document ID from search results |

**Response Schema:**
```json
{
  "doc_id": "string",
  "repo": "string",
  "file_path": "string",
  "full_content": "string",
  "metadata": {}
}
```

**Status:** TODO - Currently returns placeholder

## Tool: archon.list_repos

List available repositories in the knowledge base.

**Arguments:** None

**Response Schema:**
```json
{
  "repos": [
    {
      "name": "string",
      "description": "string",
      "last_updated": "string"
    }
  ]
}
```

## Authentication

**Current:** No authentication required

**TODO:** Add API key or OAuth for production

## Error Handling

**Tool Not Found:**
```json
{
  "content": [{"type": "text", "text": "Error: Tool not found: ..."}],
  "isError": true
}
```

**Invalid Arguments:**
```json
{
  "content": [{"type": "text", "text": "Error: validation error..."}],
  "isError": true
}
```

**Source**
- `src/archon_mcp/server.py` - Endpoint implementations
- `src/archon_mcp/models.py` - Request/response schemas
- `src/archon_mcp/tools.py` - Tool definitions
