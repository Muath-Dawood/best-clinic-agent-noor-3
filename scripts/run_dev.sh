#!/bin/bash

# Noor AI Agent - Development Server
# Quick script to run the server in development mode

export RELOAD=true
export LOG_LEVEL=debug

echo "🚀 Starting Noor AI Agent in Development Mode..."
echo "📍 Server will be available at: http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo "🔄 Auto-reload enabled for development"
echo ""

exec ./scripts/run_api.sh --reload --log-level debug
