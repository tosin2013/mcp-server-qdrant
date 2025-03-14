#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Function to check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 could not be found. Please install it first."
        exit 1
    fi
}

# Check required commands
check_command python3.11
check_command docker
check_command curl

# Test local Python environment
test_local_environment() {
    log_info "Testing local Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment..."
        python3.11 -m venv .venv
    fi
    
    # Activate virtual environment
    log_info "Activating virtual environment..."
    source .venv/bin/activate
    
    # Upgrade pip first
    log_info "Upgrading pip..."
    python -m pip install --upgrade pip
    
    # Install development dependencies
    log_info "Installing development dependencies..."
    python -m pip install hatch
    
    # Create development environment with all dependencies
    log_info "Creating development environment..."
    if ! hatch env create; then
        log_error "Failed to create hatch environment"
        exit 1
    fi
    
    # Install the project in development mode
    log_info "Installing project in development mode..."
    if ! hatch build; then
        log_error "Failed to build project"
        exit 1
    fi
    python -m pip install -e .
    
    # Show installed packages for debugging
    log_info "Installed packages:"
    pip list
    
    # Run tests with verbose output
    log_info "Running tests..."
    if ! python -m pytest -v; then
        log_error "Tests failed"
        exit 1
    fi
    
    log_info "Local environment tests passed ✅"
}

# Test Docker build
test_docker_build() {
    log_info "Testing Docker build..."
    
    # Build the Docker image with build args
    log_info "Building Docker image..."
    docker build \
        --build-arg VERSION=$(cat VERSION 2>/dev/null || echo "dev") \
        --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
        --build-arg VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
        -t mcp-server-qdrant:test .
    
    # Run the container
    log_info "Starting container..."
    docker run -d --name mcp-server-test -p 8000:8000 mcp-server-qdrant:test
    
    # Wait for container to be ready and show logs
    log_info "Waiting for container to be ready..."
    sleep 5
    docker logs mcp-server-test
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    
    if [ "$response" == "200" ]; then
        log_info "Health check passed ✅"
    else
        log_error "Health check failed ❌"
        docker logs mcp-server-test
        cleanup
        exit 1
    fi
    
    cleanup
    log_info "Docker tests passed ✅"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    docker stop mcp-server-test 2>/dev/null || true
    docker rm mcp-server-test 2>/dev/null || true
}

# Main execution
main() {
    log_info "Starting end-to-end tests..."
    
    # Run local environment tests
    test_local_environment
    
    # Run Docker tests
    test_docker_build
    
    log_info "All tests passed successfully! 🎉"
}

# Trap cleanup on script exit
trap cleanup EXIT

# Run main function
main 