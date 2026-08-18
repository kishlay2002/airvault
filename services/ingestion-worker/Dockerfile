# VaultMind Ingestion Worker — Multi-stage Docker build
# Includes OCR (Tesseract) and audio (faster-whisper) dependencies.

FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# Pre-download embedding model
RUN pip install --no-cache-dir sentence-transformers && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

FROM python:3.12-slim AS runtime

# Install Tesseract OCR and audio processing deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

WORKDIR /app
COPY app/ ./app/

RUN useradd -r -s /bin/false vaultmind && \
    mkdir -p /data/inbox && chown vaultmind:vaultmind /data/inbox
USER vaultmind

CMD ["python", "-m", "arq", "app.worker.WorkerSettings"]
