#!/usr/bin/env bash
# TrustNet AI — Linux/macOS Local Development Launcher

set -e

echo "======================================================="
echo "         TrustNet AI - Local Development Launcher      "
echo "======================================================="

if [ ! -d ".venv" ]; then
    echo "[ERROR] Virtual environment .venv not found."
    echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -e shared/"
    exit 1
fi

echo "[1/3] Starting Apache Kafka 3.7 (Docker)..."
docker compose up -d kafka

echo "[2/3] Launching backend microservices in background..."
source .venv/bin/activate
uvicorn gateway.app.main:app --port 8000 --reload &
uvicorn services.auth.app.main:app --port 8001 --reload &
uvicorn services.scan_management.app.main:app --port 8002 --reload &
uvicorn services.image_deepfake.app.main:app --port 8003 --reload &
uvicorn services.trust_engine.app.main:app --port 8004 --reload &

echo "[3/3] Launching React Frontend..."
cd frontend
npm run dev
