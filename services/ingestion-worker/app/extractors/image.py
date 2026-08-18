import asyncio
import structlog

from app.extractors.base import BaseExtractor, ExtractionResult

logger = structlog.get_logger()


class ImageExtractor(BaseExtractor):
    async def extract(self, file_path: str) -> ExtractionResult:
        return await asyncio.to_thread(self._extract_sync, file_path)

    def _extract_sync(self, file_path: str) -> ExtractionResult:
        try:
            import pytesseract
            from PIL import Image, ImageFilter

            image = Image.open(file_path)

            # Preprocessing for better OCR accuracy
            image = image.convert("L")  # Grayscale
            image = image.filter(ImageFilter.SHARPEN)

            text = pytesseract.image_to_string(image).strip()

            logger.info(
                "image_ocr_extracted",
                file_path=file_path,
                chars=len(text),
                image_size=image.size,
            )

            return ExtractionResult(
                text=text,
                metadata={"image_size": image.size, "mode": "ocr"},
            )
        except ImportError:
            logger.error("tesseract_or_pillow_not_installed")
            raise RuntimeError("pytesseract and Pillow are required for image extraction")
        except Exception as e:
            logger.error("image_extraction_failed", file_path=file_path, error=str(e))
            raise
