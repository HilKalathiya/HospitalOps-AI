"""
HospitalOps AI — PDF Document Extractor.

Extracts text from PDF documents page-by-page using pypdf.
Detects empty / scanned documents lacking text layers to flag requires_ocr.
"""

from __future__ import annotations

import io
import logging

from pypdf import PdfReader

from app.knowledge.contracts import ExtractedDocument, ExtractedPage
from app.knowledge.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class PDFExtractor(BaseExtractor):
    """Extracts text and page structure from PDF bytes."""

    def extract_from_bytes(self, content: bytes, filename: str) -> ExtractedDocument:
        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception as err:
            logger.error("Failed to parse PDF %s: %s", filename, err)
            raise ValueError(f"Corrupted or invalid PDF file: {err}") from err

        pages: list[ExtractedPage] = []
        raw_parts: list[str] = []
        total_extracted_chars = 0

        for i, page in enumerate(reader.pages):
            page_text = ""
            try:
                page_text = page.extract_text() or ""
            except Exception as err:
                logger.warning("Error extracting page %d of %s: %s", i + 1, filename, err)

            clean_page_text = page_text.strip()
            total_extracted_chars += len(clean_page_text)
            pages.append(ExtractedPage(page_number=i + 1, text=clean_page_text))
            if clean_page_text:
                raw_parts.append(clean_page_text)

        # Scanned PDF detection: if non-empty pages exist but 0 text extracted
        num_pages = len(reader.pages)
        requires_ocr = False
        if num_pages > 0 and total_extracted_chars == 0:
            requires_ocr = True
            logger.warning(
                "PDF %s contains %d pages but 0 text characters extracted (likely scanned image)",
                filename,
                num_pages,
            )

        full_raw_text = "\n\n".join(raw_parts)

        return ExtractedDocument(
            raw_text=full_raw_text,
            pages=pages,
            tables=[],
            metadata={
                "page_count": num_pages,
                "author": reader.metadata.author if reader.metadata else None,
                "title": reader.metadata.title if reader.metadata else None,
            },
            requires_ocr=requires_ocr,
        )
