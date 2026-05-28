#!/bin/bash
# Start both backend (Django) and frontend (Vite) in development mode
# Usage: ./start.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_ROOT"

# Start backend
echo "Starting backend (Django) with uv..."
cd "$PROJECT_ROOT/backend"
uv run python manage.py runserver &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Start frontend
echo "Starting frontend (Vite)..."
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo "Both servers started. Press Ctrl+C to stop."

# Wait for background processes
wait
