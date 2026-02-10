# Requirements Document: Enhanced MCP Tools for Knowledge Base

## Introduction

This specification defines enhanced MCP tools for the ArchonMCPServer package that leverage the knowledge base infrastructure to provide graph queries and ARN-enriched searches. These tools enable Kiro agents to navigate code structure, resolve ARNs to file locations, and perform semantic searches with rich metadata.

**This is a child spec** of the root Archon Agent Pipeline specification at `.kiro/specs/archon-agent-pipeline/`. It implements Requirement 14 (Enhanced MCP Tools for Knowledge Base) from the root spec's Phase 2: Knowledge Base Integration.

### Scope

This spec covers:
- Enhancing the existing `archon.search` tool to return ARN metadata
- Implementing a new `archon.graph` tool for GraphQL queries against the Code Graph
- Implementing a new `archon.resolve` tool for ARN-to-location resolution

### Dependencies

This spec depends on:
- **ArchonKnowledgeBaseInfrastructure/code-graph-storage**: Provides the GraphQL Code Graph with PostgreSQL backend
- **ArchonKnowledgeBaseInfrastructure/vector-store-arn**: Provides the Vector Store with ARN metadata in chunk payloads
- **ArchonDocumentationMCPTools**: Provides the ARN library for validation and parsing

### Root Spec Reference

For architectural context and Phase 2 design details, see:
- `.kiro/specs/archon-agent-pipeline/requirements.md` - Requirement 14
- `.kiro/specs/archon-agent-pipeline/design.md` - Phase 2: Knowledge Base Integration Design

## Glossary

- **ARN**: Archon Resource Name - deterministic identifier for graph nodes (format: `arn:archon:<type>:<workspace>/<package>/<path>#<symbol>`)
- **Code_Graph**: GraphQL-queryable representation of code structure and relationships stored in PostgreSQL
- **Vector_Store**: Embedding-based storage for semantic search with ARN metadata (Qdrant)
- **MCP_Tool**: Model Context Protocol tool that provides capabilities to LLM agents
- **GraphQL**: Query language for APIs that enables flexible data retrieval
- **Chunk**: A segment of documentation text stored in the Vector Store with associated metadata

## Requirements

### Requirement 1: Enhanced archon.search with ARN Metadata

**User Story:** As a Kiro agent, I want search results to include ARN metadata, so that I can navigate from search results to the Code Graph for relationship traversal.

#### Acceptance Criteria

1.1 THE archon.search tool SHALL return ARN metadata with each search result including: `arn`, `related_arns`, `symbol_name`, `symbol_kind`, and `package`

1.2 THE `arn` field SHALL contain a valid ARN that resolves to a Code_Graph node when the chunk has an associated symbol

1.3 THE `related_arns` field SHALL contain a list of valid ARNs referenced in the chunk content

1.4 THE `symbol_name` field SHALL contain the name of the documented symbol when applicable, or null otherwise

1.5 THE `symbol_kind` field SHALL contain the kind of symbol (function, class, method, etc.) when applicable, or null otherwise

1.6 THE `package` field SHALL contain the package name where the documented content resides

1.7 THE enhanced search results SHALL maintain backward compatibility with existing search result fields (`content`, `source`, `score`, `doc_id`, `chunk_id`, `repo`)

### Requirement 2: archon.graph Tool for GraphQL Queries

**User Story:** As a Kiro agent, I want to execute GraphQL queries against the Code Graph, so that I can traverse code relationships and find relevant symbols.

#### Acceptance Criteria

2.1 A new `archon.graph` tool SHALL accept GraphQL queries and return results from the Code_Graph

2.2 THE tool SHALL accept a `query` parameter containing a valid GraphQL query string

2.3 THE tool SHALL accept an optional `variables` parameter containing query variables as a JSON object

2.4 THE tool SHALL support all Query operations defined in the GraphQL schema:
  - `node(arn: ID!)` - Direct ARN lookup
  - `searchNodes(name: String!, kind: SymbolKind, package: String, limit: Int)` - Name-based search
  - `findReferences(arn: ID!)` - Find all references to a symbol
  - `symbolsInFile(path: String!, package: String!)` - List symbols in a file
  - `symbolsInPackage(package: String!, kind: SymbolKind)` - List symbols in a package
  - `traverse(startArn: ID!, edgeTypes: [EdgeType!]!, depth: Int)` - Relationship traversal

2.5 THE tool SHALL return results in standard GraphQL response format with `data` and optional `errors` fields

2.6 THE tool SHALL return descriptive error messages for invalid GraphQL queries

2.7 THE tool SHALL return descriptive error messages when the Code_Graph service is unavailable

### Requirement 3: archon.resolve Tool for ARN Resolution

**User Story:** As a Kiro agent, I want to resolve ARNs to file locations, so that I can navigate to referenced code and documentation.

#### Acceptance Criteria

3.1 A new `archon.resolve` tool SHALL accept an ARN and return the file path and line number

3.2 THE tool SHALL accept an `arn` parameter containing a valid ARN string

3.3 WHEN the ARN is valid and resolvable THEN the tool SHALL return:
  - `success: true`
  - `filePath`: Absolute or workspace-relative file path
  - `lineNumber`: Line number in the file (when available)

3.4 WHEN the ARN is invalid (malformed) THEN the tool SHALL return:
  - `success: false`
  - `error`: Descriptive message explaining the ARN format error

3.5 WHEN the ARN is valid but unresolvable (resource not found) THEN the tool SHALL return:
  - `success: false`
  - `error`: Descriptive message indicating the resource could not be found

3.6 THE tool SHALL support resolving both `code` and `doc` ARN types

3.7 THE tool SHALL validate ARN format before attempting resolution

### Requirement 4: Tool Registration and Discovery

**User Story:** As an MCP client, I want the enhanced tools to be properly registered, so that I can discover and invoke them.

#### Acceptance Criteria

4.1 THE enhanced `archon.search` tool SHALL maintain its existing tool name for backward compatibility

4.2 THE `archon.graph` tool SHALL be registered with name `archon.graph`

4.3 THE `archon.resolve` tool SHALL be registered with name `archon.resolve`

4.4 ALL tools SHALL include accurate input schemas describing their parameters

4.5 ALL tools SHALL include descriptive help text explaining their purpose and usage

### Requirement 5: Error Handling and Resilience

**User Story:** As a Kiro agent, I want clear error messages when tools fail, so that I can understand and recover from failures.

#### Acceptance Criteria

5.1 WHEN the Code_Graph service is unavailable THEN `archon.graph` SHALL return an error indicating service unavailability

5.2 WHEN the Vector_Store service is unavailable THEN `archon.search` SHALL return an error indicating service unavailability

5.3 ALL tools SHALL return structured error responses with descriptive messages

5.4 ALL tools SHALL handle timeout conditions gracefully with appropriate error messages

5.5 THE tools SHALL NOT expose internal implementation details in error messages

