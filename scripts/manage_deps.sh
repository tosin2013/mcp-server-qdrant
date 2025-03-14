#!/bin/bash
set -euo pipefail

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to ensure Python 3.11 is available
ensure_python() {
    if ! command_exists python3.11; then
        echo "Error: Python 3.11 is required but not found"
        echo "Please install Python 3.11 and try again"
        exit 1
    fi
}

# Function to ensure virtual environment
ensure_venv() {
    if [ ! -d ".venv" ]; then
        echo "Creating Python 3.11 virtual environment..."
        python3.11 -m venv .venv
    fi
    
    # Activate virtual environment if not already active
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        echo "Activating virtual environment..."
        source .venv/bin/activate
    fi
}

# Function to ensure pip is available
ensure_pip() {
    ensure_venv
    echo "Upgrading pip..."
    python3 -m pip install --upgrade pip
}

# Function to install dependencies
install_deps() {
    echo "Installing development dependencies..."
    ensure_python
    ensure_pip
    
    if command_exists hatch; then
        hatch env create
    else
        echo "Hatch not found. Installing..."
        python3 -m pip install hatch
        hatch env create
    fi
}

# Function to update dependencies
update_deps() {
    echo "Updating dependencies..."
    ensure_pip
    
    if ! command_exists pip-tools; then
        python3 -m pip install pip-tools
    fi
    
    # Update requirements.txt from pyproject.toml
    python3 -m piptools compile --upgrade --no-emit-index-url pyproject.toml -o requirements.txt
    
    # Update dev requirements
    python3 -m piptools compile --upgrade --no-emit-index-url --extra dev pyproject.toml -o dev-requirements.txt
    
    echo "Dependencies updated. New versions written to requirements.txt and dev-requirements.txt"
}

# Function to sync current environment with requirements
sync_deps() {
    echo "Syncing dependencies..."
    ensure_pip
    
    if ! command_exists pip-tools; then
        python3 -m pip install pip-tools
    fi
    
    if [ -f "dev-requirements.txt" ]; then
        python3 -m piptools sync dev-requirements.txt
    else
        python3 -m piptools sync requirements.txt
    fi
}

# Function to check dependency security
check_deps() {
    echo "Checking dependencies for security vulnerabilities..."
    ensure_pip
    
    if ! command_exists safety; then
        python3 -m pip install safety
    fi
    
    safety check -r requirements.txt
    if [ -f "dev-requirements.txt" ]; then
        safety check -r dev-requirements.txt
    fi
}

# Function to clean up
clean_deps() {
    echo "Cleaning up dependency files and virtual environment..."
    rm -f requirements.txt dev-requirements.txt
    rm -rf .venv
    echo "Cleanup complete. Run 'install' to set up a fresh environment."
}

# Help message
show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install    Create virtualenv and install development dependencies using hatch"
    echo "  update     Update and compile requirements files"
    echo "  sync       Sync current environment with requirements"
    echo "  check      Check dependencies for security vulnerabilities"
    echo "  clean      Remove virtual environment and generated files"
    echo "  help       Show this help message"
    echo ""
    echo "Note: This script requires Python 3.11"
}

# Main script
case "${1:-help}" in
    "install")
        install_deps
        ;;
    "update")
        update_deps
        ;;
    "sync")
        sync_deps
        ;;
    "check")
        check_deps
        ;;
    "clean")
        clean_deps
        ;;
    "help"|*)
        show_help
        ;;
esac 