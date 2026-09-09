#!/usr/bin/env bash
# SIH 2026 Problem Statement 26127: One-Click Command Center Launcher
# Starts Backend (FastAPI + Simulator + WebSockets) & Frontend (Vite + React HUD)

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "======================================================================"
echo " SIH 2026: INTELLIGENT TRAFFIC SURVEILLANCE & COMMAND CENTER (PS 26127)"
echo "======================================================================"

# 1. Ensure database is initialized and seeded
echo "[1/3] Checking database seed..."
python3 scripts/seed_db.py

# 2. Trap signals for graceful shutdown of both servers
cleanup() {
    echo ""
    echo "[!] Shutting down Command Center servers..."
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 3. Start Backend FastAPI on port 8000
echo "[2/3] Launching FastAPI Backend on http://localhost:8000..."
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait briefly for backend to initialize
sleep 2

# 4. Start Frontend Vite on port 3000
echo "[3/3] Launching Police Command HUD on http://localhost:3000..."
cd frontend
npm run dev -- --host 0.0.0.0 --port 3000 &
FRONTEND_PID=$!

echo ""
echo "======================================================================"
echo " COMMAND CENTER IS LIVE!"
echo "======================================================================"
echo "  • Dashboard HUD:  http://localhost:3000"
echo "  • Backend API:    http://localhost:8000"
echo "  • Swagger Docs:   http://localhost:8000/docs"
echo "  • Live WebSocket: ws://localhost:8000/ws/live-feed"
echo "======================================================================"
echo "Press Ctrl+C to terminate both servers."

# Keep parent script running
wait
