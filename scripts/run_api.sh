#!/usr/bin/env bash
set -euo pipefail
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
