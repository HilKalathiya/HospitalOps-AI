"""
HospitalOps AI — HTML Document Extractor.

Extracts structured text from HTML documents using BeautifulSoup4.
Removes navigation, scripts, styles, and footers, and converts HTML tables
into Markdown tables.
"""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from app.knowledge.contracts import ExtractedDocument, ExtractedTable
from app.knowledge.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class HtmlExtractor(BaseExtractor):
    """Extracts text, headings, and tables from HTML content."""

    def extract_from_bytes(self, content: bytes, filename: str) -> ExtractedDocument:
        try:
            html_str = content.decode("utf-8")
        except UnicodeDecodeError:
            html_str = content.decode("latin-1", errors="replace")

        soup = BeautifulSoup(html_str, "html.parser")

        # Strip unhelpful elements
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            tag.decompose()

        tables: list[ExtractedTable] = []

        # Convert <table> to markdown
        for t_idx, table_tag in enumerate(soup.find_all("table")):
            rows: list[list[str]] = []
            for tr in table_tag.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
                if cells:
                    rows.append(cells)

            if not rows:
                continue

            headers = rows[0]
            data_rows = rows[1:] if len(rows) > 1 else []

            header_line = "| " + " | ".join(headers) + " |"
            sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
            data_lines = ["| " + " | ".join(r) + " |" for r in data_rows]
            md_table = "\n".join([header_line, sep_line] + data_lines)

            tables.append(
                ExtractedTable(
                    headers=headers,
                    rows=data_rows,
                    caption=f"Table {t_idx + 1}",
                    markdown=md_table,
                )
            )

            # Replace table tag in soup with plaintext markdown
            table_tag.replace_with(soup.new_string(f"\n\n{md_table}\n\n"))

        # Extract text from remaining DOM
        text = soup.get_text(separator="\n\n")

        title_tag = soup.find("title")
        doc_title = title_tag.get_text(strip=True) if title_tag else None

        return ExtractedDocument(
            raw_text=text,
            pages=[],
            tables=tables,
            metadata={"title": doc_title, "table_count": len(tables)},
            requires_ocr=False,
        )
