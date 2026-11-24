"""
HospitalOps AI — Operational Rule Engine Exceptions (Milestone 6, Chunk 6.2).

Defines exception types for rule validation, condition evaluation, versioning,
persistence, and execution safety.
"""

from __future__ import annotations


class RuleEngineError(Exception):
    """Base exception for all operational rule engine errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RuleValidationError(RuleEngineError):
    """Raised when a rule definition, condition tree, or operator fails validation."""


class RuleEvaluationError(RuleEngineError):
    """Raised when rule evaluation encounters an unrecoverable runtime error."""


class RuleNotFoundError(RuleEngineError):
    """Raised when a requested rule ID or version cannot be found."""


class RuleConflictError(RuleEngineError):
    """Raised when an attempt to create or update a rule conflicts with existing state."""


class RulePersistenceError(RuleEngineError):
    """Raised when saving, updating, or querying rules or evaluations fails."""
