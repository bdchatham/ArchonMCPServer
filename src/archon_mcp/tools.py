"""MCP tool definitions for Archon RAG system."""

from .models import Tool

ARCHON_SEARCH = Tool(
    name="archon.search",
    description=(
        "Search across internal Archon/Aphex documentation with ARN metadata.\n\n"
        "Returns ranked chunks with provenance and ARN metadata for graph traversal:\n"
        "- content: The chunk text\n"
        "- source: File path (e.g., 'ArchonAgent/src/orchestrator/main.py')\n"
        "- score: Relevance score\n"
        "- arn: ARN of the documented symbol/file\n"
        "- related_arns: ARNs referenced in this chunk\n"
        "- symbol_name: Name of the documented symbol (if applicable)\n"
        "- symbol_kind: Kind of symbol (function, class, etc.)\n"
        "- package: Package name\n\n"
        "Use before answering anything that depends on internal architecture, patterns, or conventions.\n"
        "Use the ARN to navigate to the Code Graph for relationship traversal."
    ),
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

ARCHON_GET_DOCUMENT = Tool(
    name="archon.get_document",
    description="Fetch full document text for a doc_id. Use when you need complete context for edits, spec generation, or detailed understanding.",
    inputSchema={
        "type": "object",
        "properties": {
            "doc_id": {
                "type": "string",
                "description": "Document ID from search results"
            }
        },
        "required": ["doc_id"]
    }
)

ARCHON_LIST_REPOS = Tool(
    name="archon.list_repos",
    description="List available repositories in the Archon knowledge base with descriptions and last updated timestamps.",
    inputSchema={
        "type": "object",
        "properties": {}
    }
)

ARCHON_GRAPH = Tool(
    name="archon.graph",
    description=(
        "Execute GraphQL queries against the Code Graph.\n\n"
        "The Code Graph stores code structure as a property graph with ARNs as primary identifiers.\n"
        "Use this tool to traverse code relationships and find relevant symbols.\n\n"
        "Supported queries:\n"
        "- node(arn: ID!): Direct ARN lookup\n"
        "- searchNodes(name: String!, kind: SymbolKind, package: String, limit: Int): Name-based search\n"
        "- findReferences(arn: ID!): Find all references to a symbol\n"
        "- symbolsInFile(path: String!, package: String!): List symbols in a file\n"
        "- symbolsInPackage(package: String!, kind: SymbolKind): List symbols in a package\n"
        "- traverse(startArn: ID!, edgeTypes: [EdgeType!]!, depth: Int): Relationship traversal\n\n"
        "SymbolKind: FUNCTION, CLASS, METHOD, VARIABLE, TYPE, MODULE, FILE, PACKAGE\n"
        "EdgeType: CONTAINS, REFERENCES, IMPLEMENTS, EXTENDS, IMPORTS, DOCUMENTS\n\n"
        "Returns standard GraphQL response format with 'data' and optional 'errors' fields."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "GraphQL query string",
            },
            "variables": {
                "type": "object",
                "description": "Optional query variables as JSON object",
            },
        },
        "required": ["query"],
    },
)

ARCHON_RESOLVE = Tool(
    name="archon.resolve",
    description=(
        "Resolve an ARN to its file location.\n\n"
        "ARN format: arn:archon:<type>:<workspace>/<package>/<path>#<symbol>\n"
        "- type: code, doc, k8s, infra\n"
        "- workspace: Workspace identifier\n"
        "- package: Package/repository name\n"
        "- path: File path relative to package\n"
        "- symbol: Symbol name (optional)\n\n"
        "Returns:\n"
        "- success: true/false\n"
        "- filePath: Workspace-relative file path (when success=true)\n"
        "- lineNumber: Line number in the file (when available)\n"
        "- error: Descriptive error message (when success=false)\n\n"
        "Use this tool to navigate from search results or graph nodes to actual code locations."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "arn": {
                "type": "string",
                "description": "ARN string to resolve",
            }
        },
        "required": ["arn"],
    },
)

ALL_TOOLS = [ARCHON_SEARCH, ARCHON_GET_DOCUMENT, ARCHON_LIST_REPOS, ARCHON_GRAPH, ARCHON_RESOLVE]
