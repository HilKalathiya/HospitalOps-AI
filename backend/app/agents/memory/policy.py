"""
HospitalOps AI — Agent Memory Policy & Validation Boundary (Milestone 5, Chunk 5.5).

Enforces strict healthcare safety, privacy, credential scanning, and anti-injection
rules before any proposed memory or preference can be created or approved.
"""

from __future__ import annotations

import logging
import re

from app.knowledge.generation.prompt_builder import is_clinical_query
from app.knowledge.privacy import scan_privacy_and_access
from app.models.agent_memory import MemoryCategory

logger = logging.getLogger(__name__)

# Patterns detecting API keys, JWT tokens, credentials, and passwords
CREDENTIAL_PATTERNS = [
    re.compile(r"\bBearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),  # JWT
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|auth[_-]?token)[\s:=]+[A-Za-z0-9_\-]{16,}\b", re.IGNORECASE),
    re.compile(r"\b(?:password|passwd|secret_key|client_secret)[\s:=]+[^\s]{6,}\b", re.IGNORECASE),
]

# Patterns detecting prompt injection, instruction override, or system jailbreaks
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?prior\s+(?:guidelines|rules|instructions)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:unconstrained|in\s+developer\s+mode|dan)", re.IGNORECASE),
    re.compile(r"system\s+prompt\s*:\s*", re.IGNORECASE),
    re.compile(r"override\s+(?:system|safety|security)\s+(?:rules|policies)", re.IGNORECASE),
    re.compile(r"<system_message>", re.IGNORECASE),
]

# Patterns detecting unauthorized privilege escalation or fake authorization claims
RBAC_SPOOFING_PATTERNS = [
    re.compile(r"\b(?:role\s+is\s+admin|grant\s+admin|bypass\s+rbac|elevate\s+permission)\b", re.IGNORECASE),
    re.compile(r"\b(?:user\s+has\s+root|allow\s+all\s+actions|override\s+permissions)\b", re.IGNORECASE),
    re.compile(r"\bexecute\s+unauthorized\s+write\b", re.IGNORECASE),
]


def sanitize_memory_key(raw_key: str) -> str:
    """
    Normalize key into a clean snake_case slug suitable for programmatic indexing.
    e.g., 'ICU Report Format' -> 'icu_report_format'
    """
    clean = raw_key.strip().lower()
    clean = re.sub(r"[^\w\s-]", "", clean)
    clean = re.sub(r"[\s-]+", "_", clean)
    clean = clean.strip("_")
    return clean[:100] or "custom_preference"


class AgentMemoryPolicy:
    """
    Deterministic validator enforcing privacy, healthcare boundaries,
    and anti-injection rules for persistent agent memory.
    """

    @classmethod
    def validate_memory_candidate(
        cls,
        category: MemoryCategory | str,
        key: str,
        value: str,
        summary: str,
    ) -> tuple[bool, str | None, list[str]]:
        """
        Validate proposed memory candidate against all system policies.

        Returns:
            (is_valid, rejection_reason, detected_violations)
        """
        violations: list[str] = []

        # 1. Structural & Boundary checks
        if not key or len(key.strip()) < 2:
            violations.append("Key must be at least 2 characters long.")
        elif len(key) > 100:
            violations.append("Key exceeds maximum length of 100 characters.")

        if not value or len(value.strip()) < 2:
            violations.append("Value must be at least 2 characters long.")
        elif len(value) > 2000:
            violations.append("Value exceeds maximum length of 2000 characters.")

        if not summary or len(summary.strip()) < 2:
            violations.append("Summary must be at least 2 characters long.")
        elif len(summary) > 500:
            violations.append("Summary exceeds maximum length of 500 characters.")

        # Ensure valid category
        valid_cats = {c.value for c in MemoryCategory}
        cat_str = category.value if hasattr(category, "value") else str(category)
        if cat_str not in valid_cats:
            violations.append(f"Invalid memory category '{cat_str}'. Must be one of: {sorted(valid_cats)}")

        combined_text = f"{key} {value} {summary}"

        # 2. Healthcare Privacy & PHI Scan
        privacy_result = scan_privacy_and_access(combined_text)
        if not privacy_result.is_safe:
            for pat in privacy_result.detected_patterns:
                violations.append(f"Prohibited PHI or patient identifier detected: {pat}")

        # 3. Healthcare Safety & Clinical Query Scan
        is_clinical, clinical_reason = is_clinical_query(combined_text)
        if is_clinical:
            violations.append(f"Clinical diagnosis/treatment content prohibited: {clinical_reason}")

        # 4. Credential & Secret Scan
        for pat in CREDENTIAL_PATTERNS:
            if pat.search(combined_text):
                violations.append("Potential secret, password, or API key detected in memory content.")
                break

        # 5. Prompt Injection & Instruction Hijack Scan
        for pat in PROMPT_INJECTION_PATTERNS:
            if pat.search(combined_text):
                violations.append("Prompt injection or instruction override attempt detected.")
                break

        # 6. Privilege Escalation & RBAC Spoofing Scan
        for pat in RBAC_SPOOFING_PATTERNS:
            if pat.search(combined_text):
                violations.append("Unauthorized RBAC claim or privilege escalation attempt detected.")
                break

        if violations:
            reason = "; ".join(violations)
            logger.warning("Agent memory policy validation failed: %s", reason)
            return False, reason, violations

        return True, None, []
