# Operations

## Deployment

### Local Development

```bash
# Clone repository
git clone https://github.com/bdchatham/ArchonMCPServer.git
cd ArchonMCPServer

# Install dependencies
pip install -e .

# Set Query Service URL (optional)
export QUERY_SERVICE_URL=http://localhost:8080

# Run server
python -m archon_mcp
```

Server starts on `http://localhost:8090`

### Docker Deployment

```bash
# Build image
docker build -t archon-mcp-server:latest .

# Run container
docker run -p 8090:8090 \
  -e QUERY_SERVICE_URL=http://query.archon-knowledge-base:8080 \
  archon-mcp-server:latest
```

### Kubernetes Deployment

```bash
# Apply manifests
kubectl apply -f manifests/

# Verify deployment
kubectl get pods -n archon-knowledge-base -l app=mcp-server
kubectl get svc -n archon-knowledge-base mcp-server

# Check logs
kubectl logs -n archon-knowledge-base -l app=mcp-server --tail=50
```

**Configuration:**
- Namespace: `archon-knowledge-base`
- Service: `mcp-server:8090`
- Replicas: 1 (stateless, can scale horizontally)

## Monitoring

### Health Checks

**Endpoint:** `GET /health`

**Expected Response:**
```json
{"status": "healthy"}
```

**Kubernetes Probes:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8090
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health
    port: 8090
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Logs

**View Logs:**
```bash
kubectl logs -n archon-knowledge-base -l app=mcp-server -f
```

**Key Log Events:**
- Server startup: `Uvicorn running on http://0.0.0.0:8090`
- Tool invocations: `POST /mcp/tools/call` with status code
- Errors: Exception tracebacks with context

### Metrics (TODO)

**Planned Prometheus Metrics:**
- Tool invocation counts by tool name
- Tool invocation latency (p50, p95, p99)
- Query Service call latency
- Error rates by tool and error type

## Alerting

### Critical Alerts (TODO)

**Server Down:**
- Condition: Health check fails for 3 consecutive checks
- Action: Restart pod, check Query Service connectivity

**High Error Rate:**
- Condition: >10% of tool invocations fail in 5-minute window
- Action: Check Query Service logs, verify Qdrant connectivity

**High Latency:**
- Condition: p95 latency >5 seconds
- Action: Check Query Service performance, review Qdrant query times

## Runbooks

### Common Issues

#### Server Won't Start

**Symptom:** Container crashes or exits immediately

**Resolution:**
```bash
# Check container logs
docker logs <container-id>

# Verify dependencies
pip list | grep -E "fastapi|uvicorn|aphex"

# Test with different port
docker run -p 8091:8090 archon-mcp-server:latest
```

#### Tool Invocation Fails

**Symptom:** `/mcp/tools/call` returns error response

**Resolution:**
```bash
# Test Query Service connectivity
kubectl exec -n archon-knowledge-base <mcp-server-pod> -- \
  curl http://query.archon-knowledge-base:8080/health

# Check Query Service logs
kubectl logs -n archon-knowledge-base -l app=query

# Verify tool arguments
curl -X POST http://localhost:8090/mcp/tools/list | jq
```

#### No Search Results

**Symptom:** `archon.search` returns empty chunks array

**Resolution:**
```bash
# Check Qdrant collection
kubectl port-forward -n archon-knowledge-base svc/qdrant 6333:6333
curl http://localhost:6333/collections/archon_docs | jq '.result.points_count'

# Test with broader query
curl -X POST http://localhost:8090/mcp/tools/call \
  -d '{"name": "archon.search", "arguments": {"query": "deployment", "top_k": 10}}'
```

### Troubleshooting

#### High Latency

**Symptom:** Tool invocations take >5 seconds

**Diagnosis:**
```bash
# Check Query Service response time
time curl http://query.archon-knowledge-base:8080/health

# Check Qdrant response time
time curl http://qdrant.archon-knowledge-base:6333/collections

# Review Query Service logs
kubectl logs -n archon-knowledge-base -l app=query | grep -i "slow\|timeout"
```

**Resolution:**
- Scale Query Service if under load
- Optimize Qdrant queries
- Check network latency between services

#### Query Service Unreachable

**Symptom:** All tool invocations fail with connection errors

**Diagnosis:**
```bash
# Verify Query Service is running
kubectl get pods -n archon-knowledge-base -l app=query

# Test connectivity from MCP server pod
kubectl exec -n archon-knowledge-base <mcp-server-pod> -- \
  curl -v http://query.archon-knowledge-base:8080/health
```

**Resolution:**
- Restart Query Service if crashed
- Verify Service DNS resolution
- Check NetworkPolicies if enabled

## Maintenance

### Updating Dependencies

```bash
# Update pyproject.toml with new versions
# Rebuild container image
docker build -t archon-mcp-server:v0.2.0 .

# Push to registry
docker push archon-mcp-server:v0.2.0

# Update Kubernetes deployment
kubectl set image deployment/mcp-server -n archon-knowledge-base \
  mcp-server=archon-mcp-server:v0.2.0
```

### Scaling

```bash
# Scale horizontally (stateless design)
kubectl scale deployment/mcp-server -n archon-knowledge-base --replicas=3

# Verify all replicas are ready
kubectl get pods -n archon-knowledge-base -l app=mcp-server
```

### Testing MCP Endpoints

```bash
# List available tools
curl -X POST http://localhost:8090/mcp/tools/list | jq

# Search documentation
curl -X POST http://localhost:8090/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "archon.search",
    "arguments": {
      "query": "How do I deploy a service?",
      "top_k": 3
    }
  }' | jq
```

**Source**
- `src/archon_mcp/server.py` - Server implementation
- `src/archon_mcp/__main__.py` - CLI entrypoint
- `Dockerfile` - Container image
- `manifests/` - Kubernetes manifests (to be created)
