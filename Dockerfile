FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY src/ src/

ENV QUERY_SERVICE_URL=http://query.archon-knowledge-base:8080

EXPOSE 8090

CMD ["python", "-m", "archon_mcp"]
