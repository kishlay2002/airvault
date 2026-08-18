# VaultMind Query API — Multi-stage Docker build
# All dependencies installed at build time. No runtime downloads.

FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# Download and cache the embedding model at build time (air-gap ready)
RUN pip install --no-cache-dir sentence-transformers && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

FROM python:3.12-slim AS runtime

# Install minimal runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages
COPY --from=builder /install /usr/local
# Copy cached model
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

WORKDIR /app
COPY app/ ./app/

# Non-root user
RUN useradd -r -s /bin/false vaultmind
USER vaultmind

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
