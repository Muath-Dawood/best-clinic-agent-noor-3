#!/usr/bin/env bash
set -euo pipefail
# Use a tunneling tool (e.g., ngrok or cloudflared) to expose :8000/webhook/wa to WhatsApp provider.
echo "Run: uvicorn src.app.main:app --reload, then start your tunnel to http://localhost:8000"
