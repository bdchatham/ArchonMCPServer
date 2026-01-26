"""MCP tool definitions for Archon RAG system."""

from .models import Tool

ARCHON_SEARCH = Tool(
    name="archon.search",
    description="Search across internal Archon/Aphex documentation. Returns ranked chunks with provenance (doc_id, chunk_id, source_path, repo, content, score). Use before answering anything that depends on internal architecture, patterns, or conventions.",
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

ALL_TOOLS = [ARCHON_SEARCH, ARCHON_GET_DOCUMENT, ARCHON_LIST_REPOS]
