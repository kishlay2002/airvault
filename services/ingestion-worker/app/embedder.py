import numpy as np
import structlog

from sentence_transformers import SentenceTransformer

from app.config import settings

logger = structlog.get_logger()


class EmbeddingService:
    """Local embedding service using sentence-transformers.

    Loads model once at startup. No external API calls — fully offline.
    """

    _instance: "EmbeddingService | None" = None
    _model: SentenceTransformer | None = None

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if EmbeddingService._model is None:
            logger.info("loading_embedding_model", model=settings.embedding_model)
            EmbeddingService._model = SentenceTransformer(
                settings.embedding_model,
                device="cpu",
            )
            logger.info("embedding_model_loaded", model=settings.embedding_model)

    @property
    def model(self) -> SentenceTransformer:
        assert self._model is not None, "Embedding model not loaded"
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors as lists of floats.
        """
        if not texts:
            return []

        embeddings: np.ndarray = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        logger.info("embeddings_generated", count=len(texts), dimension=embeddings.shape[1])
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query text."""
        result = self.embed([query])
        return result[0]

    @property
    def dimension(self) -> int:
        return settings.embedding_dimension
