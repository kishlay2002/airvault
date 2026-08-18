"""Plain text / Markdown extractor with encoding detection."""

from pathlib import Path

import chardet
import structlog

from airvault.ingestion.extractors.base import BaseExtractor, ExtractionResult

logger = structlog.get_logger()


class TextExtractor(BaseExtractor):
    def extract(self, file_path: Path) -> ExtractionResult:
        raw = file_path.read_bytes()
        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "utf-8") or "utf-8"

        text = raw.decode(encoding, errors="replace").strip()

        logger.info("text_extracted", file=file_path.name, encoding=encoding, chars=len(text))
        return ExtractionResult(text=text, metadata={"encoding": encoding})
