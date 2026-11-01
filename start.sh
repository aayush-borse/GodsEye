#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -f "frontend/dist/index.html" ]; then
  echo "[GOD'S EYE] Building React frontend..."
  (cd frontend && npm install && npm run build)
fi
uv run python run.py
