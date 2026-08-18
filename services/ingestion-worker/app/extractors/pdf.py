import asyncio
import structlog
import fitz  # PyMuPDF

from app.extractors.base import BaseExtractor, ExtractionResult

logger = structlog.get_logger()

MIN_TEXT_PER_PAGE = 50  # chars — below this, fall back to OCR


class PDFExtractor(BaseExtractor):
    async def extract(self, file_path: str) -> ExtractionResult:
        return await asyncio.to_thread(self._extract_sync, file_path)

    def _extract_sync(self, file_path: str) -> ExtractionResult:
        doc = fitz.open(file_path)
        page_texts: list[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()

            # If text extraction yields very little, try OCR fallback
            if len(text) < MIN_TEXT_PER_PAGE:
                text = self._ocr_page(page, page_num)

            page_texts.append(text)

        doc.close()

        full_text = "\n\n".join(page_texts)
        logger.info(
            "pdf_extracted",
            file_path=file_path,
            pages=len(page_texts),
            total_chars=len(full_text),
        )

        return ExtractionResult(
            text=full_text,
            page_texts=page_texts,
            metadata={"pages": len(page_texts)},
        )

    def _ocr_page(self, page: fitz.Page, page_num: int) -> str:
        """OCR fallback for scanned pages using Tesseract."""
        try:
            import pytesseract
            from PIL import Image
            import io

            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            text = pytesseract.image_to_string(image).strip()

            logger.info("ocr_fallback_used", page_num=page_num, chars=len(text))
            return text
        except ImportError:
            logger.warning("tesseract_not_available", page_num=page_num)
            return ""
        except Exception as e:
            logger.error("ocr_failed", page_num=page_num, error=str(e))
            return ""
