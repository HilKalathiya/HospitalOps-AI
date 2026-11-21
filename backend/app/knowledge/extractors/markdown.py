"""
HospitalOps AI — Markdown Document Extractor.

Extracts text, preserving hierarchy of markdown headers, blockquotes, and tables.
"""

from __future__ import annotations

import logging

from app.knowledge.contracts import ExtractedDocument
from app.knowledge.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class MarkdownExtractor(BaseExtractor):
    """Extracts text from Markdown (.md) documents."""

    def extract_from_bytes(self, content: bytes, filename: str) -> ExtractedDocument:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception as err:
                raise ValueError(f"Unable to decode Markdown file {filename}: {err}") from err

        return ExtractedDocument(
            raw_text=text,
            pages=[],
            tables=[],
            metadata={"format": "markdown"},
            requires_ocr=False,
        )
