#!/bin/bash
# Verify model artifact checksums before loading.
# Prevents model tampering in the supply chain.

set -euo pipefail

MODEL_DIR="${1:-/root/.cache/huggingface}"

echo "=== Model Artifact Verification ==="

if [ ! -d "${MODEL_DIR}" ]; then
    echo "ERROR: Model directory not found: ${MODEL_DIR}"
    exit 1
fi

CHECKSUM_FILE="${MODEL_DIR}/CHECKSUMS"

if [ -f "${CHECKSUM_FILE}" ]; then
    echo "Verifying against ${CHECKSUM_FILE}..."
    cd "${MODEL_DIR}"
    if sha256sum --check CHECKSUMS 2>/dev/null || shasum -a 256 -c CHECKSUMS 2>/dev/null; then
        echo "All model artifacts verified."
    else
        echo "ERROR: Model checksum mismatch! Possible tampering detected."
        exit 1
    fi
else
    echo "No CHECKSUMS file found. Generating checksums..."
    cd "${MODEL_DIR}"
    find . -type f ! -name "CHECKSUMS" -exec sha256sum {} \; > CHECKSUMS
    echo "Checksums written to ${CHECKSUM_FILE}"
    echo "Sign this file with GPG for production use:"
    echo "  gpg --sign ${CHECKSUM_FILE}"
fi
