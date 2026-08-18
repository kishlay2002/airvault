"""Embedding service — loads a local sentence-transformers model once."""

import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()


class EmbeddingService:
    """Singleton-like embedding service using a local model.

    Loads the model on first access and reuses it across all operations.
    No external API calls — fully offline.
    """

    _instances: dict[str, "EmbeddingService"] = {}

    def __new__(cls, model_name: str, dimension: int = 384) -> "EmbeddingService":
        if model_name not in cls._instances:
            instance = super().__new__(cls)
            instance._model = None
            instance._model_name = model_name
            instance._dimension = dimension
            cls._instances[model_name] = instance
        return cls._instances[model_name]

    def __init__(self, model_name: str, dimension: int = 384):
        self._model_name = model_name
        self._dimension = dimension

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("loading_embedding_model", model=self._model_name)
            self._model = SentenceTransformer(self._model_name, device="cpu")
            logger.info("embedding_model_loaded", model=self._model_name)
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts. Returns list of float vectors."""
        embeddings: np.ndarray = self.model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return embeddings.tolist()

    def embed_batched(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Embed texts in batches to prevent OOM on large documents.

        Args:
            texts: List of text strings to embed.
            batch_size: Number of texts per batch (default 64).

        Returns:
            List of embedding vectors.
        """
        if len(texts) <= batch_size:
            return self.embed(texts)

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            all_embeddings.extend(self.embed(batch))
            logger.debug("embed_batch", batch=i // batch_size + 1, chunks=len(batch))
        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        return self.embed([query])[0]
