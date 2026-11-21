"""
HospitalOps AI — Healthcare Privacy & Operational Boundary Validation.

Strictly verifies that knowledge documents do NOT contain Protected Health
Information (PHI) or raw patient-level identifiers (such as MIMIC-IV patient keys).
Knowledge documents must only represent operational policies, guidelines, SOPs,
and technical reference materials.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


class PrivacyValidationResult(BaseModel):
    """Result of privacy scan across document text."""

    is_safe: bool = True
    quarantined: bool = False
    quarantine_reason: str | None = None
    detected_patterns: list[str] = Field(default_factory=list)
    violation_count: int = 0


# Compiled regex patterns for PHI and clinical patient keys
PHI_PATTERNS: dict[str, re.Pattern[str]] = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "MRN_EXPLICIT": re.compile(r"\b(?:MRN|Medical Record Number|Patient ID)[\s:#]+[A-Z0-9-]{6,12}\b", re.IGNORECASE),
    "MIMIC_HADM": re.compile(r"\bhadm_id[\s:=]+[0-9]{4,10}\b", re.IGNORECASE),
    "MIMIC_SUBJECT": re.compile(r"\bsubject_id[\s:=]+[0-9]{4,10}\b", re.IGNORECASE),
    "MIMIC_STAY": re.compile(r"\bstay_id[\s:=]+[0-9]{4,10}\b", re.IGNORECASE),
    "PHONE_US": re.compile(r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "PATIENT_DOB": re.compile(r"\b(?:DOB|Date of Birth)[\s:#]+(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b", re.IGNORECASE),
}


def scan_privacy_and_access(text: str) -> PrivacyValidationResult:
    """
    Scan text for prohibited PHI and raw patient identifiers.

    If prohibited clinical records or PHI patterns are detected, the document
    is quarantined and must not be indexed into public/operational knowledge vectors.
    """
    detected: list[str] = []
    total_violations = 0

    for name, pattern in PHI_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            detected.append(f"{name} ({len(matches)} instance(s))")
            total_violations += len(matches)

    if detected:
        reason = (
            f"Document rejected/quarantined by Healthcare Privacy Boundary. "
            f"Detected sensitive patient/PHI patterns: {', '.join(detected)}. "
            f"Operational knowledge base cannot store individual patient charts or identifiers."
        )
        return PrivacyValidationResult(
            is_safe=False,
            quarantined=True,
            quarantine_reason=reason,
            detected_patterns=detected,
            violation_count=total_violations,
        )

    return PrivacyValidationResult(
        is_safe=True,
        quarantined=False,
        quarantine_reason=None,
        detected_patterns=[],
        violation_count=0,
    )
