from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    postgres_dsn: str = "postgresql+asyncpg://vaultmind:changeme@localhost:5432/vaultmind"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # Embedding
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 64
    min_chunk_size: int = 50

    # Worker
    max_retries: int = 3
    retry_base_delay: int = 30

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
