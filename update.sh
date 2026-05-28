#!/bin/bash
# TimeTracker Update Script
# This script updates dependencies and optionally starts the development servers
# Usage: ./update.sh [--start] [--backend-only] [--frontend-only]

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHOULD_START=false
BACKEND_ONLY=false
FRONTEND_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --start) SHOULD_START=true; shift ;;
        --backend-only) BACKEND_ONLY=true; shift ;;
        --frontend-only) FRONTEND_ONLY=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# If only one is specified, set the other to false
if [ "$BACKEND_ONLY" = true ] || [ "$FRONTEND_ONLY" = true ]; then
    if [ "$BACKEND_ONLY" = true ]; then
        FRONTEND_ONLY=false
    else
        BACKEND_ONLY=false
    fi
else
    BACKEND_ONLY=false
    FRONTEND_ONLY=false
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_section() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Main update process
print_section "TimeTracker Update"

# Check if uv is installed, install if needed
if ! command -v uv &> /dev/null; then
    echo "Installing uv (fast Python package manager)..."
    if command -v pip &> /dev/null; then
        pip install uv > /dev/null 2>&1
        if ! command -v uv &> /dev/null; then
            echo -e "${RED}✗${NC} Failed to install uv via pip."
            echo "Please install uv manually from https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        fi
    else
        echo -e "${RED}✗${NC} uv and pip not found."
        echo "Please install uv from https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi

# Update Backend
if [ "$FRONTEND_ONLY" = false ]; then
    print_section "Updating Backend Dependencies"

    cd "$PROJECT_ROOT/backend" || exit 1

    # Update dependencies with uv
    echo "Updating Python dependencies..."
    uv sync --all-extras > /dev/null 2>&1
    print_status "Python dependencies updated"

    # Run any pending migrations
    echo "Running database migrations..."
    uv run python manage.py migrate > /dev/null 2>&1
    print_status "Database migrations completed"

    # Run tests (optional, comment out if you want to skip)
    echo "Running backend tests..."
    if uv run pytest > /dev/null 2>&1; then
        print_status "All backend tests passed"
    else
        echo -e "${YELLOW}⚠${NC} Some backend tests failed (see output above)"
    fi
fi

# Update Frontend
if [ "$BACKEND_ONLY" = false ]; then
    print_section "Updating Frontend Dependencies"

    cd "$PROJECT_ROOT/frontend" || exit 1

    # Update npm packages
    echo "Updating npm packages..."
    npm install --legacy-peer-deps > /dev/null 2>&1
    print_status "npm packages updated"

    # Optionally run tests
    echo "Running frontend tests..."
    if npm test 2>/dev/null; then
        print_status "All frontend tests passed"
    else
        echo -e "${YELLOW}⚠${NC} Some frontend tests may have failed"
    fi
fi

# Completion message
print_section "Update Complete! 🎉"

if [ "$SHOULD_START" = true ]; then
    echo "Starting development servers..."
    echo ""

    if [ "$FRONTEND_ONLY" = false ]; then
        print_info "Starting backend on http://localhost:8000"
        cd "$PROJECT_ROOT/backend"
        uv run python manage.py runserver &
        BACKEND_PID=$!
        echo "Backend PID: $BACKEND_PID"
        sleep 2
    fi

    if [ "$BACKEND_ONLY" = false ]; then
        print_info "Starting frontend on http://localhost:5173"
        cd "$PROJECT_ROOT/frontend"
        npm run dev &
        FRONTEND_PID=$!
        echo "Frontend PID: $FRONTEND_PID"
    fi

    echo ""
    print_info "Both servers are running. Press Ctrl+C to stop."
    echo ""
    wait
else
    echo "Next steps:"
    echo ""
    echo "  Start the backend:"
    echo "    cd $PROJECT_ROOT/backend"
    echo "    uv run python manage.py runserver"
    echo "  Start the frontend (in another terminal):"
    echo "    cd $PROJECT_ROOT/frontend"
    echo "    npm run dev"
    echo ""
    echo "  Or run both with:"
    echo "    ./update.sh --start"
    echo ""
fi
