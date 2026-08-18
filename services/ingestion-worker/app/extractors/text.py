import structlog
import chardet

from app.extractors.base import BaseExtractor, ExtractionResult

logger = structlog.get_logger()


class TextExtractor(BaseExtractor):
    async def extract(self, file_path: str) -> ExtractionResult:
        raw = open(file_path, "rb").read()

        # Detect encoding
        detection = chardet.detect(raw)
        encoding = detection.get("encoding", "utf-8") or "utf-8"

        text = raw.decode(encoding, errors="replace").strip()

        logger.info(
            "text_extracted",
            file_path=file_path,
            encoding=encoding,
            chars=len(text),
        )

        return ExtractionResult(
            text=text,
            metadata={"encoding": encoding},
        )
