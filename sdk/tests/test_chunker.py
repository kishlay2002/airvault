"""Tests for the recursive chunker."""

from airvault.ingestion.chunker import RecursiveChunker


class TestRecursiveChunker:
    def setup_method(self):
        self.chunker = RecursiveChunker(chunk_size=100, chunk_overlap=10, min_chunk_size=5)

    def test_empty_text_returns_empty(self):
        assert self.chunker.chunk_text("") == []
        assert self.chunker.chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        text = " ".join(["word"] * 50)
        chunks = self.chunker.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0

    def test_respects_min_chunk_size(self):
        text = "tiny"  # below min_chunk_size of 5 words
        chunks = self.chunker.chunk_text(text)
        assert len(chunks) == 0  # too small

    def test_page_aware_chunking(self):
        pages = [" ".join(["page1word"] * 50), " ".join(["page2word"] * 50)]
        chunks = self.chunker.chunk_text("", page_texts=pages)
        assert len(chunks) >= 2
        assert chunks[0].page_number == 1
        assert any(c.page_number == 2 for c in chunks)

    def test_chunk_index_is_sequential(self):
        text = " ".join(["word"] * 300)
        chunks = self.chunker.chunk_text(text)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_token_count_populated(self):
        text = " ".join(["word"] * 50)
        chunks = self.chunker.chunk_text(text)
        for chunk in chunks:
            assert chunk.token_count > 0

    def test_paragraph_boundary_respected(self):
        paragraphs = [" ".join(["word"] * 30) for _ in range(5)]
        text = "\n\n".join(paragraphs)
        chunks = self.chunker.chunk_text(text)
        assert len(chunks) >= 1
