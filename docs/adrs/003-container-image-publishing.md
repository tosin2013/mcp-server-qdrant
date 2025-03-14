# ADR-003: Container Image Publishing Strategy

## Status
Proposed

## Context
We need to provide officially supported container images for the MCP server to simplify deployment and ensure consistency. Publishing to quay.io allows users to easily pull pre-built images rather than building locally.

### Current Situation
- Users currently need to build images locally
- No official container image repository
- Need for consistent versioning and tagging strategy
- Support needed for both Docker and Podman users

## Decision

### Image Repository
We will use Quay.io as our container registry:
- Repository: `quay.io/takinosh/mcp-server-qdrant`
- Support for multiple architectures (amd64/arm64)
- Automated security scanning
- Public access for pulling images

### Image Tags Strategy
1. **Version Tags**
   - Release versions: `vX.Y.Z` (e.g., `v0.7.1`)
   - Latest release: `latest`
   - Development: `edge`

2. **Architecture-specific Tags**
   - `vX.Y.Z-amd64`
   - `vX.Y.Z-arm64`

### Build and Publishing Workflow

#### Local Development (Makefile)
```makefile
# Variables
IMAGE_NAME := quay.io/takinosh/mcp-server-qdrant
VERSION := $(shell cat VERSION || echo "0.0.0")
PLATFORMS := linux/amd64,linux/arm64

# Docker targets
.PHONY: docker-build docker-push docker-test

docker-build:
	DOCKER_BUILDKIT=1 docker build \
		--platform $(PLATFORMS) \
		--tag $(IMAGE_NAME):latest \
		--tag $(IMAGE_NAME):v$(VERSION) \
		--file Dockerfile .

docker-push:
	docker push $(IMAGE_NAME):latest
	docker push $(IMAGE_NAME):v$(VERSION)

docker-test:
	docker compose -f docker-compose.test.yml up --exit-code-from tests

# Podman targets
.PHONY: podman-build podman-push podman-test

podman-build:
	podman build \
		--platform $(PLATFORMS) \
		--tag $(IMAGE_NAME):latest \
		--tag $(IMAGE_NAME):v$(VERSION) \
		--file Containerfile .

podman-push:
	podman push $(IMAGE_NAME):latest
	podman push $(IMAGE_NAME):v$(VERSION)

podman-test:
	podman-compose -f podman-compose.test.yml up --exit-code-from tests

# Common targets
.PHONY: build push test

build: docker-build
push: docker-push
test: docker-test

# Default to Docker, but allow override with CONTAINER_RUNTIME
ifeq ($(CONTAINER_RUNTIME),podman)
build: podman-build
push: podman-push
test: podman-test
endif
```

### CI/CD Integration
1. **GitHub Actions Workflow**
   ```yaml
   name: Build and Push Container Images

   on:
     push:
       tags:
         - 'v*'
     workflow_dispatch:

   jobs:
     build-and-push:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         
         - name: Set up QEMU
           uses: docker/setup-qemu-action@v3
           
         - name: Set up Docker Buildx
           uses: docker/setup-buildx-action@v3
           
         - name: Login to Quay.io
           uses: docker/login-action@v3
           with:
             registry: quay.io
             username: ${{ secrets.QUAY_USERNAME }}
             password: ${{ secrets.QUAY_PASSWORD }}
             
         - name: Build and push
           uses: docker/build-push-action@v5
           with:
             context: .
             platforms: linux/amd64,linux/arm64
             push: true
             tags: |
               quay.io/takinosh/mcp-server-qdrant:latest
               quay.io/takinosh/mcp-server-qdrant:${{ github.ref_name }}
   ```

### Security Considerations
1. **Image Signing**
   - Use cosign for signing container images
   - Verify signatures during deployment

2. **Vulnerability Scanning**
   - Leverage Quay.io's built-in security scanning
   - Regular base image updates
   - CVE monitoring and fixes

## Consequences

### Positive
- Easy access to pre-built images
- Consistent versioning across deployments
- Automated security scanning
- Multi-architecture support
- Simplified deployment process

### Negative
- Need to maintain CI/CD pipeline
- Storage costs for container registry
- Additional security considerations
- Need to manage access credentials

## Implementation Plan

1. **Phase 1: Local Build Infrastructure**
   - Create Makefile for local builds
   - Test multi-architecture builds
   - Document build process

2. **Phase 2: Registry Setup**
   - Set up Quay.io repository
   - Configure access controls
   - Set up automated scanning

3. **Phase 3: CI/CD Pipeline**
   - Implement GitHub Actions workflow
   - Set up secrets for registry access
   - Test automated builds

4. **Phase 4: Documentation**
   - Update README with new image information
   - Add deployment examples
   - Document version policy

## References
- [Quay.io Documentation](https://docs.quay.io/)
- [Container Image Signing](https://docs.sigstore.dev/cosign/overview/)
- [GitHub Actions Docker Build](https://docs.github.com/en/actions/publishing-packages/publishing-docker-images)
- [OCI Image Specification](https://github.com/opencontainers/image-spec) 