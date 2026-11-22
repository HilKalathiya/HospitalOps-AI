"""
HospitalOps AI — Multi-Agent Aggregator (Milestone 5, Chunk 5.6.3).

Synthesizes evidence from multiple domain specialists into a unified AggregatedSpecialistResult.
Enforces epistemic integrity (never confusing observed data, forecasts, simulations,
optimization proposals, or knowledge policies), detects domain contradictions, and handles
partial failure gracefully while preserving the non-negotiable human review requirement.
"""

from __future__ import annotations

import logging
import re

from app.agents.contracts import ProvenanceItem
from app.agents.evidence import AgentEvidence, EvidenceCategory
from app.agents.multi_agent.contracts import (
    AggregatedSpecialistResult,
    AggregationStatus,
    SpecialistExecutionStatus,
    SpecialistId,
    SpecialistResult,
)
from app.knowledge.generation.contracts import CitationReference
from app.models.base import utc_now

logger = logging.getLogger(__name__)

# Expected epistemic mapping per specialist
SPECIALIST_EPISTEMIC_MAP: dict[SpecialistId, EvidenceCategory] = {
    SpecialistId.FORECASTING: EvidenceCategory.FORECAST,
    SpecialistId.SIMULATION: EvidenceCategory.SIMULATION,
    SpecialistId.OPTIMIZATION: EvidenceCategory.OPTIMIZATION,
    SpecialistId.KNOWLEDGE: EvidenceCategory.KNOWLEDGE_POLICY,
}

# Polarity keywords for cross-domain inconsistency detection
SHORTAGE_INDICATORS = (
    "shortage",
    "deficit",
    "capacity exceeded",
    "critical surge",
    "over capacity",
    "insufficient beds",
    "unmet demand",
    "exhausted",
)

SURPLUS_INDICATORS = (
    "surplus",
    "adequate capacity",
    "under capacity",
    "sufficient beds",
    "ample capacity",
    "within normal limits",
    "available headroom",
)


class MultiAgentAggregator:
    """
    Synthesizes and cross-references multi-agent operational evidence.
    """

    def aggregate(
        self,
        parent_execution_id: str,
        plan_id: str,
        results: list[SpecialistResult],
        duration_ms: float = 0.0,
    ) -> AggregatedSpecialistResult:
        """
        Aggregate individual specialist results into a consolidated package.

        1. Categorize successful vs unsuccessful contributors.
        2. Enforce epistemic categorization on all returned evidence.
        3. Deduplicate evidence, provenance, and citations.
        4. Detect domain contradictions and operational discrepancies.
        5. Assign overall aggregation status and healthcare safety flags.
        """
        if not results:
            logger.warning(
                "Aggregator received empty results list | parent_id=%s plan_id=%s",
                parent_execution_id,
                plan_id,
            )
            return AggregatedSpecialistResult(
                parent_execution_id=parent_execution_id,
                plan_id=plan_id,
                status=AggregationStatus.NO_RESULTS,
                is_partial_result=False,
                specialist_results=[],
                successful_contributors=[],
                unsuccessful_contributors=[],
                conflicts_or_inconsistencies=[],
                aggregated_evidence=[],
                all_evidence_ids=[],
                all_provenance=[],
                all_citations=[],
                duration_ms=max(0.0, float(duration_ms)),
                requires_human_review=True,
                aggregated_at=utc_now(),
            )

        successful_contributors: list[SpecialistId] = []
        unsuccessful_contributors: list[SpecialistId] = []

        seen_evidence_ids: set[str] = set()
        aggregated_evidence: list[AgentEvidence] = []
        all_evidence_ids: list[str] = []

        seen_provenance: set[tuple[str, str]] = set()
        all_provenance: list[ProvenanceItem] = []

        seen_citations: set[tuple[str, str | None]] = set()
        all_citations: list[CitationReference] = []

        for res in results:
            if res.status == SpecialistExecutionStatus.COMPLETED:
                successful_contributors.append(res.specialist_id)

                # Process evidence
                expected_category = SPECIALIST_EPISTEMIC_MAP.get(
                    res.specialist_id, res.epistemic_category
                )

                for ev in res.evidence:
                    if ev.evidence_id not in seen_evidence_ids:
                        seen_evidence_ids.add(ev.evidence_id)
                        # Ensure epistemic boundary integrity (prevent projections relabeled as facts)
                        if ev.category != expected_category and ev.category == EvidenceCategory.OBSERVED_DATA:
                            logger.warning(
                                "Correcting mislabeled evidence category | evidence_id=%s original=%s corrected=%s",
                                ev.evidence_id,
                                ev.category,
                                expected_category,
                            )
                            ev.category = expected_category

                        aggregated_evidence.append(ev)

                for ev_id in res.evidence_ids:
                    if ev_id not in all_evidence_ids:
                        all_evidence_ids.append(ev_id)

                # Collect provenance
                for prov in res.provenance:
                    prov_key = (prov.category, prov.id)
                    if prov_key not in seen_provenance:
                        seen_provenance.add(prov_key)
                        all_provenance.append(prov)

                # Collect citations
                for cite in res.citations:
                    cite_key = (cite.document_id, cite.chunk_id)
                    if cite_key not in seen_citations:
                        seen_citations.add(cite_key)
                        all_citations.append(cite)
            else:
                unsuccessful_contributors.append(res.specialist_id)

        # Detect cross-specialist contradictions
        conflicts = self._detect_inconsistencies(results)

        # Determine overall aggregation status
        total_count = len(results)
        success_count = len(successful_contributors)

        if success_count == total_count:
            status = AggregationStatus.COMPLETED
            is_partial = False
        elif success_count > 0:
            status = AggregationStatus.PARTIAL_SUCCESS
            is_partial = True
        else:
            status = AggregationStatus.FAILED
            is_partial = False

        logger.info(
            "Aggregated multi-agent results | parent_id=%s status=%s successful=%d unsuccessful=%d conflicts=%d",
            parent_execution_id,
            status.value,
            len(successful_contributors),
            len(unsuccessful_contributors),
            len(conflicts),
        )

        return AggregatedSpecialistResult(
            parent_execution_id=parent_execution_id,
            plan_id=plan_id,
            status=status,
            is_partial_result=is_partial,
            specialist_results=results,
            successful_contributors=successful_contributors,
            unsuccessful_contributors=unsuccessful_contributors,
            conflicts_or_inconsistencies=conflicts,
            aggregated_evidence=aggregated_evidence,
            all_evidence_ids=all_evidence_ids,
            all_provenance=all_provenance,
            all_citations=all_citations,
            duration_ms=max(0.0, float(duration_ms)),
            requires_human_review=True,
            aggregated_at=utc_now(),
        )

    def _detect_inconsistencies(self, results: list[SpecialistResult]) -> list[str]:
        """
        Scan completed specialist findings for domain contradictions.

        Checks:
        1. Conflicting occupancy / capacity metrics between Forecasting and Simulation.
        2. Polarity divergence (shortage vs surplus) across findings.
        3. SOP policy requirements versus optimization solution trade-offs.
        """
        completed_results = [
            r for r in results if r.status == SpecialistExecutionStatus.COMPLETED
        ]
        if len(completed_results) < 2:
            return []

        conflicts: list[str] = []

        results_by_id = {
            r.specialist_id.value if hasattr(r.specialist_id, "value") else str(r.specialist_id): r
            for r in completed_results
        }

        forecast_res = results_by_id.get(SpecialistId.FORECASTING.value)
        sim_res = results_by_id.get(SpecialistId.SIMULATION.value)
        opt_res = results_by_id.get(SpecialistId.OPTIMIZATION.value)
        know_res = results_by_id.get(SpecialistId.KNOWLEDGE.value)

        # 1. Forecast vs Simulation Capacity Divergence
        if forecast_res and sim_res:
            forecast_metrics = self._extract_occupancy_metrics(forecast_res)
            sim_metrics = self._extract_occupancy_metrics(sim_res)

            common_depts = set(forecast_metrics.keys()) & set(sim_metrics.keys())
            for dept in common_depts:
                f_val = forecast_metrics[dept]
                s_val = sim_metrics[dept]
                # If values differ by more than 20 percentage points or 20 beds
                if abs(f_val - s_val) >= 20.0:
                    conflicts.append(
                        f"Divergence detected in department '{dept}': Forecasting projected "
                        f"{f_val:.1f}% occupancy while Simulation projected {s_val:.1f}%."
                    )

        # 2. Polarity Contradiction (Shortage vs Surplus)
        shortage_specialists: list[str] = []
        surplus_specialists: list[str] = []

        for r in completed_results:
            text = (r.summary + " " + " ".join(e.summary for e in r.evidence)).lower()
            has_shortage = any(term in text for term in SHORTAGE_INDICATORS)
            has_surplus = any(term in text for term in SURPLUS_INDICATORS)

            spec_str = (
                r.specialist_id.value
                if hasattr(r.specialist_id, "value")
                else str(r.specialist_id)
            )
            if has_shortage and not has_surplus:
                shortage_specialists.append(spec_str)
            elif has_surplus and not has_shortage:
                surplus_specialists.append(spec_str)

        if shortage_specialists and surplus_specialists:
            conflicts.append(
                f"Operational polarity conflict: {', '.join(shortage_specialists)} identified a bed/resource "
                f"shortage, whereas {', '.join(surplus_specialists)} concluded adequate capacity or surplus."
            )

        # 3. Knowledge Policy vs Optimization Constraints
        if know_res and opt_res:
            know_text = (know_res.summary + " " + " ".join(e.summary for e in know_res.evidence)).lower()
            opt_text = (opt_res.summary + " " + " ".join(e.summary for e in opt_res.evidence)).lower()

            # Check if policy mentions mandatory reserve beds and optimization reports 0 reserve / 100% allocation
            if ("reserve" in know_text or "buffer" in know_text or "contingency" in know_text) and (
                "100%" in opt_text or "zero reserve" in opt_text or "unmet demand" in opt_text
            ):
                conflicts.append(
                    "Policy alignment notice: Knowledge policies recommend reserve/buffer bed maintenance, "
                    "whereas the Optimization schedule proposes near-total or complete bed capacity utilization."
                )

        return conflicts

    def _extract_occupancy_metrics(self, result: SpecialistResult) -> dict[str, float]:
        """
        Extract numeric occupancy metrics by department from evidence data and summaries.
        """
        metrics: dict[str, float] = {}

        # Look in structured evidence first
        for ev in result.evidence:
            data = ev.data or {}
            dept = str(data.get("department_id") or data.get("department") or "general").lower()

            if "predicted_occupancy_rate" in data:
                metrics[dept] = float(data["predicted_occupancy_rate"])
            elif "occupancy_rate" in data:
                metrics[dept] = float(data["occupancy_rate"])
            elif "occupancy_percentage" in data:
                metrics[dept] = float(data["occupancy_percentage"])
            elif "peak_occupancy" in data:
                metrics[dept] = float(data["peak_occupancy"])

        # Fallback to regex in summary if not in data dict
        if not metrics:
            matches = re.findall(r"([A-Za-z0-9_-]+)\s+occupancy\s*(?:at|of|:)?\s*(\d+(?:\.\d+)?)\s*%", result.summary, re.IGNORECASE)
            for dept, val in matches:
                metrics[dept.lower()] = float(val)

        return metrics
