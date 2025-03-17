# Variables
IMAGE_NAME := quay.io/takinosh/mcp-server-qdrant
VERSION := $(shell cat VERSION || echo "0.0.0")
PLATFORMS := linux/amd64,linux/arm64
BUILD_DATE := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF := $(shell git rev-parse --short HEAD)

# Build arguments
BUILD_ARGS := \
	--build-arg VERSION=$(VERSION) \
	--build-arg BUILD_DATE=$(BUILD_DATE) \
	--build-arg VCS_REF=$(VCS_REF)

# Docker targets
.PHONY: docker-build docker-push docker-test docker-run docker-debug

docker-debug:
	@echo "Current directory contents:"
	@ls -la
	@echo "\nChecking README.md:"
	@ls -la README.md || echo "README.md not found"
	@echo "\nChecking VERSION:"
	@ls -la VERSION || echo "VERSION not found"
	@echo "\nChecking pyproject.toml:"
	@ls -la pyproject.toml || echo "pyproject.toml not found"
	@echo "\nChecking src directory:"
	@ls -la src/ || echo "src/ not found"

docker-build: docker-debug
	@echo "\nBuilding Docker image..."
	DOCKER_BUILDKIT=1 docker build \
		$(BUILD_ARGS) \
		--progress=plain \
		--no-cache \
		--tag $(IMAGE_NAME):latest \
		--tag $(IMAGE_NAME):v$(VERSION) \
		--file Containerfile .

docker-push:
	docker push $(IMAGE_NAME):latest
	docker push $(IMAGE_NAME):v$(VERSION)

docker-test:
	docker compose -f docker-compose.test.yml up --exit-code-from tests

docker-run:
	docker run -it --rm \
		-p 8000:8000 \
		-e QDRANT_URL \
		-e QDRANT_API_KEY \
		-e COLLECTION_NAME \
		$(IMAGE_NAME):latest

# Podman targets
.PHONY: podman-build podman-push podman-test podman-run

podman-build:
	podman build \
		$(BUILD_ARGS) \
		--platform $(PLATFORMS) \
		--tag $(IMAGE_NAME):latest \
		--tag $(IMAGE_NAME):v$(VERSION) \
		--file Containerfile .

podman-push:
	podman push $(IMAGE_NAME):latest
	podman push $(IMAGE_NAME):v$(VERSION)

podman-test:
	podman-compose -f podman-compose.test.yml up --exit-code-from tests

podman-run:
	podman run -it --rm \
		-p 8000:8000 \
		-e QDRANT_URL \
		-e QDRANT_API_KEY \
		-e COLLECTION_NAME \
		$(IMAGE_NAME):latest

# Common targets
.PHONY: build push test run debug

build: docker-build
push: docker-push
test: docker-test
run: docker-run
debug: docker-debug

# Default to Docker, but allow override with CONTAINER_RUNTIME
ifeq ($(CONTAINER_RUNTIME),podman)
build: podman-build
push: podman-push
test: podman-test
run: podman-run
endif

# Helper targets
.PHONY: version clean login

version:
	@echo $(VERSION)

clean:
	docker system prune -f || podman system prune -f

login:
ifeq ($(CONTAINER_RUNTIME),podman)
	podman login quay.io
else
	docker login quay.io
endif 