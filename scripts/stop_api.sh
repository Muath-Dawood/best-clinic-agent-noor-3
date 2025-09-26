#!/bin/bash

# Noor AI Agent - Stop Server Script
# This script stops the running Noor AI Agent server

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_status "Stopping Noor AI Agent server..."

# Find and kill uvicorn processes
PIDS=$(pgrep -f "uvicorn.*noor_ai_agent" 2>/dev/null || true)

if [ -z "$PIDS" ]; then
    print_warning "No running Noor AI Agent server found"
    exit 0
fi

print_status "Found running server processes: $PIDS"

# Kill the processes
for PID in $PIDS; do
    print_status "Stopping process $PID..."
    kill -TERM $PID 2>/dev/null || true
done

# Wait a moment for graceful shutdown
sleep 2

# Check if processes are still running
REMAINING_PIDS=$(pgrep -f "uvicorn.*noor_ai_agent" 2>/dev/null || true)

if [ -n "$REMAINING_PIDS" ]; then
    print_warning "Some processes are still running, forcing shutdown..."
    for PID in $REMAINING_PIDS; do
        print_status "Force killing process $PID..."
        kill -KILL $PID 2>/dev/null || true
    done
fi

# Final check
FINAL_PIDS=$(pgrep -f "uvicorn.*noor_ai_agent" 2>/dev/null || true)

if [ -z "$FINAL_PIDS" ]; then
    print_success "Noor AI Agent server stopped successfully"
else
    print_error "Failed to stop some server processes: $FINAL_PIDS"
    exit 1
fi
