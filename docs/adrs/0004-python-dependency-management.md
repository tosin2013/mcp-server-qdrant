# ADR 0004: Python Dependency Management Strategy

## Status

Accepted

## Context

We need a robust strategy for managing Python dependencies that works consistently across:
1. Local development environments (macOS with Python 3.11 in virtualenv)
2. Container builds (Docker and Podman with Python 3.11)
3. CI/CD pipelines

We've encountered several issues with dependency management, particularly during container builds. Based on research and best practices, we need to establish a clear approach that balances:
- Reproducibility
- Build performance
- Development experience
- Security considerations

## Decision

We will implement a multi-layered dependency management strategy using modern Python tooling:

### 1. Local Development (macOS)

- Use Python 3.11 with virtualenv for local development
- Use `hatch` as our primary build system and dependency manager
  - Rationale: Hatch provides modern packaging features and aligns with PEP 517/PEP 621 standards
  - Supports both development and production dependencies
  - Integrates well with `pyproject.toml`

Local setup process:
```bash
# Create Python 3.11 virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install hatch in the virtual environment
pip install hatch

# Install project in development mode
hatch env create
```

### 2. Container Builds

- Use Python 3.11 for consistency with local development
- Implement multi-stage builds to optimize caching and reduce image size
- Use `pip wheel` in the build stage to create reproducible wheel packages
- Separate build-time and runtime dependencies
- Cache pip packages appropriately

Structure:
```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY pyproject.toml README.md VERSION ./

# Install and cache build dependencies first
RUN pip install --no-cache-dir hatchling

# Copy source and build wheel
COPY src/ ./src/
RUN pip wheel --no-deps -w dist .

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/dist/*.whl .
RUN pip install --no-cache-dir *.whl
```

### 3. Dependency Specification

Use `pyproject.toml` as the single source of truth for dependencies:

```toml
[project]
name = "mcp-server-qdrant"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]>=1.3.0",
    "fastembed>=0.6.0",
    "qdrant-client>=1.12.0",
    "pydantic>=2.10.6",
]

[project.optional-dependencies]
dev = [
    "pre-commit>=4.1.0",
    "pyright>=1.1.389",
    "pytest>=8.3.3",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.8.0"
]

[tool.hatch.envs.default]
python = "3.11"
```

### 4. Version Management

- Use semantic versioning for all dependencies
- Pin exact versions in container builds for reproducibility
- Allow flexible versions in development for easier updates
- Generate and maintain `requirements.txt` for container builds

## Consequences

### Positive

1. Improved build reproducibility through:
   - Explicit dependency specifications
   - Wheel-based installations
   - Multi-stage builds
   - Consistent Python version (3.11) across all environments

2. Better development experience:
   - Single source of truth in `pyproject.toml`
   - Modern tooling with `hatch`
   - Clear separation of dev and production dependencies
   - Isolated local development environment

3. Optimized container builds:
   - Efficient layer caching
   - Smaller final images
   - Faster rebuilds when dependencies change

### Negative

1. Learning curve for developers new to `hatch` and virtualenv
2. Need to maintain both `pyproject.toml` and container build files
3. Initial setup complexity for multi-stage builds

### Mitigations

1. Provide clear documentation and examples for common tasks
2. Create helper scripts for generating container-specific requirement files
3. Implement CI checks to ensure dependency consistency

## Implementation Plan

1. Update local development setup:
   ```bash
   # Create and activate virtual environment
   python3.11 -m venv .venv
   source .venv/bin/activate
   
   # Install hatch
   pip install hatch
   
   # Create development environment
   hatch env create
   ```

2. Update container builds:
   ```bash
   # Generate requirements.txt for containers
   source .venv/bin/activate
   ./scripts/manage_deps.sh update
   
   # Build container
   make build
   ```

3. Add CI checks:
   - Verify `pyproject.toml` and `requirements.txt` consistency
   - Test builds in both Docker and Podman
   - Validate dependency security with safety checks

## References

1. [Python Packaging User Guide - Managing Dependencies](https://packaging.python.org/tutorials/managing-dependencies/)
2. [Docker Python Module Management Best Practices](https://stackoverflow.com/questions/53812532/advice-for-how-to-manage-python-modules-in-docker)
3. [Hatch Documentation](https://hatch.pypa.io/latest/) 