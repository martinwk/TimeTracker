#!/bin/bash
# TimeTracker Installation Script
# This script sets up the complete TimeTracker environment (backend + frontend)
# Usage: ./install.sh

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🚀 Installing TimeTracker..."
echo "Project root: $PROJECT_ROOT"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_section() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Check prerequisites
print_section "Checking Prerequisites"

# Check and install uv if needed
if ! command -v uv &> /dev/null; then
    echo "Installing uv (fast Python package manager)..."
    if command -v pip &> /dev/null; then
        pip install uv > /dev/null 2>&1
        if command -v uv &> /dev/null; then
            print_status "uv installed successfully"
        else
            print_error "Failed to install uv via pip. Please install manually from https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        fi
    else
        print_error "uv and pip not found. Please install uv from https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
else
    print_status "uv: $(uv --version)"
fi

if ! command -v node &> /dev/null; then
    print_error "Node.js not found."
    echo ""
    echo "To install Node.js without admin rights, use the portable version:"
    echo ""
    echo "  1. Download portable Node.js from: https://nodejs.org/"
    echo "     (Look for 'Windows Binary (.zip)' - 64-bit or 32-bit)"
    echo ""
    echo "  2. Extract the ZIP to a folder, e.g.:"
    echo "     C:\Users\$USER\Tools\nodejs"
    echo "     or: C:\nodejs"
    echo ""
    echo "  3. Add to PATH in Git Bash:"
    echo "     export PATH=\"C:/Users/\$USER/Tools/nodejs:\$PATH\""
    echo "     (Use forward slashes in Git Bash, or escape backslashes)"
    echo ""
    echo "  4. Make it permanent by adding to ~/.bashrc (Git Bash style):"
    echo "     echo 'export PATH=\"$HOME/Tools/nodejs:\$PATH\"' >> ~/.bashrc"
    echo "     # then reload for current session: source ~/.bashrc"
    echo ""
    echo "  5. Verify installation:"
    echo "     node --version"
    echo "     npm --version"
    echo ""
    echo "Folders already in PATH:"
    echo "$PATH" | tr ':' '\n' | head -10
    echo ""
    echo "     Create the folder (Git Bash):"
    echo "       mkdir -p /c/Users/\$USER/Tools/nodejs"
    echo "     Or (PowerShell / CMD):"
    echo "       mkdir \"%USERPROFILE%\\\\Tools\\\\nodejs\""
    exit 1
fi
print_status "Node.js: $(node --version)"
print_status "npm: $(npm --version)"

if ! command -v git &> /dev/null; then
    print_error "Git not found. Please install Git."
    exit 1
fi
print_status "Git: $(git --version | cut -d' ' -f3)"

# Setup Backend
print_section "Setting up Backend"

cd "$PROJECT_ROOT/backend" || exit 1

# Install dependencies with uv (includes virtual environment management)
echo "Installing Python dependencies with uv..."
uv sync --all-extras > /dev/null 2>&1
print_status "Python dependencies installed"

# Run migrations
echo "Running database migrations..."
uv run python manage.py migrate > /dev/null 2>&1
print_status "Database migrations completed"

# Setup Frontend
print_section "Setting up Frontend"

cd "$PROJECT_ROOT/frontend" || exit 1

# Install npm dependencies
echo "Installing npm packages..."
npm install --legacy-peer-deps > /dev/null 2>&1
print_status "npm packages installed"

# Success message
print_section "Installation Complete! 🎉"

echo "Next steps:"
echo ""
echo "  1. Start the backend:"
echo "     cd $PROJECT_ROOT/backend"
echo "     uv run python manage.py runserver"
echo ""
echo "  2. In another terminal, start the frontend:"
echo "     cd $PROJECT_ROOT/frontend"
echo "     npm run dev"
echo ""
echo "  3. Open http://localhost:5173 in your browser"
echo ""
echo "  4. Access the admin panel at http://localhost:8000/admin/"
echo ""
echo "Optional: Run tests"
echo "  Backend tests:  cd backend && uv run pytest"
echo "  Frontend tests: cd frontend &&uv run  npm test"
echo ""
