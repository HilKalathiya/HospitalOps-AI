"""
HospitalOps AI — Grounded Answer Generator (Chunk 4.4).

Orchestrates prompt assembly, LLM completion, structured JSON decoding,
citation verification, and single-shot bounded retry if invalid citations are emitted.
"""

from __future__ import annotations

import json
import logging
import re
import time

from pydantic import ValidationError

from app.knowledge.generation.citation_validator import CitationValidator
from app.knowledge.generation.contracts import (
    AnswerStatus,
    AnswerType,
    CitationReference,
    GenerationMetadata,
    RawAnswerOutput,
)
from app.knowledge.generation.prompt_builder import (
    PROMPT_VERSION,
    build_correction_message,
    build_system_prompt,
    build_user_message,
)
from app.knowledge.generation.provider import LLMMessage, LLMProvider
from app.knowledge.retrieval.contracts import ContextBlock, RetrievalStatus, SourceCitation

logger = logging.getLogger(__name__)


class GroundedAnswerGenerator:
    """Executes grounded generation, JSON parsing, citation validation, and bounded retry."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def generate(
        self,
        query: str,
        formatted_context: str | None = None,
        available_citations: list[SourceCitation] | None = None,
        context_blocks: list[ContextBlock] | None = None,
        retrieval_status: RetrievalStatus = RetrievalStatus.SUCCESS,
        temperature: float = 0.0,
        max_output_tokens: int = 1500,
        max_sources: int | None = None,
        require_citations: bool = True,
    ) -> tuple[
        AnswerStatus,
        AnswerType,
        str,
        list[CitationReference],
        list[str],
        list[str],
        GenerationMetadata,
        str | None,
    ]:
        """
        Generate and validate a grounded operational answer.

        Returns:
            (status, answer_type, answer_text, verified_citations, limitations, follow_up_questions, metadata, status_reason)
        """
        start_time = time.perf_counter()

        if available_citations is None and context_blocks:
            from app.knowledge.retrieval.contracts import SourceCitation
            available_citations = [
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
                for b in context_blocks
            ]
        elif available_citations is None:
            available_citations = []

        if formatted_context is None and context_blocks:
            formatted_context = "\n\n".join(
                f"[{b.citation_id}] Document: {b.document_title} (v{b.document_version})\n{b.content}"
                for b in context_blocks
            )

        available_markers = [c.citation_marker for c in available_citations]

        # 1. Build Initial Messages
        system_prompt = build_system_prompt()
        user_prompt = build_user_message(
            query=query,
            formatted_context=formatted_context,
            citations=available_citations,
            retrieval_status=retrieval_status,
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        # 2. Invoke Provider
        retry_count = 0
        total_input_tokens = 0
        total_output_tokens = 0

        try:
            raw_content, usage, _ = await self.provider.generate(
                messages=messages,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            if usage:
                total_input_tokens += usage.get("prompt_tokens", 0)
                total_output_tokens += usage.get("completion_tokens", 0)
        except TimeoutError as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            meta = GenerationMetadata(
                provider=self.provider.provider_name,
                model=self.provider.model_name,
                prompt_version=PROMPT_VERSION,
                duration_ms=round(duration_ms, 2),
            )
            return (
                AnswerStatus.GENERATION_FAILED,
                AnswerType.INSUFFICIENT_EVIDENCE,
                "",
                [],
                ["Answer generation timed out."],
                [],
                meta,
                f"Model provider timed out: {exc}",
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            meta = GenerationMetadata(
                provider=self.provider.provider_name,
                model=self.provider.model_name,
                prompt_version=PROMPT_VERSION,
                duration_ms=round(duration_ms, 2),
            )
            from app.knowledge.generation.provider import NullLLMProvider
            is_unavailable = (
                isinstance(self.provider, NullLLMProvider)
                or "disabled" in str(exc).lower()
                or "unconfigured" in str(exc).lower()
            )
            status = AnswerStatus.GENERATION_UNAVAILABLE if is_unavailable else AnswerStatus.GENERATION_FAILED
            msg = f"Answer generation is currently unavailable: {exc}" if is_unavailable else ""
            return (
                status,
                AnswerType.INSUFFICIENT_EVIDENCE,
                msg,
                [],
                ["Generation provider communication failed."],
                [],
                meta,
                f"Generation provider error: {exc}",
            )

        # 3. Parse JSON Output
        parsed_output, parse_err = self._parse_raw_output(raw_content)

        # 4. If JSON parsing failed, try once more or fail
        if parse_err or parsed_output is None:
            logger.warning("Failed to parse structured JSON from LLM: %s", parse_err)
            duration_ms = (time.perf_counter() - start_time) * 1000
            meta = GenerationMetadata(
                provider=self.provider.provider_name,
                model=self.provider.model_name,
                prompt_version=PROMPT_VERSION,
                input_tokens=total_input_tokens or None,
                output_tokens=total_output_tokens or None,
                duration_ms=round(duration_ms, 2),
                retry_count=retry_count,
            )
            return (
                AnswerStatus.GENERATION_FAILED,
                AnswerType.INSUFFICIENT_EVIDENCE,
                "",
                [],
                ["Model produced malformed or unparseable structured output."],
                [],
                meta,
                f"Response decoding error: {parse_err}",
            )

        # 5. Extract and Validate Citations
        cited_markers = CitationValidator.extract_markers(parsed_output.answer)
        is_valid, invalid_markers, verified_citations = CitationValidator.validate_citations(
            cited_markers=cited_markers,
            available_citations=available_citations,
            context_blocks=context_blocks,
        )

        # 6. Bounded Single-Shot Retry on Invalid Citations
        if not is_valid and retry_count == 0:
            logger.info(
                "Invalid citation markers detected (%s); attempting 1-shot correction retry.",
                invalid_markers,
            )
            retry_count += 1
            correction_prompt = build_correction_message(invalid_markers, available_markers)
            messages.append(LLMMessage(role="assistant", content=raw_content))
            messages.append(LLMMessage(role="user", content=correction_prompt))

            try:
                retry_content, retry_usage, _ = await self.provider.generate(
                    messages=messages,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
                if retry_usage:
                    total_input_tokens += retry_usage.get("prompt_tokens", 0)
                    total_output_tokens += retry_usage.get("completion_tokens", 0)

                retry_parsed, retry_err = self._parse_raw_output(retry_content)
                if retry_parsed and not retry_err:
                    retry_cited_markers = CitationValidator.extract_markers(retry_parsed.answer)
                    retry_valid, retry_invalid, retry_verified = CitationValidator.validate_citations(
                        cited_markers=retry_cited_markers,
                        available_citations=available_citations,
                        context_blocks=context_blocks,
                    )
                    if retry_valid:
                        parsed_output = retry_parsed
                        is_valid = True
                        verified_citations = retry_verified
                        invalid_markers = []
                    else:
                        invalid_markers = retry_invalid
            except Exception as exc:
                logger.warning("Citation correction retry failed: %s", exc)

        # 7. If still invalid after retry, reject output rather than returning misleading citations
        duration_ms = (time.perf_counter() - start_time) * 1000
        meta = GenerationMetadata(
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            prompt_version=PROMPT_VERSION,
            input_tokens=total_input_tokens or None,
            output_tokens=total_output_tokens or None,
            duration_ms=round(duration_ms, 2),
            retry_count=retry_count,
        )

        if not is_valid:
            logger.error("Answer failed citation validation after retry; unknown markers: %s", invalid_markers)
            return (
                AnswerStatus.GENERATION_FAILED,
                AnswerType.INSUFFICIENT_EVIDENCE,
                "",
                [],
                [f"Answer cited nonexistent reference markers: {', '.join(invalid_markers)}."],
                [],
                meta,
                f"Citation validation rejected hallucinated markers: {', '.join(invalid_markers)}",
            )

        # 8. Determine Answer Status and Grounding Type
        limitations = list(parsed_output.limitations)
        status_reason = None

        if parsed_output.insufficient_evidence or parsed_output.answer_type == AnswerType.INSUFFICIENT_EVIDENCE:
            answer_status = AnswerStatus.INSUFFICIENT_EVIDENCE
            answer_type = AnswerType.INSUFFICIENT_EVIDENCE
            status_reason = "Available reference documents do not establish sufficient facts to answer the question."
        elif parsed_output.answer_type == AnswerType.CONFLICTING_EVIDENCE:
            answer_status = AnswerStatus.CONFLICTING_EVIDENCE
            answer_type = AnswerType.CONFLICTING_EVIDENCE
            status_reason = "Retrieved documents contain conflicting operational guidelines."
        elif parsed_output.answer_type == AnswerType.OUT_OF_SCOPE:
            answer_status = AnswerStatus.OUT_OF_SCOPE
            answer_type = AnswerType.OUT_OF_SCOPE
            status_reason = "Question falls outside operational knowledge scope."
        elif (
            retrieval_status == RetrievalStatus.PARTIAL_CONTEXT
            or parsed_output.answer_type == AnswerType.PARTIALLY_GROUNDED
        ):
            answer_status = AnswerStatus.PARTIAL_ANSWER
            answer_type = AnswerType.PARTIALLY_GROUNDED
            if retrieval_status == RetrievalStatus.PARTIAL_CONTEXT:
                limitations.append(
                    "Answer is based on partial retrieved context due to context token budget limits."
                )
            status_reason = "Answer is partially supported by available evidence."
        else:
            answer_status = AnswerStatus.ANSWERED
            answer_type = AnswerType.GROUNDED
            status_reason = "Answer generated and verified against retrieved operational references."

        return (
            answer_status,
            answer_type,
            parsed_output.answer,
            verified_citations,
            limitations,
            parsed_output.follow_up_questions,
            meta,
            status_reason,
        )

    def _parse_raw_output(self, raw_text: str) -> tuple[RawAnswerOutput | None, str | None]:
        """Clean markdown wrapping and validate structured JSON schema."""
        cleaned = raw_text.strip()
        # Strip markdown ```json ... ``` code fence if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
            parsed = RawAnswerOutput.model_validate(data)
            return parsed, None
        except json.JSONDecodeError as err:
            return None, f"JSONDecodeError: {err}"
        except ValidationError as err:
            return None, f"ValidationError: {err}"
        except Exception as err:
            return None, str(err)
