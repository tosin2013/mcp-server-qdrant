#!/bin/bash

# Function to check container logs
check_logs() {
    local container_name=$1
    echo "=== Checking logs for $container_name ==="
    docker logs $container_name
}

# Function to check container health
check_health() {
    local container_name=$1
    echo "=== Checking health status for $container_name ==="
    docker inspect --format='{{json .State.Health}}' $container_name | jq .
}

# Function to check container status
check_status() {
    local container_name=$1
    echo "=== Checking container status for $container_name ==="
    docker inspect --format='{{json .State.Status}}' $container_name
    echo "=== Checking container network settings ==="
    docker inspect --format='{{json .NetworkSettings.Networks}}' $container_name | jq .
}

# Function to safely execute command in container
safe_exec() {
    local container_name=$1
    local cmd=$2
    local desc=$3
    echo "=== $desc ==="
    if ! docker exec $container_name which ${cmd%% *} >/dev/null 2>&1; then
        echo "Warning: Command '${cmd%% *}' not found in container"
        return 1
    fi
    docker exec $container_name $cmd || true
}

# Function to execute health checks inside container
exec_health_checks() {
    local container_name=$1
    echo "=== Executing health checks in $container_name ==="
    
    # Check if curl exists and use it
    if docker exec $container_name which curl >/dev/null 2>&1; then
        echo "Testing with curl:"
        docker exec $container_name curl -v http://localhost:6333/collections || true
    fi
    
    # Check if wget exists and use it
    if docker exec $container_name which wget >/dev/null 2>&1; then
        echo "Testing with wget:"
        docker exec $container_name wget --no-verbose --tries=1 --spider http://localhost:6333/collections || true
    fi

    # Check processes
    safe_exec "$container_name" "ps aux" "Checking processes"
    
    # Check ports - try different commands
    safe_exec "$container_name" "netstat -tulpn" "Checking listening ports (netstat)" || \
    safe_exec "$container_name" "ss -tulpn" "Checking listening ports (ss)" || \
    safe_exec "$container_name" "lsof -i -P -n" "Checking listening ports (lsof)"
    
    # Check Qdrant specific info
    echo "=== Checking Qdrant API info ==="
    if docker exec $container_name which curl >/dev/null 2>&1; then
        docker exec $container_name curl -s http://localhost:6333/api/v1/collections || true
    fi
}

# Main script
container_name=$1
if [ -z "$container_name" ]; then
    echo "Usage: $0 <container_name>"
    exit 1
fi

# Run all checks
check_logs $container_name
check_status $container_name
check_health $container_name
exec_health_checks $container_name

# Try to start the container if it's not running
container_status=$(docker inspect --format='{{.State.Status}}' $container_name 2>/dev/null)
if [ "$container_status" != "running" ]; then
    echo "Container is not running. Attempting to start..."
    docker start $container_name
    sleep 5  # Give it some time to start
    check_logs $container_name
fi 