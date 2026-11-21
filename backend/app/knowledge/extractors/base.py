"""
HospitalOps AI — Base Document Extractor.

Abstract interface for format-specific document text extractors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.knowledge.contracts import ExtractedDocument


class BaseExtractor(ABC):
    """Abstract base class for format-specific document extractors."""

    @abstractmethod
    def extract_from_bytes(self, content: bytes, filename: str) -> ExtractedDocument:
        """
        Parse raw bytes and extract structured text, pages, and tables.

        Raises:
            ValueError: If the file is corrupted or unreadable.
        """
