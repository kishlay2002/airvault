"""Extractor registry. Maps FileType → BaseExtractor subclass."""

from airvault.types import FileType
from airvault.ingestion.extractors.base import BaseExtractor, ExtractionResult
from airvault.ingestion.extractors.pdf import PDFExtractor
from airvault.ingestion.extractors.image import ImageExtractor
from airvault.ingestion.extractors.text import TextExtractor

EXTRACTOR_MAP: dict[FileType, type[BaseExtractor]] = {
    FileType.PDF: PDFExtractor,
    FileType.IMAGE: ImageExtractor,
    FileType.TEXT: TextExtractor,
    FileType.MARKDOWN: TextExtractor,
}

# Audio extractor is optional (requires faster-whisper)
try:
    from airvault.ingestion.extractors.audio import AudioExtractor
    EXTRACTOR_MAP[FileType.AUDIO] = AudioExtractor
except ImportError:
    pass


def get_extractor(file_type: FileType) -> BaseExtractor:
    """Get an extractor instance for the given file type."""
    cls = EXTRACTOR_MAP.get(file_type)
    if cls is None:
        raise ValueError(f"No extractor for file type: {file_type}")
    return cls()


__all__ = ["get_extractor", "BaseExtractor", "ExtractionResult", "EXTRACTOR_MAP"]
