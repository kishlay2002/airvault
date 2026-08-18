#!/bin/bash
# VaultMind Air-Gap Deployment Script
# Loads images and deploys on an air-gapped machine.

set -euo pipefail

BUNDLE_FILE="${1:-vaultmind-airgap-bundle.tar}"
CHECKSUM_FILE="${BUNDLE_FILE}.sha256"

echo "=== VaultMind Air-Gap Deployment ==="

# Verify checksum
if [ -f "${CHECKSUM_FILE}" ]; then
    echo "[1/3] Verifying checksum..."
    if shasum -a 256 -c "${CHECKSUM_FILE}"; then
        echo "  Checksum verified."
    else
        echo "  ERROR: Checksum mismatch! Bundle may be corrupted."
        exit 1
    fi
else
    echo "[1/3] WARNING: No checksum file found. Skipping verification."
fi

# Load images
echo "[2/3] Loading Docker images from ${BUNDLE_FILE}..."
docker load -i "${BUNDLE_FILE}"

# Deploy
echo "[3/3] Deploying with Docker Compose..."
cd "$(dirname "$0")/../.."
docker compose up -d

echo ""
echo "=== Deployment Complete ==="
echo "  Query API:  http://localhost:8000"
echo "  API Docs:   http://localhost:8000/docs"
echo "  Health:     http://localhost:8000/health"
echo ""
echo "Run 'docker compose logs -f' to view logs."
