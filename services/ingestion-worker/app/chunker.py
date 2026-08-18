import structlog

from app.models import ChunkData
from app.config import settings

logger = structlog.get_logger()

SEPARATORS = ["\n\n", "\n", ". ", " "]


class RecursiveChunker:
    def __init__(
        self,
        chunk_size: int = settings.chunk_size,
        chunk_overlap: int = settings.chunk_overlap,
        min_chunk_size: int = settings.min_chunk_size,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, page_texts: list[str] | None = None) -> list[ChunkData]:
        """Split text into overlapping chunks, preserving page boundaries where possible."""
        if page_texts:
            return self._chunk_with_pages(page_texts)
        return self._chunk_flat(text)

    def _chunk_with_pages(self, page_texts: list[str]) -> list[ChunkData]:
        """Chunk text while tracking page numbers."""
        chunks: list[ChunkData] = []
        chunk_index = 0

        for page_num, page_text in enumerate(page_texts, start=1):
            if not page_text.strip():
                continue

            page_chunks = self._recursive_split(page_text)
            for chunk_text in page_chunks:
                if len(chunk_text.strip()) < self.min_chunk_size:
                    continue
                chunks.append(
                    ChunkData(
                        content=chunk_text.strip(),
                        chunk_index=chunk_index,
                        page_number=page_num,
                        token_count=len(chunk_text.split()),
                    )
                )
                chunk_index += 1

        logger.info("chunking_complete", total_chunks=len(chunks))
        return chunks

    def _chunk_flat(self, text: str) -> list[ChunkData]:
        """Chunk text without page tracking."""
        raw_chunks = self._recursive_split(text)
        chunks: list[ChunkData] = []

        for i, chunk_text in enumerate(raw_chunks):
            if len(chunk_text.strip()) < self.min_chunk_size:
                continue
            chunks.append(
                ChunkData(
                    content=chunk_text.strip(),
                    chunk_index=i,
                    token_count=len(chunk_text.split()),
                )
            )

        logger.info("chunking_complete", total_chunks=len(chunks))
        return chunks

    def _recursive_split(self, text: str) -> list[str]:
        """Recursively split text using separator hierarchy."""
        if len(text.split()) <= self.chunk_size:
            return [text] if text.strip() else []

        # Find the best separator
        for separator in SEPARATORS:
            if separator in text:
                return self._split_by_separator(text, separator)

        # Fallback: hard split by word count
        return self._hard_split(text)

    def _split_by_separator(self, text: str, separator: str) -> list[str]:
        """Split text by separator and merge into chunks respecting size limits."""
        parts = text.split(separator)
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_size = 0

        for part in parts:
            part_size = len(part.split())
            if current_size + part_size > self.chunk_size and current_chunk:
                chunks.append(separator.join(current_chunk))
                # Overlap: keep last portion
                overlap_parts: list[str] = []
                overlap_size = 0
                for p in reversed(current_chunk):
                    if overlap_size + len(p.split()) > self.chunk_overlap:
                        break
                    overlap_parts.insert(0, p)
                    overlap_size += len(p.split())
                current_chunk = overlap_parts
                current_size = overlap_size

            current_chunk.append(part)
            current_size += part_size

        if current_chunk:
            chunks.append(separator.join(current_chunk))

        return chunks

    def _hard_split(self, text: str) -> list[str]:
        """Fallback: split by word count."""
        words = text.split()
        chunks: list[str] = []

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i : i + self.chunk_size]
            chunks.append(" ".join(chunk_words))

        return chunks
