"""
HospitalOps AI — Declarative Rule Evaluator (Milestone 6, Chunk 6.2).

Executes safe, deterministic evaluation of declarative conditions against
OperationalEvent objects.
Guarantees:
- Pure Python AST-like evaluation (strictly zero eval, exec, or dynamic code execution).
- Non-clinical scope preservation.
- Explicit missing-data classification (never silently assumes zero or normal).
- Evidence traceability for all evaluated conditions.
"""

from __future__ import annotations

import logging
from typing import Any

from app.events.contracts import OperationalEvent, _enum_str
from app.models.base import utc_now
from app.rules.contracts import (
    CompositeCondition,
    OperationalRule,
    RuleEvaluationRecord,
    RuleEvaluationStatus,
    SingleCondition,
    compute_evaluation_id,
)

logger = logging.getLogger(__name__)

# Unique sentinel to differentiate missing field from None value
_MISSING = object()


def resolve_field_value(event: OperationalEvent, field_path: str) -> Any:
    """
    Safely extract field value from an OperationalEvent using dot-notation.
    Supports envelope fields, payload fields, and metadata fields.

    Returns:
        The extracted value, or _MISSING if the path does not exist.
    """
    parts = field_path.split(".")
    root = parts[0]

    # 1. Resolve root object
    if root == "payload":
        current = event.payload
        remaining = parts[1:]
    elif root == "metadata":
        current = event.metadata
        remaining = parts[1:]
    elif hasattr(event, root):
        current = getattr(event, root)
        remaining = parts[1:]
    else:
        return _MISSING

    # 2. Traverse remaining path
    for part in remaining:
        if current is None or current is _MISSING:
            return _MISSING
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return _MISSING
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return _MISSING

    # Normalize enums to their raw string values for safe comparisons
    if hasattr(current, "value"):
        return current.value
    return current


def evaluate_single_condition(
    condition: SingleCondition,
    event: OperationalEvent,
) -> tuple[RuleEvaluationStatus, str, dict[str, Any]]:
    """
    Evaluate an atomic SingleCondition against an OperationalEvent.

    Returns:
        tuple[RuleEvaluationStatus, str, dict[str, Any]]:
            (status, explanation, evidence_dict)
    """
    field_val = resolve_field_value(event, condition.field)
    target_val = condition.value
    if hasattr(target_val, "value"):
        target_val = target_val.value

    op = condition.operator.value if hasattr(condition.operator, "value") else str(condition.operator)

    evidence = {
        "field": condition.field,
        "operator": op,
        "observed_value": field_val if field_val is not _MISSING else None,
        "target_value": target_val,
    }

    # 1. Existence operators
    if op == "exists":
        exists = field_val is not _MISSING and field_val is not None
        status = RuleEvaluationStatus.MATCHED if exists else RuleEvaluationStatus.NOT_MATCHED
        explanation = f"Field '{condition.field}' exists" if exists else f"Field '{condition.field}' does not exist"
        return status, explanation, evidence

    if op == "does_not_exist":
        missing = field_val is _MISSING or field_val is None
        status = RuleEvaluationStatus.MATCHED if missing else RuleEvaluationStatus.NOT_MATCHED
        explanation = f"Field '{condition.field}' is absent" if missing else f"Field '{condition.field}' is present"
        return status, explanation, evidence

    # 2. For all other operators, missing field is classified as DATA_MISSING
    if field_val is _MISSING:
        explanation = f"Required field '{condition.field}' is missing from event"
        return RuleEvaluationStatus.DATA_MISSING, explanation, evidence

    if field_val is None:
        explanation = f"Field '{condition.field}' has null value; cannot evaluate comparison"
        return RuleEvaluationStatus.DATA_MISSING, explanation, evidence

    # 3. Membership operators
    if op == "in":
        target_set = target_val if isinstance(target_val, list | tuple | set) else [target_val]
        matched = field_val in target_set
        explanation = (
            f"Observed value '{field_val}' is in target set"
            if matched
            else f"Observed value '{field_val}' not in target set"
        )
        status = RuleEvaluationStatus.MATCHED if matched else RuleEvaluationStatus.NOT_MATCHED
        return status, explanation, evidence

    if op == "not_in":
        target_set = target_val if isinstance(target_val, list | tuple | set) else [target_val]
        matched = field_val not in target_set
        explanation = (
            f"Observed value '{field_val}' is not in target set"
            if matched
            else f"Observed value '{field_val}' unexpectedly in target set"
        )
        status = RuleEvaluationStatus.MATCHED if matched else RuleEvaluationStatus.NOT_MATCHED
        return status, explanation, evidence

    # 4. Equality operators
    if op == "eq":
        matched = field_val == target_val
        explanation = (
            f"'{condition.field}' ({field_val}) equals target ({target_val})"
            if matched
            else f"'{condition.field}' ({field_val}) != target ({target_val})"
        )
        status = RuleEvaluationStatus.MATCHED if matched else RuleEvaluationStatus.NOT_MATCHED
        return status, explanation, evidence

    if op == "neq":
        matched = field_val != target_val
        explanation = (
            f"'{condition.field}' ({field_val}) does not equal target ({target_val})"
            if matched
            else f"'{condition.field}' ({field_val}) == target ({target_val})"
        )
        status = RuleEvaluationStatus.MATCHED if matched else RuleEvaluationStatus.NOT_MATCHED
        return status, explanation, evidence

    # 5. Relational operators (require numeric or comparable types)
    try:
        f_num = float(field_val)
        t_num = float(target_val)
    except (ValueError, TypeError):
        explanation = (
            f"Cannot perform numeric comparison '{op}' on non-numeric types: "
            f"observed={type(field_val).__name__}, target={type(target_val).__name__}"
        )
        return RuleEvaluationStatus.DATA_MISSING, explanation, evidence

    if op == "gt":
        matched = f_num > t_num
        op_str = ">"
    elif op == "gte":
        matched = f_num >= t_num
        op_str = ">="
    elif op == "lt":
        matched = f_num < t_num
        op_str = "<"
    elif op == "lte":
        matched = f_num <= t_num
        op_str = "<="
    else:
        return RuleEvaluationStatus.ERROR, f"Unsupported operator '{op}'", evidence

    status = RuleEvaluationStatus.MATCHED if matched else RuleEvaluationStatus.NOT_MATCHED
    explanation = (
        f"'{condition.field}' ({f_num}) {op_str} threshold ({t_num}): {matched}"
    )
    return status, explanation, evidence


def evaluate_condition_tree(
    condition: SingleCondition | CompositeCondition,
    event: OperationalEvent,
) -> tuple[RuleEvaluationStatus, str, list[dict[str, Any]]]:
    """
    Recursively evaluate condition tree (SingleCondition or CompositeCondition).

    Returns:
        tuple[RuleEvaluationStatus, str, list[dict[str, Any]]]:
            (overall_status, overall_explanation, list_of_evidences)
    """
    if isinstance(condition, SingleCondition):
        st, exp, ev = evaluate_single_condition(condition, event)
        return st, exp, [ev]

    # Composite condition
    child_statuses: list[RuleEvaluationStatus] = []
    child_explanations: list[str] = []
    all_evidences: list[dict[str, Any]] = []

    for child in condition.conditions:
        st, exp, ev_list = evaluate_condition_tree(child, event)
        child_statuses.append(st)
        child_explanations.append(exp)
        all_evidences.extend(ev_list)

    lop = condition.operator.value if hasattr(condition.operator, "value") else str(condition.operator)
    if lop == "AND":
        if any(st == RuleEvaluationStatus.ERROR for st in child_statuses):
            return (
                RuleEvaluationStatus.ERROR,
                f"AND condition error: {'; '.join(child_explanations)}",
                all_evidences,
            )
        if any(st == RuleEvaluationStatus.NOT_MATCHED for st in child_statuses):
            return (
                RuleEvaluationStatus.NOT_MATCHED,
                f"AND condition not satisfied: {'; '.join(child_explanations)}",
                all_evidences,
            )
        if any(st == RuleEvaluationStatus.DATA_MISSING for st in child_statuses):
            return (
                RuleEvaluationStatus.DATA_MISSING,
                f"AND condition has missing data: {'; '.join(child_explanations)}",
                all_evidences,
            )
        # All matched
        return (
            RuleEvaluationStatus.MATCHED,
            f"AND condition fully satisfied: {'; '.join(child_explanations)}",
            all_evidences,
        )

    elif lop == "OR":
        if any(st == RuleEvaluationStatus.MATCHED for st in child_statuses):
            return (
                RuleEvaluationStatus.MATCHED,
                f"OR condition satisfied: {'; '.join(child_explanations)}",
                all_evidences,
            )
        if any(st == RuleEvaluationStatus.DATA_MISSING for st in child_statuses):
            return (
                RuleEvaluationStatus.DATA_MISSING,
                f"OR condition has missing data and no branches matched: {'; '.join(child_explanations)}",
                all_evidences,
            )
        if any(st == RuleEvaluationStatus.ERROR for st in child_statuses):
            return (
                RuleEvaluationStatus.ERROR,
                f"OR condition error: {'; '.join(child_explanations)}",
                all_evidences,
            )
        # All not matched
        return (
            RuleEvaluationStatus.NOT_MATCHED,
            f"OR condition not satisfied (all branches failed): {'; '.join(child_explanations)}",
            all_evidences,
        )

    return RuleEvaluationStatus.ERROR, "Unknown composite operator", all_evidences


# ── Scope Checking & Evaluation Orchestrator ─────────────────────────────────


def is_rule_applicable_to_event(rule: OperationalRule, event: OperationalEvent) -> tuple[bool, str]:
    """
    Verify whether a rule is eligible to evaluate against a given event.
    Checks:
    - Rule active state
    - Supported event types
    - Allowed categories (epistemic boundary protection)
    - Facility scoping
    - Department scoping
    """
    if not rule.is_active:
        return False, "Rule is disabled"

    # Event type match
    if event.event_type not in rule.supported_event_types:
        return False, f"Event type '{event.event_type.value}' not in rule supported types"

    # Epistemic category match (e.g. operational vs forecast vs simulation)
    # Map event category to string for robust comparison
    ev_cat_str = _enum_str(event.category)
    allowed_cat_strs = {_enum_str(c) for c in rule.allowed_categories}
    if ev_cat_str not in allowed_cat_strs:
        return (
            False,
            f"Event category '{ev_cat_str}' not permitted by rule (allowed: {allowed_cat_strs})",
        )

    # Facility scoping
    if rule.facility_id is not None and rule.facility_id != event.facility_id:
        return (
            False,
            f"Rule facility scope '{rule.facility_id}' does not match event facility '{event.facility_id}'",
        )

    # Department scoping
    if rule.department_id is not None:
        event_dept = None
        if hasattr(event.payload, "department_id"):
            event_dept = event.payload.department_id
        elif "department_id" in event.metadata:
            event_dept = event.metadata["department_id"]
        elif event.entity_type.value == "department":
            event_dept = event.entity_id

        if event_dept is not None and event_dept != rule.department_id:
            return (
                False,
                f"Rule department '{rule.department_id}' does not match event department '{event_dept}'",
            )

    return True, "Eligible"


def evaluate_rule_against_event(
    rule: OperationalRule,
    event: OperationalEvent,
    worker_id: str | None = None,
) -> RuleEvaluationRecord:
    """
    Evaluate an OperationalRule against a single OperationalEvent.
    Constructs an immutable, auditable RuleEvaluationRecord with deterministic identity.
    """
    applicable, reason = is_rule_applicable_to_event(rule, event)
    now = utc_now()

    if not applicable:
        eval_id = compute_evaluation_id(rule.rule_id, rule.version, [event.event_id])
        return RuleEvaluationRecord(
            evaluation_id=eval_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            rule_name=rule.name,
            domain=rule.domain,
            severity=rule.severity,
            facility_id=event.facility_id,
            department_id=rule.department_id,
            source_event_ids=[event.event_id],
            status=RuleEvaluationStatus.SKIPPED,
            matched=False,
            evaluated_at=now,
            source_occurred_at=event.occurred_at,
            evidence_references={"skip_reason": reason},
            condition_explanation=f"Evaluation skipped: {reason}",
            requires_human_review=True,
            metadata={"worker_id": worker_id} if worker_id else {},
        )

    # Evaluate declarative condition tree
    status, explanation, evidences = evaluate_condition_tree(rule.condition, event)
    matched = status == RuleEvaluationStatus.MATCHED
    eval_id = compute_evaluation_id(rule.rule_id, rule.version, [event.event_id])

    return RuleEvaluationRecord(
        evaluation_id=eval_id,
        rule_id=rule.rule_id,
        rule_version=rule.version,
        rule_name=rule.name,
        domain=rule.domain,
        severity=rule.severity,
        facility_id=event.facility_id,
        department_id=rule.department_id,
        source_event_ids=[event.event_id],
        status=status,
        matched=matched,
        evaluated_at=now,
        source_occurred_at=event.occurred_at,
        evidence_references={"conditions": evidences},
        condition_explanation=explanation,
        requires_human_review=True,
        metadata={"worker_id": worker_id} if worker_id else {},
    )


# ── Time Window Aggregation Evaluation ────────────────────────────────────────


def evaluate_rule_against_window(
    rule: OperationalRule,
    events: list[OperationalEvent],
    worker_id: str | None = None,
) -> RuleEvaluationRecord:
    """
    Evaluate a time-windowed OperationalRule against a sequence of windowed events.
    Events must already be pre-filtered for the applicable time window [T_now - window, T_now].
    """
    now = utc_now()
    if not events:
        eval_id = compute_evaluation_id(rule.rule_id, rule.version, ["none"])
        return RuleEvaluationRecord(
            evaluation_id=eval_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            rule_name=rule.name,
            domain=rule.domain,
            severity=rule.severity,
            facility_id=rule.facility_id or "global",
            department_id=rule.department_id,
            source_event_ids=[],
            status=RuleEvaluationStatus.DATA_MISSING,
            matched=False,
            evaluated_at=now,
            source_occurred_at=now,
            evidence_references={"reason": "No events in evaluation window"},
            condition_explanation="Evaluation window contained 0 events",
            requires_human_review=True,
            metadata={"worker_id": worker_id} if worker_id else {},
        )

    # Deterministic sorting: chronological by occurred_at, then event_id
    sorted_events = sorted(events, key=lambda e: (e.occurred_at, e.event_id))
    latest_event = sorted_events[-1]
    source_ids = [e.event_id for e in sorted_events]
    eval_id = compute_evaluation_id(rule.rule_id, rule.version, source_ids)

    # Check minimum events constraint
    tw = rule.time_window
    if tw is not None and len(sorted_events) < tw.min_events:
        return RuleEvaluationRecord(
            evaluation_id=eval_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            rule_name=rule.name,
            domain=rule.domain,
            severity=rule.severity,
            facility_id=latest_event.facility_id,
            department_id=rule.department_id,
            source_event_ids=source_ids,
            status=RuleEvaluationStatus.DATA_MISSING,
            matched=False,
            evaluated_at=now,
            source_occurred_at=latest_event.occurred_at,
            evidence_references={
                "events_count": len(sorted_events),
                "min_required": tw.min_events,
            },
            condition_explanation=(
                f"Insufficient events in window (found {len(sorted_events)}, minimum required: {tw.min_events})"
            ),
            requires_human_review=True,
            metadata={"worker_id": worker_id} if worker_id else {},
        )

    # For window evaluations:
    # If aggregation_type is LATEST, evaluate against the most recent event in the window
    if tw is None or tw.aggregation_type == "LATEST":
        return evaluate_rule_against_event(rule, latest_event, worker_id)

    # Numeric aggregations (COUNT, MAX, MIN, AVG)
    if tw.aggregation_type == "COUNT":
        agg_val = len(sorted_events)
    else:
        values = []
        for ev in sorted_events:
            val = resolve_field_value(ev, tw.aggregation_field or "")
            if val is not _MISSING and val is not None:
                try:
                    values.append(float(val))
                except (ValueError, TypeError):
                    pass

        if not values:
            return RuleEvaluationRecord(
                evaluation_id=eval_id,
                rule_id=rule.rule_id,
                rule_version=rule.version,
                rule_name=rule.name,
                domain=rule.domain,
                severity=rule.severity,
                facility_id=latest_event.facility_id,
                department_id=rule.department_id,
                source_event_ids=source_ids,
                status=RuleEvaluationStatus.DATA_MISSING,
                matched=False,
                evaluated_at=now,
                source_occurred_at=latest_event.occurred_at,
                evidence_references={
                    "field": tw.aggregation_field,
                    "valid_numeric_samples": 0,
                },
                condition_explanation=f"No valid numeric samples found for field '{tw.aggregation_field}' in window",
                requires_human_review=True,
                metadata={"worker_id": worker_id} if worker_id else {},
            )

        if tw.aggregation_type == "MAX":
            agg_val = max(values)
        elif tw.aggregation_type == "MIN":
            agg_val = min(values)
        elif tw.aggregation_type == "AVG":
            agg_val = sum(values) / len(values)
        else:
            agg_val = values[-1]

    # Synthesize aggregated event context for condition evaluation
    # We evaluate against the latest event but override the aggregated field with agg_val
    class _SyntheticEventWrapper:
        def __init__(self, base_ev: OperationalEvent, field_override: str, override_val: Any) -> None:
            self._base = base_ev
            self._override_field = field_override
            self._override_val = override_val

        def __getattr__(self, name: str) -> Any:
            return getattr(self._base, name)

    # Evaluate atomic condition
    if isinstance(rule.condition, SingleCondition):
        # Direct check on aggregated metric
        st, exp, ev = evaluate_single_condition(
            rule.condition,
            latest_event,
        )
        matched = st == RuleEvaluationStatus.MATCHED
        explanation = f"Window {tw.aggregation_type} aggregation: {exp}"
        ev["window_aggregated_value"] = agg_val

        return RuleEvaluationRecord(
            evaluation_id=eval_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            rule_name=rule.name,
            domain=rule.domain,
            severity=rule.severity,
            facility_id=latest_event.facility_id,
            department_id=rule.department_id,
            source_event_ids=source_ids,
            status=st,
            matched=matched,
            evaluated_at=now,
            source_occurred_at=latest_event.occurred_at,
            evidence_references={
                "conditions": [ev],
                "window_events_count": len(sorted_events),
                "aggregation_type": tw.aggregation_type,
            },
            condition_explanation=explanation,
            requires_human_review=True,
            metadata={"worker_id": worker_id} if worker_id else {},
        )

    # For composite conditions, evaluate against latest event
    return evaluate_rule_against_event(rule, latest_event, worker_id)
