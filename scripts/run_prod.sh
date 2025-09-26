#!/bin/bash

# Noor AI Agent - Production Server
# Script to run the server in production mode

export WORKERS=${WORKERS:-4}
export LOG_LEVEL=info

echo "🚀 Starting Noor AI Agent in Production Mode..."
echo "👥 Workers: $WORKERS"
echo "📊 Log Level: $LOG_LEVEL"
echo ""

exec ./scripts/run_api.sh --workers $WORKERS --log-level info
