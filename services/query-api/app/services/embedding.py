import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = structlog.get_logger()


class EmbeddingService:
    """Local embedding service. Loaded once, shared across requests."""

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
                settings.embedding_model, device="cpu"
            )
            logger.info("embedding_model_loaded", model=settings.embedding_model)

    @property
    def model(self) -> SentenceTransformer:
        assert self._model is not None
        return self._model

    def embed_query(self, query: str) -> list[float]:
        embedding: np.ndarray = self.model.encode(
            [query], normalize_embeddings=True, show_progress_bar=False
        )
        return embedding[0].tolist()

    @property
    def dimension(self) -> int:
        return settings.embedding_dimension
