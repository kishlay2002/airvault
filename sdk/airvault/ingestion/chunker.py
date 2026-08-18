"""Recursive character chunker with overlap and page tracking."""

from airvault.types import ChunkData

SEPARATORS = ["\n\n", "\n", ". ", " "]


class RecursiveChunker:
    """Splits text into overlapping chunks using a separator hierarchy.

    Respects paragraph and sentence boundaries where possible.
    Supports page-aware chunking for PDFs.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64, min_chunk_size: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(
        self,
        text: str,
        page_texts: list[str] | None = None,
    ) -> list[ChunkData]:
        """Chunk text into overlapping segments.

        If page_texts is provided, chunks are created per-page with page numbers.
        Otherwise, the full text is chunked as a flat document.
        """
        if page_texts:
            return self._chunk_pages(page_texts)
        return self._chunk_flat(text)

    def _chunk_flat(self, text: str) -> list[ChunkData]:
        if not text.strip():
            return []

        raw_chunks = self._recursive_split(text, SEPARATORS)
        return self._build_chunk_data(raw_chunks, page_number=None)

    def _chunk_pages(self, page_texts: list[str]) -> list[ChunkData]:
        all_chunks: list[ChunkData] = []
        idx = 0

        for page_num, page_text in enumerate(page_texts, start=1):
            if not page_text.strip():
                continue
            raw_chunks = self._recursive_split(page_text, SEPARATORS)
            for content in raw_chunks:
                word_count = len(content.split())
                if word_count < self.min_chunk_size:
                    continue
                all_chunks.append(
                    ChunkData(
                        content=content,
                        chunk_index=idx,
                        page_number=page_num,
                        token_count=word_count,
                    )
                )
                idx += 1

        return all_chunks

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        if not separators:
            return self._split_by_words(text)

        sep = separators[0]
        parts = text.split(sep)
        merged: list[str] = []
        current = ""

        for part in parts:
            candidate = (current + sep + part).strip() if current else part.strip()
            if len(candidate.split()) <= self.chunk_size:
                current = candidate
            else:
                if current.strip():
                    merged.append(current.strip())
                if len(part.split()) > self.chunk_size:
                    sub_chunks = self._recursive_split(part, separators[1:])
                    merged.extend(sub_chunks)
                    current = ""
                else:
                    current = part.strip()

        if current.strip():
            merged.append(current.strip())

        return merged

    def _split_by_words(self, text: str) -> list[str]:
        words = text.split()
        chunks: list[str] = []
        i = 0
        while i < len(words):
            end = min(i + self.chunk_size, len(words))
            chunk = " ".join(words[i:end])
            chunks.append(chunk)
            i = end - self.chunk_overlap if end < len(words) else end
        return chunks

    def _build_chunk_data(self, raw_chunks: list[str], page_number: int | None) -> list[ChunkData]:
        results: list[ChunkData] = []
        for idx, content in enumerate(raw_chunks):
            word_count = len(content.split())
            if word_count < self.min_chunk_size:
                continue
            results.append(
                ChunkData(
                    content=content,
                    chunk_index=idx,
                    page_number=page_number,
                    token_count=word_count,
                )
            )
        return results
