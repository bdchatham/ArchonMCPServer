# FAQ

## General Questions

### What is ArchonMCPServer?

ArchonMCPServer is an HTTP server that exposes the Archon RAG system as MCP (Model Context Protocol) tools. It allows AI assistants like Kiro CLI to search internal documentation and retrieve grounded information instead of hallucinating.

### Why MCP instead of a custom API?

MCP is a standardized protocol supported by multiple LLM clients (Kiro, Claude Desktop, Cursor). Using MCP means:
- No custom client integration needed
- Tools are automatically discovered by clients
- Standard request/response format
- Works with any MCP-compatible client

### How does this integrate with Kiro?

Repositories using ArchonKiroTemplate include `.kiro/steering/archon-rag.md`, which instructs Kiro to call MCP tools before making implementation decisions. No manual configuration needed.

### What's the difference between archon.search and archon.get_document?

- `archon.search`: Returns top-k ranked chunks with provenance. Use for finding relevant information.
- `archon.get_document`: Returns full document text. Use when you need complete context for edits or generation.

## Deployment Questions

### Where should I deploy ArchonMCPServer?

Deploy in the `archon-knowledge-base` namespace alongside Query Service and Qdrant for minimal latency. The server is stateless and can scale horizontally.

### Can I run this locally?

Yes! Set `QUERY_SERVICE_URL` to point to your Query Service (local or remote) and run `python -m archon_mcp`. Useful for development and testing.

### How do I expose this to external clients?

Options:
1. **Port forward:** `kubectl port-forward -n archon-knowledge-base svc/mcp-server 8090:8090`
2. **Ingress:** Create an Ingress resource with TLS and authentication
3. **LoadBalancer:** Change Service type to LoadBalancer (adds authentication first!)

**Security:** Add authentication before exposing publicly.

## Usage Questions

### How do I test the MCP endpoints?

```bash
# List tools
curl -X POST http://localhost:8090/mcp/tools/list | jq

# Search
curl -X POST http://localhost:8090/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "archon.search", "arguments": {"query": "deployment", "top_k": 3}}' | jq
```

### Why am I getting empty search results?

Possible causes:
1. Qdrant index is empty (check document ingestion)
2. Query doesn't match any documents (try broader terms)
3. Embedding model mismatch (verify BAAI/bge-base-en-v1.5)

Check Qdrant collection:
```bash
kubectl port-forward -n archon-knowledge-base svc/qdrant 6333:6333
curl http://localhost:6333/collections/archon_docs | jq '.result.points_count'
```

### How do I filter results to a specific repository?

Use the `repo_filter` argument:
```json
{
  "name": "archon.search",
  "arguments": {
    "query": "vLLM version",
    "repo_filter": "ArchonAgent"
  }
}
```

### Can I use this with Claude Desktop?

Yes! Configure Claude Desktop to use ArchonMCPServer as an MCP server. You'll need to add the server URL to Claude's MCP configuration file.

## Technical Questions

### Why is archon.get_document not implemented?

The Query Service currently only returns chunks, not full documents. Implementation requires either:
1. Querying Qdrant directly for document metadata
2. Fetching from GitHub API
3. Maintaining a document cache

Planned for future release.

### Why is archon.list_repos hardcoded?

Metadata about repositories isn't currently stored in Qdrant. Implementation requires:
1. Adding metadata collection during document ingestion
2. Storing repo info in Qdrant or separate metadata store
3. Querying metadata in list_repos handler

Planned for future release.

### How does retry logic work?

ArchonMCPServer uses `AphexServiceClients.QueryClient`, which has built-in retry:
- 5 attempts maximum
- Exponential backoff (1s initial, 60s max)
- Random jitter (0-5s) to prevent thundering herd
- Retries on connection errors and timeouts

### What's the performance overhead?

Minimal. ArchonMCPServer adds ~10-50ms latency:
- Request parsing: <5ms
- Query Service call: depends on Query Service (typically 100-500ms)
- Response formatting: <5ms

Total latency dominated by Query Service and Qdrant query time.

### Can I scale this horizontally?

Yes! ArchonMCPServer is stateless. Scale with:
```bash
kubectl scale deployment/mcp-server -n archon-knowledge-base --replicas=3
```

Load balancing handled by Kubernetes Service.

## Troubleshooting

### Server won't start

Check:
1. Dependencies installed: `pip list | grep -E "fastapi|uvicorn|aphex"`
2. Port 8090 available: `lsof -i :8090`
3. `QUERY_SERVICE_URL` format: Must be valid HTTP URL

### Tool invocations fail with connection errors

Check Query Service connectivity:
```bash
kubectl exec -n archon-knowledge-base <mcp-server-pod> -- \
  curl http://query.archon-knowledge-base:8080/health
```

If Query Service is down, restart it:
```bash
kubectl rollout restart deployment/query -n archon-knowledge-base
```

### High latency (>5 seconds)

Check:
1. Query Service performance: `kubectl logs -n archon-knowledge-base -l app=query`
2. Qdrant query time: Review Query Service logs for slow queries
3. Network latency: Ensure MCP server and Query Service are co-located

### Invalid tool arguments error

Verify arguments match tool schema:
```bash
curl -X POST http://localhost:8090/mcp/tools/list | \
  jq '.tools[] | select(.name=="archon.search") | .inputSchema'
```

Common mistakes:
- Missing required `query` parameter
- `top_k` as string instead of number
- Typo in tool name

## Integration Questions

### How do I add this to my Kiro workflow?

If your repository uses ArchonKiroTemplate, it's automatic! The `.kiro/steering/archon-rag.md` file instructs Kiro to use MCP tools.

If not, copy the steering file:
```bash
curl -o .kiro/steering/archon-rag.md \
  https://raw.githubusercontent.com/bdchatham/ArchonKiroTemplate/mainline/.kiro/steering/archon-rag.md
```

### Can I use this without Kubernetes?

Yes! Run locally with Docker:
```bash
docker run -p 8090:8090 \
  -e QUERY_SERVICE_URL=http://your-query-service:8080 \
  archon-mcp-server:latest
```

Or directly with Python:
```bash
export QUERY_SERVICE_URL=http://your-query-service:8080
python -m archon_mcp
```

### How do I monitor MCP tool usage?

Currently: Check server logs for `/mcp/tools/call` requests.

Planned: Prometheus metrics for tool invocation counts, latency, and error rates.

**Source**
- `src/archon_mcp/server.py` - Implementation
- `.kiro/steering/archon-rag.md` - Kiro integration guidance
- `README.md` - Quick start guide
