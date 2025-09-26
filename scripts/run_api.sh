#!/bin/bash

# Noor AI Agent - API Server Startup Script
# This script starts the FastAPI server for the Noor AI Agent

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-8001}
WORKERS=${WORKERS:-1}
RELOAD=${RELOAD:-"true"}
LOG_LEVEL=${LOG_LEVEL:-"info"}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --host HOST        Host to bind to (default: 0.0.0.0)"
    echo "  -p, --port PORT        Port to bind to (default: 8000)"
    echo "  -w, --workers WORKERS  Number of worker processes (default: 1)"
    echo "  -r, --reload           Enable auto-reload for development"
    echo "  -l, --log-level LEVEL  Log level (default: info)"
    echo "  --help                 Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  HOST                   Host to bind to"
    echo "  PORT                   Port to bind to"
    echo "  WORKERS                Number of worker processes"
    echo "  RELOAD                 Enable auto-reload (true/false)"
    echo "  LOG_LEVEL              Log level"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run with defaults"
    echo "  $0 --host 127.0.0.1 --port 9000     # Custom host and port"
    echo "  $0 --reload --workers 4              # Development mode with 4 workers"
    echo "  $0 --log-level debug                 # Debug logging"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -r|--reload)
            RELOAD="true"
            shift
            ;;
        -l|--log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate inputs
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    print_error "Port must be a number between 1 and 65535"
    exit 1
fi

if ! [[ "$WORKERS" =~ ^[0-9]+$ ]] || [ "$WORKERS" -lt 1 ]; then
    print_error "Workers must be a positive number"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed or not in PATH"
    exit 1
fi

# Check if the project structure exists
if [ ! -d "noor_ai_agent" ]; then
    print_error "noor_ai_agent directory not found. Are you in the correct project directory?"
    exit 1
fi

# Check if requirements are installed
print_status "Checking dependencies..."
if ! python3 -c "import fastapi, uvicorn, pydantic" 2>/dev/null; then
    print_warning "Some dependencies might be missing. Installing requirements..."
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
else
    print_success "Dependencies are available"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_warning ".env file not found. Copying from .env.example..."
        cp .env.example .env
        print_warning "Please update .env with your actual configuration values"
    else
        print_warning ".env file not found. You may need to create one with your configuration"
    fi
fi

# Build uvicorn command
UVICORN_CMD="python3 -m uvicorn noor_ai_agent.main:app"

# Add host and port
UVICORN_CMD="$UVICORN_CMD --host $HOST --port $PORT"

# Add workers (only if not in reload mode)
if [ "$RELOAD" = "false" ] && [ "$WORKERS" -gt 1 ]; then
    UVICORN_CMD="$UVICORN_CMD --workers $WORKERS"
fi

# Add reload mode
if [ "$RELOAD" = "true" ]; then
    UVICORN_CMD="$UVICORN_CMD --reload"
    print_warning "Running in development mode with auto-reload enabled"
fi

# Add log level
UVICORN_CMD="$UVICORN_CMD --log-level $LOG_LEVEL"

# Display startup information
print_status "Starting Noor AI Agent API Server..."
print_status "Host: $HOST"
print_status "Port: $PORT"
print_status "Workers: $WORKERS"
print_status "Reload: $RELOAD"
print_status "Log Level: $LOG_LEVEL"
print_status "Command: $UVICORN_CMD"
echo ""

# Start the server
print_success "Server starting... Press Ctrl+C to stop"
echo ""

# Run the command
exec $UVICORN_CMD
