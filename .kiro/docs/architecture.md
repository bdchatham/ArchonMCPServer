# Architecture

## System Design

ArchonMCPServer is a stateless HTTP server that translates MCP protocol requests into backend service calls. It acts as an adapter between MCP clients (Kiro, Claude Desktop) and the knowledge base infrastructure, providing semantic search, code graph queries, and ARN resolution.

```mermaid
graph TD
    subgraph "MCP Client"
        A[Kiro CLI]
    end
    
    subgraph "ArchonMCPServer"
        B[FastAPI App]
        C[Tool Handlers]
        D[QueryClient]
        E[GraphClient]
        F[ResolveClient]
    end
    
    subgraph "Knowledge Base"
        G[Query Service]
        H[Qdrant Vector Store]
        I[Code Graph GraphQL]
        J[PostgreSQL]
    end
    
    A -->|POST /mcp/tools/call| B
    B --> C
    C --> D
    C --> E
    C --> F
    D -->|HTTP + Retry| G
    G --> H
    E -->|GraphQL| I
    I --> J
    F -->|GraphQL| I
    
    style B fill:#e1f5ff
    style C fill:#e1f5ff
    style D fill:#fff4e1
    style E fill:#fff4e1
    style F fill:#fff4e1
```

## Knowledge Base Integration

ArchonMCPServer connects to the knowledge base infrastructure to provide three key capabilities:

### Semantic Search with ARN Metadata

The `archon.search` tool queries the Qdrant vector store via the Query Service. Search results include ARN metadata that enables navigation to the Code Graph for relationship traversal.

```
Search Query → QueryClient → Query Service → Qdrant → EnrichedSearchResult
                                                        ├── content
                                                        ├── source
                                                        ├── score
                                                        ├── arn
                                                        ├── related_arns
                                                        └── symbol_name/kind
```

### Code Graph Queries

The `archon.graph` tool proxies GraphQL queries to the Code Graph service, enabling relationship traversal and code navigation.

```
GraphQL Query → GraphClient → Code Graph Service → PostgreSQL → GraphQL Response
                                                                  ├── data
                                                                  └── errors
```

### ARN Resolution

The `archon.resolve` tool resolves ARNs to file locations by querying the Code Graph.

```
ARN → ResolveClient → Code Graph Service → PostgreSQL → ResolveResult
                                                          ├── filePath
                                                          └── lineNumber
```

## Components

### 1. FastAPI Application

HTTP server exposing MCP endpoints.

**Responsibilities:**
- Serve `/health` for health checks
- Serve `/mcp/tools/list` to advertise available tools
- Serve `/mcp/tools/call` to invoke tools
- Handle errors and return MCP-compliant responses

**Configuration:**
- `QUERY_SERVICE_URL`: URL of Query Service (default: `http://query.archon-knowledge-base:8080`)
- Port: 8090

### 2. Tool Handlers

Functions that implement each MCP tool.

**archon.search Handler (Enhanced):**
- Parses `SearchArguments` from request
- Calls `QueryClient.retrieve(query, k)`
- Transforms results to `EnhancedSearchResult` format with ARN metadata
- Applies `repo_filter` if specified
- Returns JSON response with chunks containing ARN, related_arns, symbol_name, symbol_kind, package

**archon.graph Handler:**
- Parses `GraphQueryInput` from request
- Validates GraphQL query is not empty
- Calls `GraphClient.execute(query, variables)`
- Returns GraphQL response with data and errors

**archon.resolve Handler:**
- Parses `ResolveInput` from request
- Validates ARN format before resolution
- Calls `ResolveClient.resolve(arn)`
- Returns success with filePath/lineNumber or error message

**archon.get_document Handler:**
- Parses `GetDocumentArguments` from request
- TODO: Retrieves full document from Qdrant or document store
- Returns `DocumentResponse` with full content

**archon.list_repos Handler:**
- TODO: Queries metadata store for repository list
- Currently returns hardcoded list of 6 Archon repos
- Returns `ListReposResponse` with repo info

### 3. QueryClient Wrapper

Uses `AphexServiceClients.QueryClient` to communicate with Query Service.

**Features:**
- Automatic retry with exponential backoff (5 attempts, 1-60s wait, 0-5s jitter)
- Async context manager for connection lifecycle
- Timeout: 30 seconds per request

### 4. GraphClient (Code Graph)

Client for the Code Graph GraphQL API, enabling relationship traversal and code navigation.

**Features:**
- Async context manager for connection lifecycle
- GraphQL query execution with variables support
- Structured error handling for validation and service errors
- Timeout: 30 seconds per request

**Configuration:**
- `GRAPH_SERVICE_URL`: URL of Code Graph service (default: `http://graph.archon-knowledge-base:8080`)

### 5. ResolveClient (ARN Resolution)

Client for resolving ARNs to file locations via the Code Graph.

**Features:**
- ARN format validation before resolution
- Async context manager for connection lifecycle
- Structured error responses for not found and service errors
- Timeout: 10 seconds per request

### 6. MCP Protocol Models

Pydantic models for MCP request/response validation.

**Core Models:**
- `Tool`: Tool definition with name, description, inputSchema
- `ToolListResponse`: List of available tools
- `ToolCallRequest`: Tool invocation request
- `ToolCallResponse`: Tool invocation response

**Tool-Specific Models:**
- `SearchArguments`, `SearchResponse`, `ChunkResult`, `EnhancedSearchResult`
- `GetDocumentArguments`, `DocumentResponse`
- `ListReposResponse`, `RepoInfo`
- `GraphQueryInput`, `GraphQueryOutput`, `GraphQLError`
- `ResolveInput`, `ResolveOutput`
- `ARNValidationResult`

### 7. Tool Definitions

Static tool metadata advertised to MCP clients.

**ARCHON_SEARCH (Enhanced):**
- Name: `archon.search`
- Description: Search across internal Archon/Aphex documentation with ARN metadata
- Parameters: query (required), top_k (optional), repo_filter (optional)
- Returns: Chunks with ARN metadata for graph traversal

**ARCHON_GRAPH:**
- Name: `archon.graph`
- Description: Execute GraphQL queries against the Code Graph
- Parameters: query (required), variables (optional)
- Returns: GraphQL response with data and errors

**ARCHON_RESOLVE:**
- Name: `archon.resolve`
- Description: Resolve an ARN to its file location
- Parameters: arn (required)
- Returns: File path and line number

**ARCHON_GET_DOCUMENT:**
- Name: `archon.get_document`
- Description: Fetch full document text for a doc_id
- Parameters: doc_id (required)

**ARCHON_LIST_REPOS:**
- Name: `archon.list_repos`
- Description: List available repositories
- Parameters: none

## Data Flow

### Search Request Flow (Enhanced)

```mermaid
sequenceDiagram
    participant K as Kiro CLI
    participant M as ArchonMCPServer
    participant Q as Query Service
    participant V as Qdrant
    
    K->>M: POST /mcp/tools/call<br/>{name: "archon.search", arguments: {query: "..."}}
    M->>M: Parse SearchArguments
    M->>Q: QueryClient.retrieve(query, k)
    Q->>V: Vector search
    V-->>Q: Ranked chunks with ARN metadata
    Q-->>M: EnhancedSearchResult[]
    M->>M: Apply repo_filter
    M->>M: Format as MCP response
    M-->>K: ToolCallResponse<br/>{chunks: [{content, arn, related_arns, ...}]}
```

### Graph Query Flow

```mermaid
sequenceDiagram
    participant K as Kiro CLI
    participant M as ArchonMCPServer
    participant G as Code Graph Service
    participant P as PostgreSQL
    
    K->>M: POST /mcp/tools/call<br/>{name: "archon.graph", arguments: {query: "..."}}
    M->>M: Parse GraphQueryInput
    M->>M: Validate query not empty
    M->>G: GraphClient.execute(query, variables)
    G->>P: Execute GraphQL query
    P-->>G: Query results
    G-->>M: GraphQLResponse
    M-->>K: ToolCallResponse<br/>{data: {...}, errors: null}
```

### ARN Resolution Flow

```mermaid
sequenceDiagram
    participant K as Kiro CLI
    participant M as ArchonMCPServer
    participant G as Code Graph Service
    participant P as PostgreSQL
    
    K->>M: POST /mcp/tools/call<br/>{name: "archon.resolve", arguments: {arn: "..."}}
    M->>M: Parse ResolveInput
    M->>M: Validate ARN format
    alt Invalid ARN
        M-->>K: {success: false, error: "Invalid ARN format..."}
    else Valid ARN
        M->>G: ResolveClient.resolve(arn)
        G->>P: Query node by ARN
        P-->>G: Node with file_path, line_number
        G-->>M: ResolveResult
        alt Found
            M-->>K: {success: true, filePath: "...", lineNumber: N}
        else Not Found
            M-->>K: {success: false, error: "Resource not found..."}
        end
    end
```

### Tool Discovery Flow

```mermaid
sequenceDiagram
    participant K as Kiro CLI
    participant M as ArchonMCPServer
    
    K->>M: POST /mcp/tools/list
    M->>M: Return ALL_TOOLS
    M-->>K: ToolListResponse<br/>{tools: [archon.search, archon.graph, archon.resolve, ...]}
    K->>K: Store tool schemas
```

## Technology Stack

- **Python 3.11+**: Runtime
- **FastAPI 0.115.0+**: HTTP framework with automatic OpenAPI docs
- **Uvicorn 0.32.0+**: ASGI server with standard extras (websockets, httptools)
- **AphexServiceClients 0.1.0+**: Query Service client
- **Pydantic 2.0.0+**: Request/response validation

## Architectural Patterns

### Adapter Pattern

ArchonMCPServer adapts the Query Service API to the MCP protocol without changing either system.

**Benefits:**
- Decouples MCP clients from Query Service implementation
- Allows Query Service to evolve independently
- Enables multiple protocol adapters (could add GraphQL, gRPC, etc.)

### Stateless Design

Server maintains no session state between requests.

**Benefits:**
- Horizontal scaling without coordination
- Simple deployment and restart
- No state synchronization complexity

**Trade-off:** Cannot cache results across requests (could add Redis later).

### Thin Wrapper Philosophy

Minimal logic between MCP protocol and Query Service.

**Benefits:**
- Easy to understand and maintain
- Low latency overhead
- Reuses existing retry and error handling

**Trade-off:** Limited ability to optimize or transform results.

## Dependencies

### Upstream Dependencies

**Query Service (port 8080):**
- Provides retrieval API via `QueryClient`
- Required for archon.search tool
- Returns chunks with ARN metadata from enhanced vector store
- Co-located in archon-knowledge-base namespace

**Code Graph Service (port 8080):**
- Provides GraphQL API via `GraphClient` and `ResolveClient`
- Required for archon.graph and archon.resolve tools
- Backed by PostgreSQL with nodes and edges tables
- Co-located in archon-knowledge-base namespace

**Qdrant 1.16.3:**
- Vector database with 768-dim embeddings
- Stores chunks with ARN metadata payload
- Accessed indirectly via Query Service
- Required for all retrieval operations

**PostgreSQL:**
- Stores Code Graph nodes and edges
- Accessed indirectly via Code Graph Service
- Required for graph queries and ARN resolution

**AphexServiceClients:**
- Python package providing QueryClient
- Handles HTTP communication and retry logic
- Version: 0.1.0+

### Downstream Dependencies

**Kiro CLI:**
- Primary consumer via archon-rag.md steering
- Calls MCP endpoints when working on Archon/Aphex code
- Requires HTTP access to port 8090

**Claude Desktop (optional):**
- Can be configured to use ArchonMCPServer
- Requires MCP server configuration in settings

**Cursor (optional):**
- Can be configured to use ArchonMCPServer
- Requires MCP server configuration

## Deployment Architecture

```mermaid
graph TD
    subgraph "archon-knowledge-base namespace"
        A[ArchonMCPServer<br/>Deployment]
        B[Service<br/>mcp-server:8090]
        C[Query Service<br/>:8080]
        D[Qdrant<br/>:6333]
        E[Code Graph Service<br/>:8080]
        F[PostgreSQL<br/>:5432]
    end
    
    subgraph "External"
        G[Kiro CLI]
    end
    
    G -->|HTTP| B
    B --> A
    A -->|QueryClient| C
    A -->|GraphClient| E
    A -->|ResolveClient| E
    C --> D
    E --> F
    
    style A fill:#e1f5ff
    style B fill:#e1f5ff
```

**Namespace:** `archon-knowledge-base` (co-located with Query Service, Code Graph, Qdrant, and PostgreSQL)

**Services:**
- `mcp-server.archon-knowledge-base:8090` - MCP server
- `query.archon-knowledge-base:8080` - Vector store query service
- `graph.archon-knowledge-base:8080` - Code Graph GraphQL service

**Deployment:** Single replica (stateless, can scale horizontally)

**Source**
- `src/archon_mcp/server.py` - FastAPI app and handlers
- `src/archon_mcp/models.py` - Pydantic models
- `src/archon_mcp/tools.py` - Tool definitions
- `src/archon_mcp/clients/graph_client.py` - GraphQL Code Graph client
- `src/archon_mcp/clients/resolve_client.py` - ARN resolution client
- `Dockerfile` - Container image
- `pyproject.toml` - Dependencies
