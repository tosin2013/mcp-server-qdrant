#!/bin/bash
set -e

# Build the test image
docker build -t mcp-server-qdrant-test -f Dockerfile.test .

# Run the tests
docker run --rm \
    -v "$(pwd):/app" \
    mcp-server-qdrant-test \
    pytest tests/test_analysis/test_codebase_analyzer.py -v 