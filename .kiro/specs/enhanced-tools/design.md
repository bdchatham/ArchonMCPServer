# Design Document: Enhanced MCP Tools for Knowledge Base

## Overview

This design document specifies the enhanced MCP tools for the ArchonMCPServer package that leverage the knowledge base infrastructure to provide graph queries and ARN-enriched searches. These tools enable Kiro agents to navigate code structure, resolve ARNs to file locations, and perform semantic searches with rich metadata.

**This is a child spec** of the root Archon Agent Pipeline specification at `.kiro/specs/archon-agent-pipeline/`. It implements Requirement 14 (Enhanced MCP Tools for Knowledge Base) from the root spec's Phase 2: Knowledge Base Integration.

### Design Principles

1. **Backward Compatibility**: Enhanced `archon.search` maintains existing response fields while adding ARN metadata
2. **Proxy Pattern**: `archon.graph` proxies GraphQL queries to the Code Graph service without exposing internal implementation
3. **Fail-Fast Validation**: `archon.resolve` validates ARN format before attempting resolution
4. **Graceful Degradation**: Tools return structured errors when backend services are unavailable

### Dependencies

This spec depends on:
- **ArchonKnowledgeBaseInfrastructure/code-graph-storage**: Provides the GraphQL Code Graph with PostgreSQL backend
- **ArchonKnowledgeBaseInfrastructure/vector-store-arn**: Provides the Vector Store with ARN metadata in chunk payloads
- **ArchonDocumentationMCPTools**: Provides the ARN library for validation and parsing

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ArchonMCPServer                                    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         MCP Tool Layer                               │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │   │
│  │  │ archon.search   │  │ archon.graph    │  │ archon.resolve  │     │   │
│  │  │ (ARN-enriched)  │  │ (GraphQL proxy) │  │ (ARN → location)│     │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │   │
│  └───────────┼────────────────────┼────────────────────┼───────────────┘   │
│              │                    │                    │                    │
│  ┌───────────┼────────────────────┼────────────────────┼───────────────┐   │
│  │           │        Service Clients                  │               │   │
│  │  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐     │   │
│  │  │ QueryClient     │  │ GraphClient     │  │ ResolveClient   │     │   │
│  │  │ (Vector Store)  │  │ (Code Graph)    │  │ (ARN Resolution)│     │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │   │
│  └───────────┼────────────────────┼────────────────────┼───────────────┘   │
└──────────────┼────────────────────┼────────────────────┼────────────────────┘
               │                    │                    │
               ▼                    ▼                    ▼
┌──────────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Qdrant Vector      │  │   PostgreSQL     │  │   Code Graph     │
│   Store              │  │   Code Graph     │  │   GraphQL API    │
│   (archon-docs)      │  │   (nodes/edges)  │  │                  │
└──────────────────────┘  └──────────────────┘  └──────────────────┘
```

### Package Structure

```
ArchonMCPServer/
├── src/
│   └── archon_mcp/
│       ├── __init__.py
│       ├── __main__.py
│       ├── server.py              # MCP server with enhanced tools
│       ├── tools.py               # Tool definitions (updated)
│       ├── models.py              # Data models (updated)
│       └── clients/               # NEW: Service clients
│           ├── __init__.py
│           ├── graph_client.py    # GraphQL Code Graph client
│           └── resolve_client.py  # ARN resolution client
├── tests/
│   ├── test_search_enhanced.py    # Enhanced search tests
│   ├── test_graph_tool.py         # Graph tool tests
│   └── test_resolve_tool.py       # Resolve tool tests
├── pyproject.toml
└── .kiro/
    └── specs/
        └── enhanced-tools/        # This spec
```

### Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Kiro      │────▶│   MCP       │────▶│   Backend   │
│   Agent     │     │   Server    │     │   Services  │
│             │◀────│             │◀────│             │
└─────────────┘     └─────────────┘     └─────────────┘

Search Flow:
  Agent → archon.search(query) → QueryClient → Qdrant → EnrichedSearchResult

Graph Flow:
  Agent → archon.graph(query) → GraphClient → PostgreSQL/GraphQL → GraphQueryOutput

Resolve Flow:
  Agent → archon.resolve(arn) → ResolveClient → Code Graph → ResolveOutput
```

## Component Interfaces

### MCP Tool: archon.search (Enhanced)

Enhances the existing search tool to return ARN metadata with each result.

**Tool Definition:**

```python
ARCHON_SEARCH_ENHANCED = Tool(
    name="archon.search",
    description="""Search across internal Archon/Aphex documentation with ARN metadata.
    
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
Use the ARN to navigate to the Code Graph for relationship traversal.""",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text"
            },
            "top_k": {
                "type": "number",
                "description": "Number of results to return (default: 5)"
            },
            "repo_filter": {
                "type": "string",
                "description": "Filter to specific repository (e.g., 'ArchonAgent')"
            }
        },
        "required": ["query"]
    }
)
```

**Implementation:**

```python
@mcp.tool()
async def search(query: str, top_k: int = 5, repo_filter: str = "") -> dict:
    """Search across Archon/Aphex documentation with ARN metadata.
    
    Returns ranked chunks with provenance and ARN metadata for graph traversal.
    """
    try:
        async with QueryClient(base_url=QUERY_SERVICE_URL) as client:
            results = await client.retrieve(query=query, k=top_k)
    except Exception as e:
        return {
            "error": "Vector store service unavailable",
            "message": str(e),
            "chunks": []
        }
    
    chunks = [
        {
            "content": chunk.content,
            "source": chunk.source,
            "score": chunk.score,
            "chunk_index": chunk.chunk_index,
            "repo": chunk.source.split("/")[0] if "/" in chunk.source else "unknown",
            # ARN metadata from enhanced vector store
            "arn": chunk.arn,
            "related_arns": chunk.related_arns,
            "symbol_name": chunk.symbol_name,
            "symbol_kind": chunk.symbol_kind,
            "package": chunk.package,
        }
        for chunk in results
    ]
    
    if repo_filter:
        chunks = [c for c in chunks if c["repo"] == repo_filter]
    
    return {"chunks": chunks, "query": query}
```

### MCP Tool: archon.graph (New)

Proxies GraphQL queries to the Code Graph for relationship traversal.

**Tool Definition:**

```python
ARCHON_GRAPH = Tool(
    name="archon.graph",
    description="""Execute GraphQL queries against the Code Graph.

The Code Graph stores code structure as a property graph with ARNs as primary identifiers.
Use this tool to traverse code relationships and find relevant symbols.

Supported queries:
- node(arn: ID!): Direct ARN lookup
- searchNodes(name: String!, kind: SymbolKind, package: String, limit: Int): Name-based search
- findReferences(arn: ID!): Find all references to a symbol
- symbolsInFile(path: String!, package: String!): List symbols in a file
- symbolsInPackage(package: String!, kind: SymbolKind): List symbols in a package
- traverse(startArn: ID!, edgeTypes: [EdgeType!]!, depth: Int): Relationship traversal

SymbolKind: FUNCTION, CLASS, METHOD, VARIABLE, TYPE, MODULE, FILE, PACKAGE
EdgeType: CONTAINS, REFERENCES, IMPLEMENTS, EXTENDS, IMPORTS, DOCUMENTS

Returns standard GraphQL response format with 'data' and optional 'errors' fields.""",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "GraphQL query string"
            },
            "variables": {
                "type": "object",
                "description": "Optional query variables as JSON object"
            }
        },
        "required": ["query"]
    }
)
```

**Implementation:**

```python
@mcp.tool()
async def graph(query: str, variables: dict | None = None) -> dict:
    """Execute GraphQL queries against the Code Graph.
    
    Proxies queries to the Code Graph service for relationship traversal.
    """
    # Validate query is not empty
    if not query or not query.strip():
        return {
            "data": None,
            "errors": [{"message": "Query string is required and cannot be empty"}]
        }
    
    try:
        async with GraphClient(base_url=GRAPH_SERVICE_URL) as client:
            result = await client.execute(query=query, variables=variables or {})
            return {
                "data": result.data,
                "errors": result.errors if result.errors else None
            }
    except GraphQLValidationError as e:
        return {
            "data": None,
            "errors": [{"message": f"Invalid GraphQL query: {e.message}"}]
        }
    except ServiceUnavailableError as e:
        return {
            "data": None,
            "errors": [{"message": "Code Graph service unavailable", "details": str(e)}]
        }
    except Exception as e:
        return {
            "data": None,
            "errors": [{"message": f"Unexpected error: {str(e)}"}]
        }
```

### MCP Tool: archon.resolve (New)

Resolves ARNs to file locations for code navigation.

**Tool Definition:**

```python
ARCHON_RESOLVE = Tool(
    name="archon.resolve",
    description="""Resolve an ARN to its file location.

ARN format: arn:archon:<type>:<workspace>/<package>/<path>#<symbol>
- type: code, doc, k8s, infra
- workspace: Workspace identifier (e.g., 'personal-work')
- package: Package/repository name
- path: File path relative to package
- symbol: Symbol name (optional)

Returns:
- success: true/false
- filePath: Absolute or workspace-relative file path (when success=true)
- lineNumber: Line number in the file (when available)
- error: Descriptive error message (when success=false)

Use this tool to navigate from search results or graph nodes to actual code locations.""",
    inputSchema={
        "type": "object",
        "properties": {
            "arn": {
                "type": "string",
                "description": "ARN string to resolve (e.g., 'arn:archon:code:workspace/package/path#symbol')"
            }
        },
        "required": ["arn"]
    }
)
```

**Implementation:**

```python
@mcp.tool()
async def resolve(arn: str) -> dict:
    """Resolve an ARN to its file location.
    
    Validates ARN format and queries the Code Graph for location information.
    """
    # Validate ARN format
    validation_result = validate_arn(arn)
    if not validation_result.valid:
        return {
            "success": False,
            "error": f"Invalid ARN format: {validation_result.error}"
        }
    
    try:
        async with ResolveClient(base_url=GRAPH_SERVICE_URL) as client:
            result = await client.resolve(arn=arn)
            
            if result.found:
                return {
                    "success": True,
                    "filePath": result.file_path,
                    "lineNumber": result.line_number
                }
            else:
                return {
                    "success": False,
                    "error": f"Resource not found for ARN: {arn}"
                }
    except ServiceUnavailableError as e:
        return {
            "success": False,
            "error": f"Code Graph service unavailable: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Resolution failed: {str(e)}"
        }
```

### Service Clients

#### GraphClient

```python
class GraphClient:
    """Client for the Code Graph GraphQL API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._session: aiohttp.ClientSession | None = None
    
    async def __aenter__(self) -> "GraphClient":
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session:
            await self._session.close()
    
    async def execute(
        self,
        query: str,
        variables: dict | None = None,
        timeout: float = 30.0
    ) -> GraphQLResponse:
        """Execute a GraphQL query against the Code Graph.
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            timeout: Request timeout in seconds
            
        Returns:
            GraphQLResponse with data and optional errors
            
        Raises:
            GraphQLValidationError: If query is invalid
            ServiceUnavailableError: If service is unreachable
        """
        pass
```

#### ResolveClient

```python
class ResolveClient:
    """Client for ARN resolution via the Code Graph."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._session: aiohttp.ClientSession | None = None
    
    async def __aenter__(self) -> "ResolveClient":
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session:
            await self._session.close()
    
    async def resolve(self, arn: str, timeout: float = 10.0) -> ResolveResult:
        """Resolve an ARN to its file location.
        
        Args:
            arn: Valid ARN string
            timeout: Request timeout in seconds
            
        Returns:
            ResolveResult with file_path and line_number
            
        Raises:
            ServiceUnavailableError: If service is unreachable
        """
        pass
```

### ARN Validation

```python
def validate_arn(arn: str) -> ARNValidationResult:
    """Validate ARN format without resolving.
    
    ARN format: arn:archon:<type>:<workspace>/<package>/<path>#<symbol>
    
    Args:
        arn: ARN string to validate
        
    Returns:
        ARNValidationResult with valid flag and optional error message
    """
    if not arn:
        return ARNValidationResult(valid=False, error="ARN cannot be empty")
    
    if not arn.startswith("arn:archon:"):
        return ARNValidationResult(valid=False, error="ARN must start with 'arn:archon:'")
    
    # Parse components
    parts = arn[11:].split(":", 1)  # Skip "arn:archon:"
    if len(parts) != 2:
        return ARNValidationResult(valid=False, error="ARN must have type and resource components")
    
    arn_type, resource = parts
    
    # Validate type
    valid_types = {"code", "doc", "k8s", "infra"}
    if arn_type not in valid_types:
        return ARNValidationResult(
            valid=False,
            error=f"Invalid ARN type '{arn_type}'. Must be one of: {', '.join(valid_types)}"
        )
    
    # Validate resource has workspace/package/path
    if "/" not in resource:
        return ARNValidationResult(
            valid=False,
            error="ARN resource must contain workspace/package/path"
        )
    
    return ARNValidationResult(valid=True)
```

## Data Models

### Input/Output Schemas

#### Enhanced Search Result

```python
@dataclass
class EnhancedSearchResult:
    """Search result with ARN metadata for graph traversal."""
    
    # Existing fields (backward compatible)
    content: str
    source: str
    score: float
    chunk_index: int
    repo: str
    
    # ARN metadata (new)
    arn: str
    related_arns: list[str]
    symbol_name: str | None
    symbol_kind: str | None
    package: str
```

**JSON Schema:**

```json
{
  "type": "object",
  "properties": {
    "content": {"type": "string"},
    "source": {"type": "string"},
    "score": {"type": "number"},
    "chunk_index": {"type": "integer"},
    "repo": {"type": "string"},
    "arn": {"type": "string"},
    "related_arns": {
      "type": "array",
      "items": {"type": "string"}
    },
    "symbol_name": {"type": ["string", "null"]},
    "symbol_kind": {"type": ["string", "null"]},
    "package": {"type": "string"}
  },
  "required": ["content", "source", "score", "chunk_index", "repo", "arn", "related_arns", "package"]
}
```

#### Graph Query Input

```python
@dataclass
class GraphQueryInput:
    """Input for archon.graph tool."""
    
    query: str              # GraphQL query string
    variables: dict | None  # Optional query variables
```

**JSON Schema:**

```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string"},
    "variables": {"type": "object"}
  },
  "required": ["query"]
}
```

#### Graph Query Output

```python
@dataclass
class GraphQueryOutput:
    """Output from archon.graph tool."""
    
    data: dict | None
    errors: list[GraphQLError] | None


@dataclass
class GraphQLError:
    """GraphQL error structure."""
    
    message: str
    locations: list[dict] | None = None
    path: list[str | int] | None = None
    extensions: dict | None = None
```

**JSON Schema:**

```json
{
  "type": "object",
  "properties": {
    "data": {"type": ["object", "null"]},
    "errors": {
      "type": ["array", "null"],
      "items": {
        "type": "object",
        "properties": {
          "message": {"type": "string"},
          "locations": {"type": "array"},
          "path": {"type": "array"},
          "extensions": {"type": "object"}
        },
        "required": ["message"]
      }
    }
  }
}
```

#### Resolve Input

```python
@dataclass
class ResolveInput:
    """Input for archon.resolve tool."""
    
    arn: str  # ARN string to resolve
```

**JSON Schema:**

```json
{
  "type": "object",
  "properties": {
    "arn": {"type": "string"}
  },
  "required": ["arn"]
}
```

#### Resolve Output

```python
@dataclass
class ResolveOutput:
    """Output from archon.resolve tool."""
    
    success: bool
    file_path: str | None = None
    line_number: int | None = None
    error: str | None = None
```

**JSON Schema (Success):**

```json
{
  "type": "object",
  "properties": {
    "success": {"type": "boolean", "const": true},
    "filePath": {"type": "string"},
    "lineNumber": {"type": ["integer", "null"]}
  },
  "required": ["success", "filePath"]
}
```

**JSON Schema (Failure):**

```json
{
  "type": "object",
  "properties": {
    "success": {"type": "boolean", "const": false},
    "error": {"type": "string"}
  },
  "required": ["success", "error"]
}
```

### Internal Models

#### ARN Validation Result

```python
@dataclass
class ARNValidationResult:
    """Result of ARN format validation."""
    
    valid: bool
    error: str | None = None
```

#### GraphQL Response

```python
@dataclass
class GraphQLResponse:
    """Response from GraphQL Code Graph API."""
    
    data: dict | None
    errors: list[GraphQLError] | None
```

#### Resolve Result

```python
@dataclass
class ResolveResult:
    """Result from ARN resolution."""
    
    found: bool
    file_path: str | None = None
    line_number: int | None = None
```

## Error Handling

### Error Categories

| Category | Tools Affected | Response Pattern |
|----------|----------------|------------------|
| Service Unavailable | All | Return structured error with service name |
| Invalid Input | archon.graph, archon.resolve | Return validation error with details |
| Resource Not Found | archon.resolve | Return success=false with descriptive error |
| Timeout | All | Return timeout error with operation context |

### Error Response Formats

#### archon.search Errors

```python
# Service unavailable
{
    "error": "Vector store service unavailable",
    "message": "Connection refused to query.archon-knowledge-base:8080",
    "chunks": []
}

# Timeout
{
    "error": "Search timeout",
    "message": "Query exceeded 30 second timeout",
    "chunks": []
}
```

#### archon.graph Errors

```python
# Invalid query
{
    "data": None,
    "errors": [{"message": "Invalid GraphQL query: Syntax error at line 1, column 5"}]
}

# Service unavailable
{
    "data": None,
    "errors": [{"message": "Code Graph service unavailable", "details": "Connection refused"}]
}

# Query execution error
{
    "data": None,
    "errors": [{"message": "Field 'unknownField' not found on type 'Node'"}]
}
```

#### archon.resolve Errors

```python
# Invalid ARN format
{
    "success": False,
    "error": "Invalid ARN format: ARN must start with 'arn:archon:'"
}

# Invalid ARN type
{
    "success": False,
    "error": "Invalid ARN format: Invalid ARN type 'unknown'. Must be one of: code, doc, k8s, infra"
}

# Resource not found
{
    "success": False,
    "error": "Resource not found for ARN: arn:archon:code:workspace/package/nonexistent.ts#Symbol"
}

# Service unavailable
{
    "success": False,
    "error": "Code Graph service unavailable: Connection refused"
}
```

### Error Handling Implementation

```python
class ServiceUnavailableError(Exception):
    """Raised when a backend service is unreachable."""
    
    def __init__(self, service_name: str, details: str):
        self.service_name = service_name
        self.details = details
        super().__init__(f"{service_name} unavailable: {details}")


class GraphQLValidationError(Exception):
    """Raised when a GraphQL query is invalid."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def with_timeout(coro, timeout: float, operation: str):
    """Execute coroutine with timeout and structured error handling."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"{operation} exceeded {timeout} second timeout")
```

## Correctness Properties

### Property 1: Enhanced Search Backward Compatibility

*For any* search query that succeeds, the response SHALL include all existing fields (`content`, `source`, `score`, `chunk_index`, `repo`) in addition to the new ARN metadata fields.

**Validates: Requirement 1.7**

### Property 2: ARN Metadata Validity

*For any* search result with a non-null `arn` field, the ARN SHALL be a valid ARN string that passes format validation.

**Validates: Requirements 1.1, 1.2**

### Property 3: GraphQL Query Passthrough

*For any* valid GraphQL query, the `archon.graph` tool SHALL return the exact response from the Code Graph service without modification to the `data` field.

**Validates: Requirements 2.1, 2.5**

### Property 4: GraphQL Error Propagation

*For any* invalid GraphQL query, the `archon.graph` tool SHALL return an error response with a descriptive message that does not expose internal implementation details.

**Validates: Requirements 2.6, 5.5**

### Property 5: ARN Validation Before Resolution

*For any* call to `archon.resolve`, the tool SHALL validate ARN format before attempting resolution, returning a format error for malformed ARNs.

**Validates: Requirements 3.4, 3.7**

### Property 6: Resolve Success Response Completeness

*For any* successful ARN resolution, the response SHALL include `success: true`, a non-null `filePath`, and optionally a `lineNumber`.

**Validates: Requirement 3.3**

### Property 7: Resolve Failure Response Completeness

*For any* failed ARN resolution (invalid format, not found, or service error), the response SHALL include `success: false` and a descriptive `error` message.

**Validates: Requirements 3.4, 3.5**

### Property 8: Service Unavailability Handling

*For any* tool call when a backend service is unavailable, the tool SHALL return a structured error indicating service unavailability without crashing or hanging.

**Validates: Requirements 5.1, 5.2, 5.4**

## Testing Strategy

### Test Categories

#### Unit Tests

1. **ARN Validation Tests**
   - Valid ARN formats for all types (code, doc, k8s, infra)
   - Invalid ARN formats (missing prefix, invalid type, malformed resource)
   - Edge cases (empty string, very long ARNs, special characters)

2. **Response Transformation Tests**
   - Enhanced search result construction from vector store response
   - GraphQL response passthrough
   - Resolve output construction

3. **Error Handling Tests**
   - Service unavailable scenarios
   - Timeout handling
   - Invalid input handling

#### Integration Tests

1. **archon.search Integration**
   - Search with ARN metadata returned
   - Repo filtering with ARN metadata
   - Empty results handling

2. **archon.graph Integration**
   - Node lookup by ARN
   - Search nodes by name
   - Relationship traversal
   - Invalid query handling

3. **archon.resolve Integration**
   - Resolve code ARN to file location
   - Resolve doc ARN to file location
   - Not found handling

#### Property-Based Tests

1. **Property 1: Backward Compatibility**
   - Generate random search queries
   - Verify all existing fields present in response

2. **Property 2: ARN Metadata Validity**
   - Generate search results with ARN metadata
   - Verify all ARNs pass validation

3. **Property 5: ARN Validation Before Resolution**
   - Generate random ARN strings (valid and invalid)
   - Verify validation occurs before resolution attempt

### Test Configuration

- **Framework**: pytest with pytest-asyncio
- **Property Testing**: hypothesis
- **Mocking**: pytest-mock for service client mocking
- **Minimum Property Test Iterations**: 100

### Test File Structure

```
tests/
├── unit/
│   ├── test_arn_validation.py
│   ├── test_response_models.py
│   └── test_error_handling.py
├── integration/
│   ├── test_search_enhanced.py
│   ├── test_graph_tool.py
│   └── test_resolve_tool.py
└── property/
    ├── test_backward_compatibility.py
    ├── test_arn_validity.py
    └── test_validation_ordering.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `QUERY_SERVICE_URL` | Vector store query service URL | `http://query.archon-knowledge-base:8080` |
| `GRAPH_SERVICE_URL` | Code Graph GraphQL service URL | `http://graph.archon-knowledge-base:8080` |
| `REQUEST_TIMEOUT` | Default request timeout (seconds) | `30` |
| `PORT` | MCP server port | `3000` |

### Service Discovery

The enhanced tools rely on Kubernetes service discovery:

```yaml
# Query Service (Vector Store)
query.archon-knowledge-base.svc.cluster.local:8080

# Graph Service (Code Graph)
graph.archon-knowledge-base.svc.cluster.local:8080
```

## Source

- `ArchonMCPServer/src/archon_mcp/server.py` - MCP server implementation
- `ArchonMCPServer/src/archon_mcp/tools.py` - Tool definitions
- `ArchonMCPServer/src/archon_mcp/models.py` - Data models
- `.kiro/specs/archon-agent-pipeline/design.md` - Root spec Phase 2 design
