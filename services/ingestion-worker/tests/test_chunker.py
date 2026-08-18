"""Tests for the recursive text chunker."""

import pytest
from app.chunker import RecursiveChunker


class TestRecursiveChunker:
    def setup_method(self):
        self.chunker = RecursiveChunker(chunk_size=50, chunk_overlap=10, min_chunk_size=5)

    def test_short_text_single_chunk(self):
        text = "This is a short text."
        chunks = self.chunker.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].chunk_index == 0

    def test_empty_text_no_chunks(self):
        chunks = self.chunker.chunk_text("")
        assert len(chunks) == 0

    def test_text_below_min_size_skipped(self):
        chunker = RecursiveChunker(chunk_size=50, chunk_overlap=10, min_chunk_size=100)
        chunks = chunker.chunk_text("tiny")
        assert len(chunks) == 0

    def test_long_text_produces_multiple_chunks(self):
        text = " ".join([f"word{i}" for i in range(200)])
        chunks = self.chunker.chunk_text(text)
        assert len(chunks) > 1

    def test_chunk_indices_sequential(self):
        text = " ".join([f"word{i}" for i in range(200)])
        chunks = self.chunker.chunk_text(text)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_page_texts_preserve_page_numbers(self):
        pages = ["Page one content here.", "Page two content here.", "Page three content here."]
        chunks = self.chunker.chunk_text("", page_texts=pages)
        page_numbers = {c.page_number for c in chunks}
        assert page_numbers.issubset({1, 2, 3})

    def test_token_count_populated(self):
        text = "This is a simple test with several words in it."
        chunks = self.chunker.chunk_text(text)
        assert all(c.token_count > 0 for c in chunks)
