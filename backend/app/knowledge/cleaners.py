"""
HospitalOps AI — Content Cleaning & Normalization.

Cleans extracted raw text while strictly preserving clinical and operational notations:
- Unicode NFKC normalization
- Whitespace and carriage return cleanup
- Preservation of clinical measurements (e.g., "SpO2: 98%", "pH: 7.35-7.45", "<0.05", ">=90%")
- Preservation of department acronyms (ICU, ED, PACU, OR, NICU)
"""

from __future__ import annotations

import re
import unicodedata


def clean_text(raw_text: str) -> str:
    """
    Clean and normalize text from document parsers.

    Steps:
    1. Unicode NFKC normalization (replaces weird quotes, ligatures, bullet chars)
    2. Normalize line endings (CRLF -> LF)
    3. Collapse trailing spaces per line
    4. Collapse 3+ consecutive newlines to double newline
    5. Strip non-printable ASCII controls while preserving standard whitespace
    """
    if not raw_text:
        return ""

    # 1. Unicode normalization
    text = unicodedata.normalize("NFKC", raw_text)

    # 2. Line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Strip trailing/leading spaces on each line
    lines = [re.sub(r"[ \t]+$", "", line) for line in text.split("\n")]
    text = "\n".join(lines)

    # 4. Collapse runs of horizontal whitespace (spaces/tabs) to a single space
    # but do NOT collapse across newlines
    text = re.sub(r"[ \t]{2,}", " ", text)

    # 5. Collapse excessive blank lines (3 or more newlines -> 2 newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 6. Remove non-printable control characters except \n and \t
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or unicodedata.category(ch)[0] != "C")

    return text.strip()
