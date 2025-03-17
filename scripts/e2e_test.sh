#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Start time of the test run
START_TIME=$(date +%s)

# Test results
TOTAL_TESTS=0
FAILED_TESTS=0
PASSED_TESTS=0
SKIPPED_TESTS=0
declare -a FAILURES

# Docker compose project name
export COMPOSE_PROJECT_NAME="mcp-test"

# Configuration
MCP_SERVER_PORT=8000
QDRANT_PORT=6333
TIMEOUT=120  # Timeout in seconds
LOAD_TEST_REQUESTS=100
MIN_MEMORY=100  # Minimum memory in MB
MAX_CPU_PERCENT=80

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Function to record test result
record_test_result() {
    local test_name=$1
    local status=$2  # "pass", "fail", or "skip"
    local error_message=$3
    local details=$4
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    case $status in
        "pass")
            PASSED_TESTS=$((PASSED_TESTS + 1))
            log_info "✅ Test passed: $test_name"
            ;;
        "fail")
            FAILED_TESTS=$((FAILED_TESTS + 1))
            FAILURES+=("{\"test\": \"$test_name\", \"error\": \"$error_message\", \"details\": \"$details\"}")
            log_error "❌ Test failed: $test_name - $error_message"
            ;;
        "skip")
            SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
            log_warn "⏭️  Test skipped: $test_name - $error_message"
            ;;
    esac
}

# Function to check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 could not be found. Please install it first."
        exit 1
    fi
}

# Function to wait for Qdrant
wait_for_qdrant() {
    local timeout=$1
    local start_time=$(date +%s)
    
    log_info "Waiting for Qdrant to be ready..."
    while true; do
        # Try to get Qdrant collections list as health check
        if curl -s "http://localhost:${QDRANT_PORT}/collections" | grep -q "result"; then
            log_info "Qdrant is ready"
            return 0
        fi
        
        if [ $(($(date +%s) - start_time)) -gt $timeout ]; then
            log_error "Qdrant failed to become ready within $timeout seconds"
            docker-compose -p ${COMPOSE_PROJECT_NAME} logs qdrant
            return 1
        fi
        
        log_debug "Waiting for Qdrant to initialize..."
        sleep 5
    done
}

# Function to wait for service health
wait_for_service() {
    local service=$1
    local port=$2
    local timeout=$3
    local start_time=$(date +%s)
    
    log_info "Waiting for $service to be healthy..."
    while true; do
        local current_time=$(($(date +%s) - start_time))
        
        # Different health check logic for different services
        case $service in
            "qdrant")
                if curl -s "http://localhost:${port}/collections" | grep -q "result"; then
                    log_info "Qdrant is healthy"
                    return 0
                fi
                ;;
            *)
                if curl -s "http://localhost:${port}/health" | grep -q "healthy"; then
                    log_info "$service is healthy"
                    return 0
                fi
                ;;
        esac
        
        if [ $current_time -gt $timeout ]; then
            log_error "$service failed to become healthy within $timeout seconds"
            docker-compose -p ${COMPOSE_PROJECT_NAME} logs $service
            return 1
        fi
        
        if [ $((current_time % 10)) -eq 0 ]; then
            log_debug "Still waiting for $service... (${current_time}s)"
            docker-compose -p ${COMPOSE_PROJECT_NAME} ps $service
        fi
        
        sleep 2
    done
}

# Function to check container resource usage
check_container_resources() {
    local container=$1
    
    # Check memory usage
    local memory_usage=$(docker stats --no-stream --format "{{.MemUsage}}" $container | awk '{print $1}' | sed 's/MiB//')
    if (( $(echo "$memory_usage < $MIN_MEMORY" | bc -l) )); then
        return 1
    fi
    
    # Check CPU usage
    local cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" $container | sed 's/%//')
    if (( $(echo "$cpu_usage > $MAX_CPU_PERCENT" | bc -l) )); then
        return 1
    fi
    
    return 0
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test environment..."
    
    # Stop and remove containers
    docker-compose -p ${COMPOSE_PROJECT_NAME} down -v --remove-orphans
    
    # Remove any leftover test data
    rm -rf ./test_data
    
    # Verify cleanup
    if docker ps -a | grep -q "${COMPOSE_PROJECT_NAME}"; then
        log_error "Failed to remove all test containers"
        return 1
    fi
    
    log_info "Cleanup completed successfully"
}

# Test container health and metrics
test_container_health() {
    local test_name="container_health"
    log_info "Testing container health and metrics..."
    
    # Check MCP server container
    if ! check_container_resources "${COMPOSE_PROJECT_NAME}-mcp-server-1"; then
        record_test_result "$test_name" "fail" "Resource usage outside acceptable range" "$(docker stats --no-stream ${COMPOSE_PROJECT_NAME}-mcp-server-1)"
        return 1
    fi
    
    # Check Qdrant container
    if ! check_container_resources "${COMPOSE_PROJECT_NAME}-qdrant-1"; then
        record_test_result "$test_name" "fail" "Resource usage outside acceptable range" "$(docker stats --no-stream ${COMPOSE_PROJECT_NAME}-qdrant-1)"
        return 1
    fi
    
    record_test_result "$test_name" "pass"
}

# Test data persistence
test_data_persistence() {
    local test_name="data_persistence"
    log_info "Testing data persistence..."
    
    # Store test data
    local test_data='{"content": "test persistence", "metadata": {"test": true}}'
    if ! curl -s -X POST "http://localhost:${MCP_SERVER_PORT}/store" \
         -H "Content-Type: application/json" \
         -d "$test_data" | grep -q "success"; then
        record_test_result "$test_name" "fail" "Failed to store test data"
        return 1
    fi
    
    # Restart containers
    docker-compose -p ${COMPOSE_PROJECT_NAME} restart
    sleep 10
    
    # Verify data persists
    if ! curl -s -X POST "http://localhost:${MCP_SERVER_PORT}/search" \
         -H "Content-Type: application/json" \
         -d '{"query": "test persistence", "limit": 1}' | grep -q "test persistence"; then
        record_test_result "$test_name" "fail" "Data did not persist after restart"
        return 1
    fi
    
    record_test_result "$test_name" "pass"
}

# Test Qdrant integration
test_qdrant_integration() {
    local test_name="qdrant_integration"
    log_info "Testing Qdrant integration..."
    
    # Start services
    if ! docker-compose -p ${COMPOSE_PROJECT_NAME} up -d; then
        record_test_result "$test_name" "fail" "Failed to start services" "$(docker-compose -p ${COMPOSE_PROJECT_NAME} logs)"
        return 1
    fi
    
    # Wait for Qdrant first
    if ! wait_for_service "qdrant" $QDRANT_PORT $TIMEOUT; then
        record_test_result "$test_name" "fail" "Qdrant failed to start" "$(docker-compose -p ${COMPOSE_PROJECT_NAME} logs qdrant)"
        return 1
    fi
    
    # Then wait for MCP server
    if ! wait_for_service "mcp-server" $MCP_SERVER_PORT $TIMEOUT; then
        record_test_result "$test_name" "fail" "MCP server failed to start" "$(docker-compose -p ${COMPOSE_PROJECT_NAME} logs mcp-server)"
        return 1
    fi
    
    # Run integration tests
    if ! python -m pytest tests/integration/test_qdrant_integration.py -v; then
        record_test_result "$test_name" "fail" "Integration tests failed" "$(docker-compose -p ${COMPOSE_PROJECT_NAME} logs)"
        return 1
    fi
    
    record_test_result "$test_name" "pass"
}

# Load test
test_load() {
    local test_name="load_test"
    log_info "Running load tests..."
    
    local success_count=0
    local start_time=$(date +%s)
    
    for i in $(seq 1 $LOAD_TEST_REQUESTS); do
        if curl -s -X POST "http://localhost:${MCP_SERVER_PORT}/store" \
            -H "Content-Type: application/json" \
            -d "{\"content\": \"load test $i\", \"metadata\": {\"test\": true}}" | grep -q "success"; then
            success_count=$((success_count + 1))
        fi
    done
    
    local duration=$(($(date +%s) - start_time))
    local success_rate=$((success_count * 100 / LOAD_TEST_REQUESTS))
    
    if [ $success_rate -lt 95 ]; then
        record_test_result "$test_name" "fail" "Success rate below 95%" "Success rate: ${success_rate}%, Duration: ${duration}s"
        return 1
    fi
    
    record_test_result "$test_name" "pass" "" "Success rate: ${success_rate}%, Duration: ${duration}s"
}

# Test codebase analyzer
test_codebase_analyzer() {
    local test_name="codebase_analyzer"
    log_info "Testing codebase analyzer..."
    
    # Build test image
    if ! docker build -t mcp-server-qdrant-test -f Dockerfile.test .; then
        record_test_result "$test_name" "fail" "Failed to build test image" "$(docker build -t mcp-server-qdrant-test -f Dockerfile.test . 2>&1)"
        return 1
    fi
    
    # Run analyzer tests
    if ! docker run --rm \
        -v "$(pwd):/app" \
        mcp-server-qdrant-test \
        pytest tests/test_analysis/test_codebase_analyzer.py -v; then
        record_test_result "$test_name" "fail" "Analyzer tests failed" "$(docker logs mcp-server-qdrant-test 2>&1)"
        return 1
    fi
    
    record_test_result "$test_name" "pass"
}

# Main test execution
main() {
    # Check required commands
    check_command "docker"
    check_command "docker-compose"
    check_command "curl"
    check_command "bc"
    
    # Clean up any previous test runs
    cleanup
    
    # Run tests
    test_qdrant_integration
    test_container_health
    test_data_persistence
    test_load
    test_codebase_analyzer
    
    # Calculate test duration
    local duration=$(($(date +%s) - START_TIME))
    
    # Print test summary
    echo
    echo "Test Summary:"
    echo "============="
    echo "Total Tests:   $TOTAL_TESTS"
    echo "Passed Tests:  $PASSED_TESTS"
    echo "Failed Tests:  $FAILED_TESTS"
    echo "Skipped Tests: $SKIPPED_TESTS"
    echo "Duration:      ${duration}s"
    echo
    
    # Print failures if any
    if [ ${#FAILURES[@]} -gt 0 ]; then
        echo "Test Failures:"
        echo "=============="
        for failure in "${FAILURES[@]}"; do
            echo "$failure" | jq '.'
        done
        echo
    fi
    
    # Final cleanup
    cleanup
    
    # Exit with failure if any tests failed
    [ $FAILED_TESTS -eq 0 ]
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi 