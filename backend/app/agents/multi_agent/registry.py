"""
HospitalOps AI — Deterministic Specialist Registry (Milestone 5, Chunk 5.6.2).

Maintains authoritative registration for the four domain specialist agents:
1. Forecasting Specialist (forecasting_specialist)
2. Simulation Specialist (simulation_specialist)
3. Optimization Specialist (optimization_specialist)
4. Knowledge Specialist (knowledge_specialist)

Guarantees:
- Stable code-defined specialist IDs (no LLM-invented agents)
- Duplicate registration rejection
- Unknown specialist ID rejection
- Deterministic iteration order
- Server-side permission and tool allowlist enforcement
"""

from __future__ import annotations

import logging

from app.agents.multi_agent.contracts import (
    STANDARD_SPECIALISTS,
    SpecialistDefinition,
    SpecialistId,
)
from app.agents.multi_agent.specialists.base import BaseSpecialist

logger = logging.getLogger(__name__)

# Canonical deterministic ordering
DETERMINISTIC_SPECIALIST_ORDER: tuple[SpecialistId, ...] = (
    SpecialistId.FORECASTING,
    SpecialistId.SIMULATION,
    SpecialistId.OPTIMIZATION,
    SpecialistId.KNOWLEDGE,
)


class SpecialistRegistry:
    """
    Deterministic registry managing domain specialist agent instances.
    """

    def __init__(self) -> None:
        self._specialists: dict[SpecialistId, BaseSpecialist] = {}

    def register(self, specialist: BaseSpecialist) -> None:
        """
        Register an approved domain specialist instance.

        Raises:
            ValueError: If specialist ID is unknown, invalid, or already registered.
        """
        spec_id = specialist.specialist_id
        if not isinstance(spec_id, SpecialistId):
            try:
                spec_id = SpecialistId(spec_id)
            except ValueError:
                raise ValueError(
                    f"Cannot register specialist: '{spec_id}' is not an approved SpecialistId."
                ) from None

        if spec_id in self._specialists:
            raise ValueError(
                f"Specialist '{spec_id.value}' is already registered. Duplicate registration prohibited."
            )

        if spec_id not in STANDARD_SPECIALISTS:
            raise ValueError(
                f"Specialist '{spec_id.value}' does not exist in standard system definitions."
            )

        self._specialists[spec_id] = specialist
        logger.info(
            "Registered domain specialist: %s (domain: %s, required_permission: %s)",
            spec_id.value,
            specialist.domain.value,
            specialist.required_permissions,
        )

    def get_specialist(self, specialist_id: SpecialistId | str) -> BaseSpecialist | None:
        """
        Retrieve a registered specialist instance by ID.
        """
        key = self._resolve_id(specialist_id)
        if key is None:
            return None
        return self._specialists.get(key)

    def list_specialists(self, include_disabled: bool = True) -> list[BaseSpecialist]:
        """
        List all registered specialists in strict deterministic order.
        """
        result: list[BaseSpecialist] = []
        for spec_id in DETERMINISTIC_SPECIALIST_ORDER:
            spec = self._specialists.get(spec_id)
            if spec is not None:
                if include_disabled or spec.enabled:
                    result.append(spec)
        return result

    def get_definition(self, specialist_id: SpecialistId | str) -> SpecialistDefinition | None:
        """
        Retrieve static contract definition for a specialist.
        """
        key = self._resolve_id(specialist_id)
        if key is None:
            return None
        return STANDARD_SPECIALISTS.get(key)

    def is_enabled(self, specialist_id: SpecialistId | str) -> bool:
        """
        Check if a registered specialist is currently enabled.
        """
        spec = self.get_specialist(specialist_id)
        if spec is None:
            return False
        return spec.enabled

    def set_enabled(self, specialist_id: SpecialistId | str, enabled: bool) -> None:
        """
        Enable or disable a registered specialist.
        """
        spec = self.get_specialist(specialist_id)
        if spec is None:
            raise ValueError(f"Specialist '{specialist_id}' is not registered.")
        spec.enabled = enabled
        logger.info("Specialist '%s' enabled set to %s", spec.specialist_id.value, enabled)

    def registered_count(self) -> int:
        """Return the count of registered specialists."""
        return len(self._specialists)

    def is_fully_registered(self) -> bool:
        """Return True if all four canonical specialists are registered."""
        return all(spec_id in self._specialists for spec_id in DETERMINISTIC_SPECIALIST_ORDER)

    @staticmethod
    def _resolve_id(specialist_id: SpecialistId | str) -> SpecialistId | None:
        """Safely coerce str to SpecialistId enum or return None."""
        if isinstance(specialist_id, SpecialistId):
            return specialist_id
        try:
            return SpecialistId(specialist_id)
        except (ValueError, KeyError):
            return None
