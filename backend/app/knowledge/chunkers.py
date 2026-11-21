"""
HospitalOps AI — Structure-Aware Document Chunker.

Splits cleaned documents into semantically coherent, bounded chunks:
- Respects section headings (#, ##, ###) and paragraph boundaries
- Preserves markdown tables as atomic units whenever possible
- Applies configurable target chunk sizes and sliding-window overlap
- Emits deterministic chunk IDs: {doc_id}_v{version}_c{index}
- Annotates each chunk with section headers, page numbers, and token counts
"""

from __future__ import annotations

import hashlib
import re

from app.models.knowledge import (
    AccessLevel,
    DocumentCategory,
    KnowledgeChunk,
    KnowledgeChunkMetadata,
)


def estimate_tokens(text: str) -> int:
    """Fast approximation of token count (~4 characters per token)."""
    if not text:
        return 0
    words = len(text.split())
    # Blend word count (1 word ~= 1.33 tokens) and character count (len / 4)
    return max(1, int(words * 1.3))


class StructureAwareChunker:
    """Structure-aware chunker for knowledge documents."""

    def __init__(
        self,
        target_tokens: int = 512,
        max_tokens: int = 800,
        min_tokens: int = 50,
        overlap_tokens: int = 64,
    ) -> None:
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_document(
        self,
        document_id: str,
        version: int,
        title: str,
        category: DocumentCategory,
        access_level: AccessLevel,
        full_text: str,
        pages_text: list[tuple[int, str]] | None = None,
    ) -> list[KnowledgeChunk]:
        """
        Split document text into structured KnowledgeChunk items.

        pages_text: Optional list of (page_num, page_text) for PDF page tracking.
        """
        if not full_text.strip():
            return []

        # 1. Break into structural units: paragraphs and markdown tables
        raw_blocks = self._split_into_blocks(full_text)

        chunks: list[KnowledgeChunk] = []
        current_section_title: str | None = None
        current_chunk_blocks: list[str] = []
        current_chunk_tokens = 0
        current_is_table = False

        chunk_index = 0

        for block in raw_blocks:
            block = block.strip()
            if not block:
                continue

            # Detect section heading
            heading_match = re.match(r"^(#{1,4})\s+(.+)$", block)
            if heading_match:
                # Flush existing chunk before starting a major new section if it has enough tokens
                if current_chunk_tokens >= self.min_tokens:
                    chunk = self._create_chunk(
                        document_id=document_id,
                        version=version,
                        chunk_index=chunk_index,
                        title=title,
                        category=category,
                        access_level=access_level,
                        section_title=current_section_title,
                        text="\n\n".join(current_chunk_blocks),
                        is_table=current_is_table,
                        pages_text=pages_text,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                    # Reset with overlap if applicable
                    current_chunk_blocks = []
                    current_chunk_tokens = 0
                    current_is_table = False

                current_section_title = heading_match.group(2).strip()
                current_chunk_blocks.append(block)
                current_chunk_tokens += estimate_tokens(block)
                continue

            is_table_block = block.startswith("|") and ("---" in block)
            block_tokens = estimate_tokens(block)

            # If a single table block exceeds max_tokens, split it or keep it standalone
            if is_table_block and block_tokens > self.max_tokens:
                # Flush previous
                if current_chunk_blocks:
                    chunks.append(self._create_chunk(
                        document_id, version, chunk_index, title, category, access_level,
                        current_section_title, "\n\n".join(current_chunk_blocks),
                        current_is_table, pages_text
                    ))
                    chunk_index += 1
                    current_chunk_blocks = []
                    current_chunk_tokens = 0

                # Add oversized table as its own chunk
                chunks.append(self._create_chunk(
                    document_id, version, chunk_index, title, category, access_level,
                    current_section_title, block, True, pages_text
                ))
                chunk_index += 1
                continue

            # If adding this block exceeds target_tokens and we already have sufficient content
            if (current_chunk_tokens + block_tokens > self.target_tokens) and (current_chunk_tokens >= self.min_tokens):
                # Flush current chunk
                chunk_text = "\n\n".join(current_chunk_blocks)
                chunks.append(self._create_chunk(
                    document_id, version, chunk_index, title, category, access_level,
                    current_section_title, chunk_text, current_is_table, pages_text
                ))
                chunk_index += 1

                # Generate overlap words from the end of previous block if not a table
                overlap_text = ""
                if not current_is_table and self.overlap_tokens > 0:
                    words = chunk_text.split()
                    if len(words) > 20:
                        overlap_words = words[-int(self.overlap_tokens * 0.75):]
                        overlap_text = " ".join(overlap_words)

                current_chunk_blocks = [overlap_text, block] if overlap_text else [block]
                current_chunk_tokens = estimate_tokens("\n\n".join(current_chunk_blocks))
                current_is_table = is_table_block
            else:
                current_chunk_blocks.append(block)
                current_chunk_tokens += block_tokens
                if is_table_block:
                    current_is_table = True

        # Flush final chunk
        if current_chunk_blocks:
            chunk_text = "\n\n".join(current_chunk_blocks).strip()
            if chunk_text:
                chunks.append(self._create_chunk(
                    document_id, version, chunk_index, title, category, access_level,
                    current_section_title, chunk_text, current_is_table, pages_text
                ))

        return chunks

    def _split_into_blocks(self, text: str) -> list[str]:
        """Split text by double newlines while preserving markdown table bodies."""
        raw_paragraphs = text.split("\n\n")
        blocks: list[str] = []
        for p in raw_paragraphs:
            cleaned = p.strip()
            if cleaned:
                blocks.append(cleaned)
        return blocks

    def _create_chunk(
        self,
        document_id: str,
        version: int,
        chunk_index: int,
        title: str,
        category: DocumentCategory,
        access_level: AccessLevel,
        section_title: str | None,
        text: str,
        is_table: bool,
        pages_text: list[tuple[int, str]] | None,
    ) -> KnowledgeChunk:
        """Create a KnowledgeChunk with deterministic ID and metadata."""
        chunk_id = f"{document_id}_v{version}_c{chunk_index}"
        token_count = estimate_tokens(text)
        char_count = len(text)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Find matching page if page text was provided
        page_num: int | None = None
        if pages_text:
            text_snippet = text[:60].strip()
            for p_num, p_text in pages_text:
                if text_snippet and text_snippet in p_text:
                    page_num = p_num
                    break

        metadata = KnowledgeChunkMetadata(
            document_id=document_id,
            version=version,
            chunk_index=chunk_index,
            category=category,
            access_level=access_level,
            title=title,
            section_title=section_title,
            page_number=page_num,
            token_count=token_count,
            char_count=char_count,
            content_hash=content_hash,
            is_table=is_table,
        )

        return KnowledgeChunk(
            chunk_id=chunk_id,
            text=text,
            metadata=metadata,
            embedding=None,
        )
