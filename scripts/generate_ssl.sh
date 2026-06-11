#!/usr/bin/env bash
# ============================================================
# BioPay — Generate self-signed SSL certificate for development
# For production, replace with Let's Encrypt or your CA cert.
# ============================================================
set -euo pipefail

CERT_DIR="$(dirname "$0")/../nginx/ssl"
mkdir -p "$CERT_DIR"

if [ -f "$CERT_DIR/cert.pem" ] && [ -f "$CERT_DIR/key.pem" ]; then
  echo "SSL certificates already exist at $CERT_DIR — skipping."
  exit 0
fi

echo "Generating self-signed certificate..."
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout "$CERT_DIR/key.pem" \
  -out    "$CERT_DIR/cert.pem" \
  -subj "/C=US/ST=Dev/L=Dev/O=BioPay/OU=Dev/CN=localhost" \
  -extensions v3_req \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "SSL certificate generated:"
echo "  Certificate: $CERT_DIR/cert.pem"
echo "  Private key: $CERT_DIR/key.pem"
echo ""
echo "NOTE: This is a self-signed certificate for development only."
echo "      Browsers will show a security warning — click 'Advanced → Proceed'."
echo "      For production, use Let's Encrypt: https://letsencrypt.org"
