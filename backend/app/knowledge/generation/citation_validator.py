"""
HospitalOps AI — Citation Extraction and Verification Engine (Chunk 4.4).

Verifies citation integrity:
- Extracts bracketed citation markers ([S1], [S2]) from model-generated text.
- Validates every marker against the authoritative Chunk 4.3 retrieval citation package.
- Detects hallucinated/fabricated citation markers (e.g. [S99]).
- Builds deterministic CitationReference contracts containing authoritative document provenance.
"""

from __future__ import annotations

import re

from app.knowledge.generation.contracts import CitationReference
from app.knowledge.retrieval.contracts import ContextBlock, SourceCitation


class CitationValidator:
    """Validates model-generated citation markers against authoritative retrieval provenance."""

    MARKER_PATTERN = re.compile(r"\[(S\d+)\]")

    @classmethod
    def extract_markers(cls, text: str) -> list[str]:
        """
        Extract all citation markers like 'S1', 'S2' from text, preserving first occurrence order.
        """
        raw_matches = cls.MARKER_PATTERN.findall(text)
        seen = set()
        unique_markers = []
        for m in raw_matches:
            if m not in seen:
                seen.add(m)
                unique_markers.append(m)
        return unique_markers

    @classmethod
    def validate_citations(
        cls,
        cited_markers: list[str],
        available_citations: list[SourceCitation],
        context_blocks: list[ContextBlock] | None = None,
    ) -> tuple[bool, list[str], list[CitationReference]]:
        """
        Validate cited markers against available retrieval citations.

        Returns:
            (is_valid, invalid_markers, verified_citations)
        """
        # Build flexible lookup table of available citations by marker and ID
        available_map: dict[str, SourceCitation] = {}
        for c in available_citations:
            clean_id = c.citation_id.strip("[]")
            available_map[clean_id] = c
            available_map[f"[{clean_id}]"] = c
            available_map[c.citation_marker] = c

        # Build block lookup for category and access level
        block_map: dict[str, ContextBlock] = {}
        if context_blocks:
            for b in context_blocks:
                block_map[b.chunk_id] = b

        invalid_markers: list[str] = []
        verified_citations: list[CitationReference] = []
        seen_chunks: set[str] = set()

        for raw_marker in cited_markers:
            clean_marker = raw_marker.strip("[]")
            if clean_marker not in available_map and raw_marker not in available_map:
                invalid_markers.append(clean_marker)
            else:
                cit = available_map.get(clean_marker) or available_map[raw_marker]
                if cit.chunk_id not in seen_chunks:
                    seen_chunks.add(cit.chunk_id)
                    block = block_map.get(cit.chunk_id)
                    verified_citations.append(
                        CitationReference(
                            marker=cit.citation_marker,
                            citation_id=cit.citation_id,
                            document_id=cit.document_id,
                            document_title=cit.document_title,
                            document_version=cit.document_version,
                            chunk_id=cit.chunk_id,
                            section_title=cit.section_title,
                            page_number=cit.page_number,
                            source_reference=cit.source_reference,
                            similarity_score=block.similarity_score if block else None,
                            category=block.category if block else None,
                            access_level=block.access_level if block else None,
                            excerpt=block.content if block else None,
                        )
                    )

        # Sort verified citations by citation_id number (S1, S2, ...)
        def _sort_key(c: CitationReference) -> int:
            try:
                return int(c.citation_id.replace("S", ""))
            except ValueError:
                return 999

        verified_citations.sort(key=_sort_key)
        is_valid = len(invalid_markers) == 0

        return is_valid, invalid_markers, verified_citations

    @classmethod
    def build_all_retrieved_references(
        cls,
        available_citations: list[SourceCitation],
        context_blocks: list[ContextBlock] | None = None,
    ) -> list[CitationReference]:
        """Convert all available retrieval citations into CitationReference contracts."""
        block_map: dict[str, ContextBlock] = {}
        if context_blocks:
            for b in context_blocks:
                block_map[b.chunk_id] = b

        refs = []
        for cit in available_citations:
            block = block_map.get(cit.chunk_id)
            refs.append(
                CitationReference(
                    marker=cit.citation_marker,
                    citation_id=cit.citation_id,
                    document_id=cit.document_id,
                    document_title=cit.document_title,
                    document_version=cit.document_version,
                    chunk_id=cit.chunk_id,
                    section_title=cit.section_title,
                    page_number=cit.page_number,
                    source_reference=cit.source_reference,
                    similarity_score=block.similarity_score if block else None,
                    category=block.category if block else None,
                    access_level=block.access_level if block else None,
                    excerpt=block.content if block else None,
                )
            )
        return refs


# Module-level convenience functions
def extract_markers(text: str) -> list[str]:
    return CitationValidator.extract_markers(text)


def validate_citations(
    cited_markers_or_text: list[str] | str,
    available_citations: list[SourceCitation] | list[ContextBlock],
    context_blocks: list[ContextBlock] | None = None,
) -> tuple[bool, list[str], list[CitationReference]]:
    """Module-level adapter for CitationValidator.validate_citations."""
    if isinstance(cited_markers_or_text, str):
        markers = extract_markers(cited_markers_or_text)
    else:
        markers = cited_markers_or_text

    if available_citations and isinstance(available_citations[0], ContextBlock):
        ctx_blocks = available_citations
        cits = [
            SourceCitation(
                citation_id=b.citation_id,
                citation_marker=f"[{b.citation_id}]",
                document_id=b.document_id,
                document_title=b.document_title,
                document_version=b.document_version,
                chunk_id=b.chunk_id,
                section_title=b.section_title,
                heading_path=b.heading_path,
                page_number=b.page_number,
                source_reference=f"{b.document_title} (v{b.document_version})",
            )
            for b in ctx_blocks
        ]
        return CitationValidator.validate_citations(markers, cits, ctx_blocks)

    return CitationValidator.validate_citations(markers, available_citations, context_blocks)  # type: ignore[arg-type]


def build_all_retrieved_references(
    available_citations: list[SourceCitation] | list[ContextBlock],
    context_blocks: list[ContextBlock] | None = None,
) -> list[CitationReference]:
    """Module-level adapter for CitationValidator.build_all_retrieved_references."""
    if available_citations and isinstance(available_citations[0], ContextBlock):
        ctx_blocks = available_citations
        cits = [
            SourceCitation(
                citation_id=b.citation_id,
                citation_marker=f"[{b.citation_id}]",
                document_id=b.document_id,
                document_title=b.document_title,
                document_version=b.document_version,
                chunk_id=b.chunk_id,
                section_title=b.section_title,
                heading_path=b.heading_path,
                page_number=b.page_number,
                source_reference=f"{b.document_title} (v{b.document_version})",
            )
            for b in ctx_blocks
        ]
        return CitationValidator.build_all_retrieved_references(cits, ctx_blocks)

    return CitationValidator.build_all_retrieved_references(available_citations, context_blocks)  # type: ignore[arg-type]
