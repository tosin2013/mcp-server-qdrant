#!/bin/bash
set -e

# Function to cleanup
cleanup() {
    echo "[INFO] Cleaning up test environment..."
    docker-compose -p mcp-test -f docker-compose.test.yml down -v
    echo "[INFO] Cleanup completed"
}

# Function to wait for container health
wait_for_health() {
    local container_name=$1
    local max_attempts=30
    local attempt=1

    echo "[INFO] Waiting for $container_name to be healthy..."
    while [ $attempt -le $max_attempts ]; do
        health_status=$(docker inspect --format='{{.State.Health.Status}}' $container_name 2>/dev/null || echo "not_found")
        
        case $health_status in
            "healthy")
                echo "[INFO] Container $container_name is healthy"
                return 0
                ;;
            "not_found")
                echo "[ERROR] Container $container_name not found"
                return 1
                ;;
            *)
                echo "[INFO] Container status: $health_status (attempt $attempt/$max_attempts)"
                ;;
        esac

        attempt=$((attempt + 1))
        sleep 2
    done

    echo "[ERROR] Container $container_name failed to become healthy"
    ./scripts/debug_container.sh $container_name
    return 1
}

# Cleanup on script exit
trap cleanup EXIT

# Ensure clean state
cleanup

# Start the services
echo "[INFO] Starting services..."
docker-compose -p mcp-test -f docker-compose.test.yml up -d qdrant

# Wait for Qdrant to be healthy
if ! wait_for_health "mcp-test-qdrant-1"; then
    echo "[ERROR] Qdrant failed to start properly"
    exit 1
fi

# Run the tests
echo "[INFO] Running tests..."
docker-compose -p mcp-test -f docker-compose.test.yml run --rm tests

# Capture test exit code
test_exit_code=$?

# Exit with test status
exit $test_exit_code 