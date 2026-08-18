from app.extractors.base import BaseExtractor
from app.extractors.pdf import PDFExtractor
from app.extractors.audio import AudioExtractor
from app.extractors.image import ImageExtractor
from app.extractors.text import TextExtractor
from app.models import FileType


EXTRACTOR_MAP: dict[FileType, type[BaseExtractor]] = {
    FileType.PDF: PDFExtractor,
    FileType.AUDIO: AudioExtractor,
    FileType.IMAGE: ImageExtractor,
    FileType.TEXT: TextExtractor,
    FileType.MARKDOWN: TextExtractor,
}


def get_extractor(file_type: FileType) -> BaseExtractor:
    extractor_cls = EXTRACTOR_MAP.get(file_type)
    if not extractor_cls:
        raise ValueError(f"No extractor available for file type: {file_type}")
    return extractor_cls()


__all__ = [
    "BaseExtractor",
    "PDFExtractor",
    "AudioExtractor",
    "ImageExtractor",
    "TextExtractor",
    "get_extractor",
]
