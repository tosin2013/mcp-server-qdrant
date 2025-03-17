# Build stage
FROM python:3.11-slim AS builder

# Set build-time arguments
ARG VERSION
ARG BUILD_DATE
ARG VCS_REF

# Set build-time labels according to OCI image spec
LABEL org.opencontainers.image.title="MCP Server Qdrant"
LABEL org.opencontainers.image.description="Model Context Protocol server for Qdrant vector database"
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.revision=${VCS_REF}
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.url="https://github.com/modelcontextprotocol/mcp-server-qdrant"
LABEL org.opencontainers.image.source="https://github.com/modelcontextprotocol/mcp-server-qdrant"
LABEL org.opencontainers.image.vendor="Model Context Protocol"

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Install build dependencies first for better layer caching
RUN pip install --no-cache-dir hatchling

# Copy requirements file first
COPY requirements.txt ./

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY pyproject.toml README.md VERSION ./

# Install the package in development mode
RUN pip install --no-cache-dir -e .

# Copy source code
COPY src/ ./src/

# Build wheel package
RUN pip wheel --no-deps -w dist .

# Debug: List contents for verification
RUN echo "Contents of /app/dist:" && \
    ls -la /app/dist

# Runtime stage
FROM python:3.11-slim AS runtime

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    dnsutils \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 app && \
    mkdir -p /app && \
    chown -R app:app /app

WORKDIR /app

# Create a startup script
RUN echo '#!/bin/bash\n\
echo "Waiting for Qdrant to be ready..."\n\
QDRANT_HOST=$(echo $QDRANT_URL | sed -e "s|http://||" -e "s|https://||" -e "s|/.*||" -e "s|:.*||")\n\
QDRANT_PORT=$(echo $QDRANT_URL | sed -e "s|.*:||" -e "s|/.*||")\n\
if [ -z "$QDRANT_PORT" ]; then\n\
  QDRANT_PORT=6333\n\
fi\n\
echo "Checking Qdrant at $QDRANT_HOST:$QDRANT_PORT"\n\
\n\
# First, wait for DNS resolution\n\
for i in $(seq 1 30); do\n\
  if nslookup $QDRANT_HOST >/dev/null 2>&1; then\n\
    echo "DNS resolution successful for $QDRANT_HOST"\n\
    break\n\
  fi\n\
  echo "Waiting for DNS resolution for $QDRANT_HOST... (attempt $i/30)"\n\
  sleep 2\n\
done\n\
\n\
# Then, wait for port to be open\n\
for i in $(seq 1 30); do\n\
  if nc -z $QDRANT_HOST $QDRANT_PORT >/dev/null 2>&1; then\n\
    echo "Port $QDRANT_PORT is open on $QDRANT_HOST"\n\
    break\n\
  fi\n\
  echo "Waiting for port $QDRANT_PORT on $QDRANT_HOST... (attempt $i/30)"\n\
  sleep 2\n\
done\n\
\n\
# Finally, wait for Qdrant to be ready\n\
for i in $(seq 1 30); do\n\
  if curl -s -f "$QDRANT_URL/collections" > /dev/null; then\n\
    echo "Qdrant is ready!"\n\
    break\n\
  fi\n\
  echo "Waiting for Qdrant API... (attempt $i/30)"\n\
  sleep 2\n\
done\n\
\n\
echo "Starting MCP server..."\n\
exec mcp-server-qdrant "$@"\n' > /app/start.sh && \
    chmod +x /app/start.sh

# Copy wheel and requirements from builder
COPY --from=builder /app/dist/*.whl /app/
COPY --from=builder /app/requirements.txt /app/

# Install runtime dependencies and package
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir *.whl && \
    rm *.whl requirements.txt

USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint to our startup script
ENTRYPOINT ["/app/start.sh"]

# Default command
CMD ["--transport", "sse", "--host", "0.0.0.0", "--port", "8000"] 