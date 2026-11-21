"""
HospitalOps AI — Document Extractor Factory.

Routes document file formats to their corresponding BaseExtractor implementation.
"""

from __future__ import annotations

from app.knowledge.extractors.base import BaseExtractor
from app.knowledge.extractors.docx import DocxExtractor
from app.knowledge.extractors.html import HtmlExtractor
from app.knowledge.extractors.markdown import MarkdownExtractor
from app.knowledge.extractors.pdf import PDFExtractor
from app.knowledge.extractors.text import PlainTextExtractor
from app.models.knowledge import SupportedFileType


def get_extractor(file_type: SupportedFileType) -> BaseExtractor:
    """Return extractor instance for the given file type."""
    if file_type == SupportedFileType.PDF:
        return PDFExtractor()
    if file_type == SupportedFileType.DOCX:
        return DocxExtractor()
    if file_type == SupportedFileType.MD:
        return MarkdownExtractor()
    if file_type == SupportedFileType.TXT:
        return PlainTextExtractor()
    if file_type == SupportedFileType.HTML:
        return HtmlExtractor()

    raise ValueError(f"Unsupported file type for extraction: {file_type}")
