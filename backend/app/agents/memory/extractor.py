"""
HospitalOps AI — Agent Memory Candidate Extractor (Milestone 5, Chunk 5.5).

Analyzes user turns and assistant responses for explicit user operational preferences,
reporting habits, or hospital operational context.
Proposes safe, bounded memory candidates in PENDING_APPROVAL status.
"""

from __future__ import annotations

import json
import logging
import re

from app.agents.memory.policy import AgentMemoryPolicy, sanitize_memory_key
from app.knowledge.generation.provider import LLMProvider
from app.models.agent_memory import AgentMemoryCandidateCreate, MemoryCategory

logger = logging.getLogger(__name__)

# Explicit heuristic cues indicating user preference or persistent operational context
PREFERENCE_CUES = [
    re.compile(r"\b(?:remember\s+(?:that\s+)?|please\s+remember\s+(?:that\s+)?)(.+)", re.IGNORECASE),
    re.compile(r"\b(?:always\s+include|always\s+format|always\s+show|always\s+provide)\s+(.+)", re.IGNORECASE),
    re.compile(r"\bfor\s+future\s+(?:sessions|reports|analyses|queries|tasks),?\s*(.+)", re.IGNORECASE),
    re.compile(r"\bmy\s+(?:reporting\s+)?preference\s+is\s+(.+)", re.IGNORECASE),
    re.compile(r"\bi\s+prefer\s+(.+)", re.IGNORECASE),
    re.compile(r"\bin\s+our\s+hospital,?\s*(.+)", re.IGNORECASE),
    re.compile(r"\bour\s+standard\s+(?:planning\s+horizon|reporting\s+format)\s+is\s+(.+)", re.IGNORECASE),
]


class AgentMemoryExtractor:
    """
    Extracts structured memory candidates from conversational turns.
    Combines deterministic regex heuristics with structured LLM extraction.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    async def extract_candidates(
        self,
        user_message: str,
        assistant_message: str = "",
        session_id: str | None = None,
        message_id: str | None = None,
    ) -> list[AgentMemoryCandidateCreate]:
        """
        Analyze user message for persistent operational preference cues.
        Validates all candidates against AgentMemoryPolicy before returning.
        """
        candidates: list[AgentMemoryCandidateCreate] = []
        user_clean = user_message.strip()
        if not user_clean:
            return candidates

        # 1. Deterministic Heuristic Extraction
        heuristic_candidate = self._extract_heuristic(user_clean)
        if heuristic_candidate:
            is_valid, reason, _ = AgentMemoryPolicy.validate_memory_candidate(
                category=heuristic_candidate.category,
                key=heuristic_candidate.key,
                value=heuristic_candidate.value,
                summary=heuristic_candidate.summary,
            )
            if is_valid:
                if session_id:
                    heuristic_candidate.source_session_id = session_id
                if message_id:
                    heuristic_candidate.source_message_ids = [message_id]
                candidates.append(heuristic_candidate)
            else:
                logger.info("Heuristic candidate rejected by memory policy: %s", reason)

        # 2. LLM-Assisted Structured Extraction (if provider available and no candidate found yet)
        if not candidates and self.provider:
            try:
                llm_candidates = await self._extract_with_llm(
                    user_clean, session_id=session_id, message_id=message_id
                )
                for cand in llm_candidates:
                    is_valid, reason, _ = AgentMemoryPolicy.validate_memory_candidate(
                        category=cand.category,
                        key=cand.key,
                        value=cand.value,
                        summary=cand.summary,
                    )
                    if is_valid:
                        candidates.append(cand)
                    else:
                        logger.info("LLM candidate rejected by memory policy: %s", reason)
            except Exception as e:
                logger.warning("LLM-assisted memory extraction failed (graceful skip): %s", e)

        return candidates

    def _extract_heuristic(self, text: str) -> AgentMemoryCandidateCreate | None:
        """
        Scan text for direct preference statements using compiled regex heuristics.
        """
        lower_text = text.lower()

        # Check for explicit preference keywords
        for cue in PREFERENCE_CUES:
            match = cue.search(text)
            if match:
                raw_pref = match.group(0).strip()
                # Categorize based on keywords
                if any(k in lower_text for k in ["table", "format", "chart", "layout", "visual", "markdown"]):
                    category = MemoryCategory.WORKFLOW_PREFERENCE
                    key = "report_formatting_preference"
                    summary = f"User preference for presentation format: {raw_pref[:80]}"
                elif any(k in lower_text for k in ["horizon", "threshold", "icu", "ward", "department", "unit"]):
                    category = MemoryCategory.EXPLICIT_USER_CONTEXT
                    key = "operational_focus_context"
                    summary = f"User stated operational context: {raw_pref[:80]}"
                else:
                    category = MemoryCategory.USER_PREFERENCE
                    key = "operational_user_preference"
                    summary = f"User preference: {raw_pref[:80]}"

                return AgentMemoryCandidateCreate(
                    category=category,
                    key=sanitize_memory_key(key),
                    value=text.strip(),
                    summary=summary.strip(),
                    metadata={"extraction_method": "deterministic_heuristic"},
                )

        return None

    async def _extract_with_llm(
        self,
        user_text: str,
        session_id: str | None = None,
        message_id: str | None = None,
    ) -> list[AgentMemoryCandidateCreate]:
        """
        Ask LLM provider to detect if the user explicitly stated a persistent operational preference.
        """
        if not self.provider:
            return []

        # Fast skip: if text does not contain any hint of personal preference or instruction
        hint_words = ["prefer", "always", "remember", "never", "format", "focus", "standard", "note that"]
        if not any(w in user_text.lower() for w in hint_words):
            return []

        prompt = f"""You are an operational memory extractor for HospitalOps AI.
Evaluate whether the user's message expresses an EXPLICIT, PERSISTENT OPERATIONAL PREFERENCE or CONTEXT (e.g., preferred report format, department focus, planning horizon).
If the message is simply an operational question (e.g., "What is the ICU forecast?"), return an empty list.

STRICT SAFETY:
- Do NOT extract Protected Health Information (PHI), patient IDs, or medical diagnoses.
- Do NOT extract system access or permission claims.

User Message:
\"\"\"{user_text}\"\"\"

Respond strictly with a JSON object in this format:
{{
  "has_preference": true,
  "candidates": [
    {{
      "category": "USER_PREFERENCE" | "WORKFLOW_PREFERENCE" | "EXPLICIT_USER_CONTEXT",
      "key": "short_snake_case_key",
      "value": "Full preference statement",
      "summary": "Concise 1-sentence summary"
    }}
  ]
}}
If no preference is stated, return {{"has_preference": false, "candidates": []}}.
"""
        response_text = await self.provider.generate(
            prompt=prompt,
            system_prompt="You are a JSON-only extraction engine. Output valid JSON only.",
            max_tokens=400,
            temperature=0.0,
        )

        candidates: list[AgentMemoryCandidateCreate] = []
        try:
            # Parse JSON
            raw_json = response_text.strip()
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:]
            if raw_json.startswith("```"):
                raw_json = raw_json[3:]
            if raw_json.endswith("```"):
                raw_json = raw_json[:-3]
            data = json.loads(raw_json.strip())

            if data.get("has_preference") and data.get("candidates"):
                for item in data["candidates"]:
                    cat_str = item.get("category", "USER_PREFERENCE")
                    category = (
                        MemoryCategory(cat_str)
                        if cat_str in MemoryCategory.__members__.values()
                        else MemoryCategory.USER_PREFERENCE
                    )
                    candidates.append(
                        AgentMemoryCandidateCreate(
                            category=category,
                            key=sanitize_memory_key(item.get("key", "user_preference")),
                            value=item.get("value", user_text)[:2000],
                            summary=item.get("summary", "User operational preference")[:500],
                            source_session_id=session_id,
                            source_message_ids=[message_id] if message_id else [],
                            metadata={"extraction_method": "llm_structured"},
                        )
                    )
        except Exception as err:
            logger.debug("Could not parse LLM extraction JSON: %s (Raw: %s)", err, response_text[:100])

        return candidates
