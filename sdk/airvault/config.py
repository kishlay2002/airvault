"""AirVault configuration.

All settings can be overridden via environment variables prefixed with AIRVAULT_.
Example: AIRVAULT_QDRANT_HOST=10.0.0.5 python my_app.py
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class AirVaultConfig(BaseSettings):
    """Configuration for the AirVault engine.

    All settings have sensible defaults for local development.
    Override via constructor kwargs or AIRVAULT_* environment variables.

    Examples:
        # Via constructor
        config = AirVaultConfig(qdrant_host="10.0.0.5")

        # Via environment
        export AIRVAULT_QDRANT_HOST=10.0.0.5
        export AIRVAULT_EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
        config = AirVaultConfig()  # picks up env vars
    """

    model_config = {"env_prefix": "AIRVAULT_"}

    # Storage
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    postgres_dsn: str = "postgresql+asyncpg://airvault:changeme@localhost:5432/airvault"

    # Embedding
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384
    embedding_batch_size: int = 64

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 64
    min_chunk_size: int = 50

    # Query
    default_top_k: int = 5
    max_top_k: int = 20

    # Ingestion
    dedup_enabled: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "console"
