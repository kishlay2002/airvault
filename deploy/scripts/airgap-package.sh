#!/bin/bash
# VaultMind Air-Gap Packaging Script
# Saves all required Docker images to a single tarball for offline deployment.

set -euo pipefail

OUTPUT_FILE="${1:-vaultmind-airgap-bundle.tar}"
IMAGES=(
    "vaultmind/query-api:latest"
    "vaultmind/ingestion-worker:latest"
    "vaultmind/file-sentinel:latest"
    "qdrant/qdrant:v1.9.0"
    "postgres:16-alpine"
    "redis:7-alpine"
)

echo "=== VaultMind Air-Gap Packaging ==="
echo "Output: ${OUTPUT_FILE}"
echo ""

# Build application images first
echo "[1/3] Building application images..."
cd "$(dirname "$0")/../.."
docker compose build --no-cache

# Save all images
echo "[2/3] Saving ${#IMAGES[@]} images to ${OUTPUT_FILE}..."
docker save "${IMAGES[@]}" -o "${OUTPUT_FILE}"

# Compute checksum
echo "[3/3] Computing SHA-256 checksum..."
shasum -a 256 "${OUTPUT_FILE}" > "${OUTPUT_FILE}.sha256"

SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
echo ""
echo "=== Package Complete ==="
echo "  File:     ${OUTPUT_FILE} (${SIZE})"
echo "  Checksum: ${OUTPUT_FILE}.sha256"
echo ""
echo "Transfer both files to the air-gapped environment."
echo "Then run: bash deploy/scripts/airgap-deploy.sh"
