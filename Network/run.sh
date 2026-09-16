#!/usr/bin/env bash
# ── NetManager startup script ──────────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$SCRIPT_DIR/backend"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       NetManager — Starting Up       ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Python venv
if [ ! -d "$BACKEND/venv" ]; then
  echo "→ Creating Python virtualenv…"
  python3 -m venv "$BACKEND/venv"
fi

source "$BACKEND/venv/bin/activate"

echo "→ Installing dependencies…"
pip install -q -r "$BACKEND/requirements.txt"

echo ""
echo "→ Starting FastAPI server at http://localhost:8000"
echo "→ Press Ctrl+C to stop"
echo ""

cd "$BACKEND"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
