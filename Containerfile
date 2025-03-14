# Build stage
FROM python:3.11-slim as builder

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

# Install build dependencies first for better layer caching
RUN pip install --no-cache-dir hatchling

# Copy dependency files first
COPY pyproject.toml README.md VERSION ./

# Generate requirements.txt for reproducible builds
RUN pip install --no-cache-dir pip-tools && \
    pip-compile --no-emit-index-url pyproject.toml -o requirements.txt

# Copy source code
COPY src/ ./src/

# Build wheel package
RUN pip wheel --no-deps -w dist .

# Debug: List contents for verification
RUN echo "Contents of /app/dist:" && \
    ls -la /app/dist && \
    echo "\nContents of requirements.txt:" && \
    cat requirements.txt

# Runtime stage
FROM python:3.11-slim

# Install curl for health check
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user and app directory
RUN useradd -m -u 1000 app && \
    mkdir -p /app && \
    chown -R app:app /app

WORKDIR /app

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
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint
ENTRYPOINT ["mcp-server-qdrant"] 