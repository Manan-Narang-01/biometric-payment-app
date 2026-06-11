#!/usr/bin/env bash
# ============================================================
# BioPay — One-command startup script
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  BioPay — Biometric Payment Platform ║"
echo "╚══════════════════════════════════════╝"
echo ""

# 1. Copy .env if missing
if [ ! -f "$ROOT/.env" ]; then
  echo "Creating .env from .env.example..."
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "✓ .env created. Edit it before going to production."
fi

# 2. Generate SSL cert if missing
bash "$ROOT/scripts/generate_ssl.sh"

# 3. Start services
echo ""
echo "Starting BioPay services..."
cd "$ROOT"
docker compose up --build -d

echo ""
echo "Waiting for services to be healthy..."
sleep 8

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  BioPay is running!                                  ║"
echo "║                                                      ║"
echo "║  Web app  → https://localhost                        ║"
echo "║  API docs → https://localhost/api/v1/docs            ║"
echo "║                                                      ║"
echo "║  Accept the self-signed cert in your browser.        ║"
echo "║  Use 'docker compose logs -f' to view live logs.     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
