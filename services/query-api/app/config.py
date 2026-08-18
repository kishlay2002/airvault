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

    # Query defaults
    default_top_k: int = 5
    max_top_k: int = 20

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
