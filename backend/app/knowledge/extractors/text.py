"""
HospitalOps AI — Plain Text Extractor.

Extracts plain text (.txt) files with encoding detection fallbacks.
"""

from __future__ import annotations

from app.knowledge.contracts import ExtractedDocument
from app.knowledge.extractors.base import BaseExtractor


class PlainTextExtractor(BaseExtractor):
    """Extracts text from plain text (.txt) files."""

    def extract_from_bytes(self, content: bytes, filename: str) -> ExtractedDocument:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception as err:
                raise ValueError(f"Unable to decode text file {filename}: {err}") from err

        return ExtractedDocument(
            raw_text=text,
            pages=[],
            tables=[],
            metadata={"format": "plain_text"},
            requires_ocr=False,
        )
