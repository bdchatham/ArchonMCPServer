# Implementation Plan: Enhanced MCP Tools for Knowledge Base

## Overview

This task list implements the enhanced MCP tools for the ArchonMCPServer package that leverage the knowledge base infrastructure. The implementation follows a bottom-up approach:

1. **Data Models** - Define input/output schemas and internal models
2. **Service Clients** - Implement clients for Code Graph and Vector Store
3. **Tool Enhancements** - Update archon.search and implement new tools
4. **Testing** - Unit tests, integration tests, and property-based tests

**Parent Spec Reference:** `.kiro/specs/archon-agent-pipeline/` - Requirement 14 (Enhanced MCP Tools for Knowledge Base)

## Tasks

### Phase 1: Data Models

- [x] 1. Create data models for enhanced tools
  - [x] 1.1 Create EnhancedSearchResult model
    - Add `EnhancedSearchResult` dataclass to `src/archon_mcp/models.py`
    - Include existing fields: `content`, `source`, `score`, `chunk_index`, `repo`
    - Add ARN metadata fields: `arn`, `related_arns`, `symbol_name`, `symbol_kind`, `package`
    - Ensure backward compatibility with existing search result structure
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_
  
  - [x] 1.2 Create GraphQL input/output models
    - Add `GraphQueryInput` dataclass with `query` and optional `variables` fields
    - Add `GraphQueryOutput` dataclass with `data` and optional `errors` fields
    - Add `GraphQLError` dataclass with `message`, `locations`, `path`, `extensions` fields
    - _Requirements: 2.2, 2.3, 2.5_
  
  - [x] 1.3 Create resolve input/output models
    - Add `ResolveInput` dataclass with `arn` field
    - Add `ResolveOutput` dataclass with `success`, `file_path`, `line_number`, `error` fields
    - Add `ResolveResult` internal dataclass with `found`, `file_path`, `line_number` fields
    - _Requirements: 3.2, 3.3, 3.4, 3.5_
  
  - [x] 1.4 Create ARN validation model
    - Add `ARNValidationResult` dataclass with `valid` and optional `error` fields
    - _Requirements: 3.4, 3.7_

### Phase 2: Service Clients

- [x] 2. Create service client infrastructure
  - [x] 2.1 Create clients module structure
    - Create `src/archon_mcp/clients/` directory
    - Create `src/archon_mcp/clients/__init__.py` with exports
    - _Requirements: 2.1, 3.1_
  
  - [x] 2.2 Create custom exception classes
    - Add `ServiceUnavailableError` exception with `service_name` and `details` attributes
    - Add `GraphQLValidationError` exception with `message` attribute
    - Add to `src/archon_mcp/clients/__init__.py` or separate `exceptions.py`
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 2.3 Create GraphClient class
    - Create `src/archon_mcp/clients/graph_client.py`
    - Implement async context manager (`__aenter__`, `__aexit__`)
    - Implement `execute(query, variables, timeout)` method
    - Handle connection errors and raise `ServiceUnavailableError`
    - Handle GraphQL validation errors and raise `GraphQLValidationError`
    - _Requirements: 2.1, 2.4, 2.6, 2.7, 5.1_
  
  - [x] 2.4 Create ResolveClient class
    - Create `src/archon_mcp/clients/resolve_client.py`
    - Implement async context manager (`__aenter__`, `__aexit__`)
    - Implement `resolve(arn, timeout)` method returning `ResolveResult`
    - Handle connection errors and raise `ServiceUnavailableError`
    - _Requirements: 3.1, 3.3, 3.5, 5.1_
  
  - [x] 2.5 Implement ARN validation function
    - Create `validate_arn(arn: str) -> ARNValidationResult` function
    - Validate ARN prefix (`arn:archon:`)
    - Validate ARN type (`code`, `doc`, `k8s`, `infra`)
    - Validate resource path structure (`workspace/package/path`)
    - Return descriptive error messages for invalid formats
    - _Requirements: 3.4, 3.6, 3.7_

### Phase 3: archon.search Enhancement

- [x] 3. Enhance archon.search with ARN metadata
  - [x] 3.1 Update search tool to return ARN metadata
    - Modify search handler in `src/archon_mcp/server.py` or `src/archon_mcp/tools.py`
    - Extract ARN metadata from vector store response payload
    - Map payload fields to `EnhancedSearchResult` model
    - Include `arn`, `related_arns`, `symbol_name`, `symbol_kind`, `package` in response
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
  
  - [x] 3.2 Maintain backward compatibility
    - Ensure existing fields (`content`, `source`, `score`, `chunk_index`, `repo`) remain unchanged
    - Verify response structure matches existing clients' expectations
    - Handle missing ARN metadata gracefully (use null/empty defaults)
    - _Requirements: 1.7, 4.1_
  
  - [x] 3.3 Update tool description
    - Update `archon.search` tool description to document ARN metadata fields
    - Explain how to use ARN for graph traversal
    - Document relationship between search results and Code Graph
    - _Requirements: 4.4, 4.5_

### Phase 4: archon.graph Implementation

- [x] 4. Implement archon.graph tool
  - [x] 4.1 Create archon.graph tool definition
    - Add tool definition with name `archon.graph`
    - Define input schema with `query` (required) and `variables` (optional) parameters
    - Add comprehensive description documenting supported queries
    - Document SymbolKind and EdgeType enums in description
    - _Requirements: 2.1, 2.2, 2.3, 4.2, 4.4, 4.5_
  
  - [x] 4.2 Implement GraphQL query execution
    - Create `graph` tool handler function
    - Validate query is not empty
    - Use `GraphClient` to execute query against Code Graph service
    - Return response in standard GraphQL format (`data`, `errors`)
    - _Requirements: 2.1, 2.4, 2.5_
  
  - [x] 4.3 Implement error handling for archon.graph
    - Handle empty/invalid query input with descriptive error
    - Handle `GraphQLValidationError` with user-friendly message
    - Handle `ServiceUnavailableError` with service unavailability message
    - Handle unexpected exceptions without exposing internal details
    - _Requirements: 2.6, 2.7, 5.1, 5.3, 5.5_

### Phase 5: archon.resolve Implementation

- [x] 5. Implement archon.resolve tool
  - [x] 5.1 Create archon.resolve tool definition
    - Add tool definition with name `archon.resolve`
    - Define input schema with `arn` (required) parameter
    - Add description documenting ARN format and return values
    - Document success and failure response structures
    - _Requirements: 3.1, 3.2, 4.3, 4.4, 4.5_
  
  - [x] 5.2 Implement ARN validation in resolve handler
    - Call `validate_arn()` before attempting resolution
    - Return structured error for invalid ARN format
    - Include descriptive error message explaining format requirements
    - _Requirements: 3.4, 3.7_
  
  - [x] 5.3 Implement resolution logic
    - Use `ResolveClient` to resolve ARN to file location
    - Return `success: true` with `filePath` and optional `lineNumber` on success
    - Return `success: false` with `error` message when resource not found
    - Support both `code` and `doc` ARN types
    - _Requirements: 3.1, 3.3, 3.5, 3.6_
  
  - [x] 5.4 Implement error handling for archon.resolve
    - Handle `ServiceUnavailableError` with service unavailability message
    - Handle unexpected exceptions without exposing internal details
    - Ensure all error paths return structured response with `success: false`
    - _Requirements: 5.1, 5.3, 5.4, 5.5_

### Phase 6: Unit Tests

- [x] 6. Create unit tests
  - [x] 6.1 Create ARN validation tests
    - Create `tests/unit/test_arn_validation.py`
    - Test valid ARN formats for all types (`code`, `doc`, `k8s`, `infra`)
    - Test invalid ARN formats (missing prefix, invalid type, malformed resource)
    - Test edge cases (empty string, very long ARNs, special characters)
    - _Requirements: 3.4, 3.7_
  
  - [x] 6.2 Create response model tests
    - Create `tests/unit/test_response_models.py`
    - Test `EnhancedSearchResult` construction and serialization
    - Test `GraphQueryOutput` construction with data and errors
    - Test `ResolveOutput` construction for success and failure cases
    - _Requirements: 1.1-1.7, 2.5, 3.3, 3.4, 3.5_
  
  - [x] 6.3 Create error handling tests
    - Create `tests/unit/test_error_handling.py`
    - Test `ServiceUnavailableError` construction and message formatting
    - Test `GraphQLValidationError` construction and message formatting
    - Test timeout handling with mock async operations
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

### Phase 7: Integration Tests

- [x] 7. Create integration tests
  - [x] 7.1 Create enhanced search integration tests
    - Create `tests/integration/test_search_enhanced.py`
    - Test search with ARN metadata returned
    - Test repo filtering with ARN metadata
    - Test empty results handling
    - Test backward compatibility with existing response fields
    - _Requirements: 1.1-1.7, 4.1_
  
  - [x] 7.2 Create graph tool integration tests
    - Create `tests/integration/test_graph_tool.py`
    - Test node lookup by ARN
    - Test search nodes by name
    - Test relationship traversal
    - Test invalid query handling
    - Test service unavailability handling
    - _Requirements: 2.1-2.7, 5.1_
  
  - [x] 7.3 Create resolve tool integration tests
    - Create `tests/integration/test_resolve_tool.py`
    - Test resolve code ARN to file location
    - Test resolve doc ARN to file location
    - Test invalid ARN format handling
    - Test not found handling
    - Test service unavailability handling
    - _Requirements: 3.1-3.7, 5.1_

### Phase 8: Property-Based Tests

- [x] 8. Create property-based tests
  - [x] 8.1 (PBT) Property 1: Enhanced Search Backward Compatibility
    - Create `tests/property/test_backward_compatibility.py`
    - Generate random search queries
    - Verify all existing fields (`content`, `source`, `score`, `chunk_index`, `repo`) present in response
    - Verify ARN metadata fields are present (may be null)
    - **Validates: Requirement 1.7**
    - _Requirements: 1.7_
  
  - [x] 8.2 (PBT) Property 2: ARN Metadata Validity
    - Create `tests/property/test_arn_validity.py`
    - Generate search results with ARN metadata
    - Verify all non-null ARNs pass format validation
    - Verify `related_arns` list contains only valid ARNs
    - **Validates: Requirements 1.1, 1.2**
    - _Requirements: 1.1, 1.2_
  
  - [x] 8.3 (PBT) Property 5: ARN Validation Before Resolution
    - Create `tests/property/test_validation_ordering.py`
    - Generate random ARN strings (valid and invalid)
    - Verify validation occurs before resolution attempt
    - Verify invalid ARNs return format error without calling resolve service
    - **Validates: Requirements 3.4, 3.7**
    - _Requirements: 3.4, 3.7_

## Notes

- **Testing Framework**: pytest with pytest-asyncio for async tests
- **Property Testing**: hypothesis library for property-based tests
- **Mocking**: pytest-mock for service client mocking in unit tests
- **Minimum Property Test Iterations**: 100

## Dependencies

This spec depends on:
- **ArchonKnowledgeBaseInfrastructure/code-graph-storage**: GraphQL Code Graph with PostgreSQL backend
- **ArchonKnowledgeBaseInfrastructure/vector-store-arn**: Vector Store with ARN metadata in chunk payloads
- **ArchonDocumentationMCPTools**: ARN library for validation and parsing

## Configuration

Environment variables required:
- `QUERY_SERVICE_URL`: Vector store query service URL (default: `http://query.archon-knowledge-base:8080`)
- `GRAPH_SERVICE_URL`: Code Graph GraphQL service URL (default: `http://graph.archon-knowledge-base:8080`)
- `REQUEST_TIMEOUT`: Default request timeout in seconds (default: `30`)

## Source

- `ArchonMCPServer/.kiro/specs/enhanced-tools/requirements.md` - Requirements document
- `ArchonMCPServer/.kiro/specs/enhanced-tools/design.md` - Design document
- `.kiro/specs/archon-agent-pipeline/` - Root spec with Phase 2 design
