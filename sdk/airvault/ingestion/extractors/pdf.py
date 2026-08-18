"""PDF text extractor using PyMuPDF with OCR fallback."""

from pathlib import Path

import structlog

from airvault.ingestion.extractors.base import BaseExtractor, ExtractionResult

logger = structlog.get_logger()

MIN_TEXT_LENGTH = 50  # chars per page to trigger OCR fallback


class PDFExtractor(BaseExtractor):
    def extract(self, file_path: Path) -> ExtractionResult:
        import fitz  # PyMuPDF

        doc = fitz.open(str(file_path))
        page_texts: list[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()

            # OCR fallback for scanned pages
            if len(text) < MIN_TEXT_LENGTH:
                text = self._ocr_page(page, page_num)

            page_texts.append(text)

        doc.close()
        full_text = "\n\n".join(page_texts)

        logger.info("pdf_extracted", file=file_path.name, pages=len(page_texts))
        return ExtractionResult(
            text=full_text,
            page_texts=page_texts,
            metadata={"pages": len(page_texts)},
        )

    def _ocr_page(self, page, page_num: int) -> str:
        try:
            import fitz
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")

            from PIL import Image
            import pytesseract
            import io

            image = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(image).strip()
            logger.debug("ocr_fallback_used", page=page_num + 1, chars=len(text))
            return text
        except ImportError:
            logger.warning("ocr_unavailable", page=page_num + 1)
            return ""
        except Exception as e:
            logger.error("ocr_failed", page=page_num + 1, error=str(e))
            return ""
