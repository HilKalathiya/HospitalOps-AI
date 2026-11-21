"""
HospitalOps AI — DOCX Document Extractor.

Extracts text, section headings, and structured tables from Word (.docx) documents.
Converts Word tables to markdown table syntax to retain relational integrity.
"""

from __future__ import annotations

import io
import logging

from docx import Document

from app.knowledge.contracts import ExtractedDocument, ExtractedTable
from app.knowledge.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class DocxExtractor(BaseExtractor):
    """Extracts paragraphs, headings, and tables from DOCX files."""

    def extract_from_bytes(self, content: bytes, filename: str) -> ExtractedDocument:
        try:
            doc = Document(io.BytesIO(content))
        except Exception as err:
            logger.error("Failed to parse DOCX %s: %s", filename, err)
            raise ValueError(f"Corrupted or invalid DOCX document: {err}") from err

        text_parts: list[str] = []
        tables: list[ExtractedTable] = []

        # 1. Process paragraphs with heading level annotations
        for p in doc.paragraphs:
            txt = p.text.strip()
            if not txt:
                continue

            style_name = p.style.name.lower() if p.style else ""
            if "heading 1" in style_name:
                text_parts.append(f"# {txt}")
            elif "heading 2" in style_name:
                text_parts.append(f"## {txt}")
            elif "heading 3" in style_name:
                text_parts.append(f"### {txt}")
            elif "list" in style_name:
                text_parts.append(f"- {txt}")
            else:
                text_parts.append(txt)

        # 2. Process tables and convert them to markdown representations
        for t_idx, table in enumerate(doc.tables):
            table_rows: list[list[str]] = []
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                table_rows.append(cells)

            if not table_rows:
                continue

            headers = table_rows[0]
            data_rows = table_rows[1:] if len(table_rows) > 1 else []

            # Format markdown table
            header_line = "| " + " | ".join(headers) + " |"
            sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
            data_lines = ["| " + " | ".join(r) + " |" for r in data_rows]
            md_table = "\n".join([header_line, sep_line] + data_lines)

            tables.append(ExtractedTable(
                headers=headers,
                rows=data_rows,
                caption=f"Table {t_idx + 1}",
                markdown=md_table,
            ))
            text_parts.append(f"\n{md_table}\n")

        full_text = "\n\n".join(text_parts)

        return ExtractedDocument(
            raw_text=full_text,
            pages=[],
            tables=tables,
            metadata={
                "paragraph_count": len(doc.paragraphs),
                "table_count": len(tables),
            },
            requires_ocr=False,
        )
