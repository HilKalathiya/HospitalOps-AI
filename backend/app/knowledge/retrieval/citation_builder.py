"""
HospitalOps AI — Source Citation Generator (Chunk 4.3).

Generates stable, human-readable, and machine-traceable citations for retrieved knowledge chunks:
- Assigns stable citation identifiers ([S1], [S2], etc.)
- Maps chunks directly to document ID, active version, section path, and page numbers
- Formats reference strings without fabricating nonexistent attributes
- Computes citation header overhead for token budgeting
"""

from __future__ import annotations

from app.knowledge.retrieval.contracts import KnowledgeSearchResult, SourceCitation
from app.knowledge.retrieval.token_budget import get_token_count


class CitationBuilder:
    """Builds structured and traceable source citation models."""

    @classmethod
    def build_citation(
        cls,
        chunk: KnowledgeSearchResult,
        citation_number: int,
    ) -> SourceCitation:
        """
        Create a SourceCitation contract from a retrieved search result.

        Args:
            chunk: Retrieved KnowledgeSearchResult.
            citation_number: 1-based sequential integer index within this retrieval execution.
        """
        citation_id = f"S{citation_number}"
        citation_marker = f"[{citation_id}]"

        doc_title = chunk.document_title or "Untitled Document"
        version = chunk.document_version or 1

        parts = [f"{citation_marker} {doc_title} — Version {version}"]
        heading_path: list[str] = []

        if chunk.section_title:
            parts.append(f"Section: {chunk.section_title}")
            heading_path.append(chunk.section_title)

        if chunk.page_number is not None:
            parts.append(f"Page {chunk.page_number}")

        source_reference = " — ".join(parts)

        return SourceCitation(
            citation_id=citation_id,
            citation_marker=citation_marker,
            document_id=chunk.document_id,
            document_title=doc_title,
            document_version=version,
            chunk_id=chunk.chunk_id,
            section_title=chunk.section_title,
            heading_path=heading_path,
            page_number=chunk.page_number,
            source_reference=source_reference,
        )

    @classmethod
    def format_citation_header(cls, citation: SourceCitation) -> str:
        """
        Produce a compact citation header line for the formatted context block.
        """
        sec = f' | Section: "{citation.section_title}"' if citation.section_title else ""
        pg = f" | Page: {citation.page_number}" if citation.page_number is not None else ""
        return f'{citation.citation_marker} Document: "{citation.document_title}" (v{citation.document_version}){sec}{pg}'

    @classmethod
    def estimate_citation_overhead(cls, chunk: KnowledgeSearchResult, citation_number: int) -> int:
        """
        Compute token overhead of the citation header and boundary tags.
        """
        citation_id = f"S{citation_number}"
        header_sample = (
            f"[{citation_id}] Document: \"{chunk.document_title}\" (v{chunk.document_version}) | "
            f"Section: \"{chunk.section_title or ''}\" | Page: {chunk.page_number or 1}\n"
            "<reference_content>\n</reference_content>\n"
        )
        return get_token_count(header_sample)
