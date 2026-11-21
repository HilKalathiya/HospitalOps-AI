"""
HospitalOps AI — Knowledge Ingestion Data Contracts.

Internal data transfer objects passed between pipeline stages.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExtractedPage(BaseModel):
    """Content extracted from an individual page (e.g. PDF)."""

    page_number: int
    text: str


class ExtractedTable(BaseModel):
    """Tabular data extracted from document structure."""

    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    caption: str | None = None
    markdown: str = ""


class ExtractedDocument(BaseModel):
    """Raw extracted document content prior to semantic cleaning."""

    raw_text: str
    pages: list[ExtractedPage] = Field(default_factory=list)
    tables: list[ExtractedTable] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    requires_ocr: bool = False


class CleanedSection(BaseModel):
    """Semantically coherent section (heading + body) ready for chunking."""

    title: str | None = None
    text: str
    page_number: int | None = None
    is_table: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class CleanedDocument(BaseModel):
    """Normalized, sanitized document content partitioned into logical sections."""

    full_text: str
    sections: list[CleanedSection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
