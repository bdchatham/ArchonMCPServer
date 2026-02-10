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

Search across internal documentation with ranked results, provenance, and ARN metadata for graph traversal.

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
      "content": "string",
      "source": "string",
      "score": "number",
      "chunk_index": "number",
      "repo": "string",
      "arn": "string",
      "related_arns": ["string"],
      "symbol_name": "string | null",
      "symbol_kind": "string | null",
      "package": "string"
    }
  ],
  "query": "string"
}
```

**ARN Metadata Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `arn` | string | ARN of the documented symbol/file (e.g., `arn:archon:doc:workspace/package/path`) |
| `related_arns` | string[] | ARNs referenced in this chunk for graph traversal |
| `symbol_name` | string \| null | Name of the documented symbol (if applicable) |
| `symbol_kind` | string \| null | Kind of symbol: `function`, `class`, `method`, `variable`, `type`, `module` |
| `package` | string | Package name containing the documented content |

**Example Request:**
```json
{
  "name": "archon.search",
  "arguments": {
    "query": "How do I generate SCIP indexes?",
    "top_k": 3
  }
}
```

**Example Response:**
```json
{
  "chunks": [
    {
      "content": "The generateScipIndex tool creates SCIP indexes for a package...",
      "source": "ArchonDocumentationMCPTools/src/tools/scip_indexing.archon.md",
      "score": 0.89,
      "chunk_index": 0,
      "repo": "ArchonDocumentationMCPTools",
      "arn": "arn:archon:doc:personal-work/ArchonDocumentationMCPTools/src/tools/scip_indexing.ts",
      "related_arns": [
        "arn:archon:code:personal-work/ArchonDocumentationMCPTools/src/lib/language_detector.ts#detect",
        "arn:archon:code:personal-work/ArchonDocumentationMCPTools/src/lib/scip_parser.ts#parse"
      ],
      "symbol_name": "generateScipIndex",
      "symbol_kind": "function",
      "package": "ArchonDocumentationMCPTools"
    }
  ],
  "query": "How do I generate SCIP indexes?"
}
```

**Error Response:**
```json
{
  "error": "Vector store service unavailable",
  "message": "Connection refused to query.archon-knowledge-base:8080",
  "chunks": []
}
```

## Tool: archon.graph

Execute GraphQL queries against the Code Graph for relationship traversal and code navigation.

**Arguments:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | GraphQL query string |
| `variables` | object | No | Optional query variables as JSON object |

**Supported Queries:**

| Query | Description |
|-------|-------------|
| `node(arn: ID!)` | Direct ARN lookup |
| `searchNodes(name: String!, kind: SymbolKind, package: String, limit: Int)` | Name-based search |
| `findReferences(arn: ID!)` | Find all references to a symbol |
| `symbolsInFile(path: String!, package: String!)` | List symbols in a file |
| `symbolsInPackage(package: String!, kind: SymbolKind)` | List symbols in a package |
| `traverse(startArn: ID!, edgeTypes: [EdgeType!]!, depth: Int)` | Relationship traversal |

**Enums:**

- **SymbolKind**: `FUNCTION`, `CLASS`, `METHOD`, `VARIABLE`, `TYPE`, `MODULE`, `FILE`, `PACKAGE`
- **EdgeType**: `CONTAINS`, `REFERENCES`, `IMPLEMENTS`, `EXTENDS`, `IMPORTS`, `DOCUMENTS`

**Response Schema:**
```json
{
  "data": { },
  "errors": [
    {
      "message": "string",
      "locations": [],
      "path": []
    }
  ]
}
```

**Example Request - Node Lookup:**
```json
{
  "name": "archon.graph",
  "arguments": {
    "query": "query GetNode($arn: ID!) { node(arn: $arn) { name kind signature filePath lineNumber } }",
    "variables": {
      "arn": "arn:archon:code:personal-work/ArchonMCPServer/src/archon_mcp/server.py#search"
    }
  }
}
```

**Example Response:**
```json
{
  "data": {
    "node": {
      "name": "search",
      "kind": "FUNCTION",
      "signature": "async def search(query: str, top_k: int = 5, repo_filter: str = \"\") -> dict",
      "filePath": "ArchonMCPServer/src/archon_mcp/server.py",
      "lineNumber": 45
    }
  },
  "errors": null
}
```

**Example Request - Find References:**
```json
{
  "name": "archon.graph",
  "arguments": {
    "query": "query FindRefs($arn: ID!) { findReferences(arn: $arn) { arn name kind package } }",
    "variables": {
      "arn": "arn:archon:code:personal-work/AphexServiceClients/src/query_client.py#QueryClient"
    }
  }
}
```

**Example Request - Traverse Relationships:**
```json
{
  "name": "archon.graph",
  "arguments": {
    "query": "query Traverse($start: ID!) { traverse(startArn: $start, edgeTypes: [IMPORTS, REFERENCES], depth: 2) { arn name kind } }",
    "variables": {
      "start": "arn:archon:code:personal-work/ArchonMCPServer/src/archon_mcp/server.py"
    }
  }
}
```

**Error Response - Invalid Query:**
```json
{
  "data": null,
  "errors": [{"message": "Invalid GraphQL query: Syntax error at line 1, column 5"}]
}
```

**Error Response - Service Unavailable:**
```json
{
  "data": null,
  "errors": [{"message": "Code Graph service unavailable", "details": "Connection refused"}]
}
```

## Tool: archon.resolve

Resolve an ARN to its file location for code navigation.

**Arguments:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `arn` | string | Yes | ARN string to resolve |

**ARN Format:**
```
arn:archon:<type>:<workspace>/<package>/<path>#<symbol>
```

| Component | Description | Example |
|-----------|-------------|---------|
| `type` | Resource type | `code`, `doc`, `k8s`, `infra` |
| `workspace` | Workspace identifier | `personal-work` |
| `package` | Package/repository name | `ArchonMCPServer` |
| `path` | File path relative to package | `src/archon_mcp/server.py` |
| `symbol` | Symbol name (optional) | `search` |

**Response Schema (Success):**
```json
{
  "success": true,
  "filePath": "string",
  "lineNumber": "number | null"
}
```

**Response Schema (Failure):**
```json
{
  "success": false,
  "error": "string"
}
```

**Example Request:**
```json
{
  "name": "archon.resolve",
  "arguments": {
    "arn": "arn:archon:code:personal-work/ArchonMCPServer/src/archon_mcp/server.py#search"
  }
}
```

**Example Response (Success):**
```json
{
  "success": true,
  "filePath": "ArchonMCPServer/src/archon_mcp/server.py",
  "lineNumber": 45
}
```

**Example Response - Invalid ARN Format:**
```json
{
  "success": false,
  "error": "Invalid ARN format: ARN must start with 'arn:archon:'"
}
```

**Example Response - Invalid ARN Type:**
```json
{
  "success": false,
  "error": "Invalid ARN format: Invalid ARN type 'unknown'. Must be one of: code, doc, k8s, infra"
}
```

**Example Response - Resource Not Found:**
```json
{
  "success": false,
  "error": "Resource not found for ARN: arn:archon:code:personal-work/package/nonexistent.ts#Symbol"
}
```

**Example Response - Service Unavailable:**
```json
{
  "success": false,
  "error": "Code Graph service unavailable: Connection refused"
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
- `src/archon_mcp/clients/graph_client.py` - GraphQL Code Graph client
- `src/archon_mcp/clients/resolve_client.py` - ARN resolution client
