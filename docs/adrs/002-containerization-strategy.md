# ADR-002: Containerization Strategy

## Status
Proposed

## Context
The MCP server for Qdrant needs to be easily deployable across different environments while maintaining consistency and isolation. Containerization provides these benefits, and we want to support both Docker and Podman to give users flexibility in their container runtime choice.

### Current Situation
- The project currently has a basic Dockerfile
- Some users may prefer Podman for its daemonless and rootless container operations
- We need to ensure consistent behavior across both container runtimes

## Decision

### Container Strategy Overview
We will support both Docker and Podman by:
1. Using OCI (Open Container Initiative) compliant container configurations
2. Providing separate build files and instructions for both runtimes
3. Implementing multi-stage builds for optimized images
4. Supporting both rootful and rootless operations

### Base Image Selection
- Use Python 3.10+ slim images as base
- Implement multi-arch support (amd64/arm64)
- Maintain minimal image size while ensuring all dependencies are included

### Container Configuration

#### Dockerfile Structure
```dockerfile
# Build stage
FROM python:3.10-slim as builder
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN pip install build && \
    python -m build

# Runtime stage
FROM python:3.10-slim
WORKDIR /app
COPY --from=builder /app/dist/*.whl .
RUN pip install *.whl && \
    rm *.whl

# Non-root user setup
RUN useradd -m -u 1000 mcp
USER mcp

EXPOSE 8000
ENTRYPOINT ["mcp-server-qdrant"]
```

#### Containerfile (Podman) Structure
```dockerfile
# Same as Dockerfile but with Podman-specific optimizations
# Build stage
FROM docker.io/python:3.10-slim as builder
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN pip install build && \
    python -m build

# Runtime stage
FROM docker.io/python:3.10-slim
WORKDIR /app
COPY --from=builder /app/dist/*.whl .
RUN pip install *.whl && \
    rm *.whl

# Non-root user setup (Podman-specific)
RUN useradd -m -u 1000 mcp
USER mcp

EXPOSE 8000
ENTRYPOINT ["mcp-server-qdrant"]
```

### Security Considerations
1. **Rootless Operation**
   - Support rootless container execution in both Docker and Podman
   - Configure appropriate file permissions
   - Use non-root user inside containers

2. **Image Scanning**
   - Implement container image scanning in CI/CD
   - Regular security updates for base images
   - Vulnerability scanning using tools like Trivy

### Build and Deployment Scripts

#### Docker Build Script
```bash
#!/bin/bash
DOCKER_BUILDKIT=1 docker build \
  --platform linux/amd64,linux/arm64 \
  --tag mcp-server-qdrant:latest \
  --file Dockerfile .
```

#### Podman Build Script
```bash
#!/bin/bash
podman build \
  --platform linux/amd64,linux/arm64 \
  --tag mcp-server-qdrant:latest \
  --file Containerfile .
```

### Development Workflow
1. Local Development:
   ```bash
   # Docker
   docker compose up -d
   
   # Podman
   podman-compose up -d
   ```

2. Testing:
   ```bash
   # Docker
   docker compose -f docker-compose.test.yml up --exit-code-from tests
   
   # Podman
   podman-compose -f podman-compose.test.yml up --exit-code-from tests
   ```

### CI/CD Integration
- GitHub Actions workflow for Docker builds
- GitLab CI template for Podman builds
- Automated testing in containerized environments
- Container registry publishing

## Consequences

### Positive
- Consistent deployment across different environments
- Support for both Docker and Podman users
- Enhanced security through rootless operation
- Optimized image sizes through multi-stage builds
- Clear separation of development and production environments

### Negative
- Additional maintenance for two container configurations
- Increased complexity in CI/CD pipelines
- Need to test both Docker and Podman workflows
- Potential differences in behavior between runtimes

### Risks
- Version compatibility issues between Docker and Podman
- Different behavior in rootless mode between runtimes
- Performance variations between container runtimes

## Implementation Plan

1. **Phase 1: Docker Enhancement**
   - Update existing Dockerfile with multi-stage builds
   - Implement security best practices
   - Add Docker Compose configurations

2. **Phase 2: Podman Support**
   - Create Containerfile for Podman
   - Test rootless operation
   - Document Podman-specific instructions

3. **Phase 3: CI/CD Integration**
   - Update GitHub Actions for Docker builds
   - Add GitLab CI templates for Podman
   - Implement container scanning

4. **Phase 4: Documentation**
   - Update README with both Docker and Podman instructions
   - Add troubleshooting guides
   - Document security considerations

## References
- [OCI Container Specification](https://github.com/opencontainers/runtime-spec)
- [Podman Documentation](https://docs.podman.io/)
- [Docker Documentation](https://docs.docker.com/)
- [Container Security Best Practices](https://docs.docker.com/develop/security-best-practices/) 