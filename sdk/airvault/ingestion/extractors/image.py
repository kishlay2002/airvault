"""Image OCR extractor using pytesseract."""

from pathlib import Path

import structlog

from airvault.ingestion.extractors.base import BaseExtractor, ExtractionResult

logger = structlog.get_logger()


class ImageExtractor(BaseExtractor):
    def extract(self, file_path: Path) -> ExtractionResult:
        import pytesseract
        from PIL import Image, ImageFilter

        image = Image.open(file_path)

        # Basic preprocessing for better OCR
        if image.mode != "L":
            image = image.convert("L")
        image = image.filter(ImageFilter.SHARPEN)

        text = pytesseract.image_to_string(image).strip()

        logger.info("image_extracted", file=file_path.name, chars=len(text))
        return ExtractionResult(
            text=text,
            metadata={"width": image.width, "height": image.height},
        )
