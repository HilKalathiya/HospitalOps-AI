"""
HospitalOps AI — Agent Safety, RBAC & Execution Policies (Milestone 5, Chunk 5.1).

Enforces:
- Clinical query screening (preserves the non-clinical boundary from AGENTS.md)
- Granular permission validation per tool invocation
- Loop and duplicate identical tool call prevention
- Output size clamping and prompt injection containment
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.tools.base import AgentTool
from app.knowledge.generation.prompt_builder import is_clinical_query

logger = logging.getLogger(__name__)

MAX_TOOL_OUTPUT_CHARS = 3500
DISCLAIMER_TEXT = (
    "Advisory Only — HospitalOps AI provides operational decision support only. "
    "This agent operates in read-only mode and does not modify real-world hospital resources "
    "or provide patient-specific clinical diagnosis or medical treatment."
)


class AgentPolicyEnforcer:
    """Centralized policy check suite for the agent execution runtime."""

    @staticmethod
    def check_clinical_scope(task: str) -> tuple[bool, str]:
        """
        Screen the user's task for clinical diagnosis, prescribing, or clinical management.
        Returns: (is_clinical, refusal_reason)
        """
        is_clinical, explanation = is_clinical_query(task)
        if is_clinical:
            logger.info("Agent task rejected by clinical safety boundary | query=%s", task[:60])
            return True, explanation
        return False, ""

    @staticmethod
    def check_tool_permission(
        user_permissions: list[str], tool: AgentTool
    ) -> tuple[bool, str | None]:
        """
        Verify that the authenticated caller holds the permission required by the tool.
        Returns: (allowed, reason_if_denied)
        """
        required = tool.required_permission
        if required not in user_permissions:
            msg = f"User lacks required permission '{required}' to invoke tool '{tool.name}'."
            logger.warning(
                "Agent tool permission denied | tool=%s required=%s", tool.name, required
            )
            return False, msg
        return True, None

    @staticmethod
    def is_duplicate_call(
        history: list[tuple[str, str]],
        tool_name: str,
        arguments: dict[str, Any],
    ) -> bool:
        """
        Detect whether an identical tool invocation with identical arguments was already executed.
        """
        serialized = json.dumps(arguments, sort_keys=True, default=str)
        call_sig = (tool_name, serialized)
        return call_sig in history

    @staticmethod
    def sanitize_and_clamp_output(raw_output: str, max_chars: int = MAX_TOOL_OUTPUT_CHARS) -> str:
        """
        Prevent context explosion by bounding output size and wrapping untrusted data in safe tags.
        """
        clean = raw_output.replace("</tool_output>", "&lt;/tool_output&gt;")
        if len(clean) > max_chars:
            clean = clean[:max_chars] + f"\n... [Output truncated after {max_chars} characters]"
        return f"<tool_output>\n{clean}\n</tool_output>"
