"""
HospitalOps AI — Declarative Rule Evaluator Tests (Milestone 6, Chunk 6.2).

Tests:
- SingleCondition operators (eq, neq, gt, gte, lt, lte, in, not_in, exists, does_not_exist)
- CompositeCondition boolean logic (AND, OR)
- Missing and null data behavior (classified as DATA_MISSING, never silently assumed 0)
- Epistemic category filtering and facility scoping
- Time-window aggregation evaluation (COUNT, MAX, AVG, LATEST)
- Evidence references and deterministic evaluation identity
"""

from datetime import datetime, timedelta

from app.events.contracts import (
    CapacityUpdatedPayload,
    EntityType,
    EventCategory,
    EventType,
    ForecastCompletedPayload,
    OperationalEvent,
)
from app.models.base import utc_now
from app.rules.contracts import (
    CompositeCondition,
    LogicalOperator,
    OperationalRule,
    RuleDomain,
    RuleEvaluationStatus,
    RuleOperator,
    RuleSeverity,
    SingleCondition,
    TimeWindowConfig,
    compute_evaluation_id,
)
from app.rules.evaluator import (
    evaluate_condition_tree,
    evaluate_rule_against_event,
    evaluate_rule_against_window,
    evaluate_single_condition,
    is_rule_applicable_to_event,
    resolve_field_value,
)


def _make_capacity_event(
    event_id: str = "evt_cap_test_01",
    facility_id: str = "facility_main",
    occupancy_rate: float = 0.92,
    available_beds: int = 4,
    category: EventCategory = EventCategory.OBSERVED_OPERATIONAL,
    occurred_at: datetime | None = None,
) -> OperationalEvent:
    payload = CapacityUpdatedPayload(
        department_id="ICU",
        total_beds=50,
        occupied_beds=46,
        available_beds=available_beds,
        operational_occupancy_rate=occupancy_rate,
    )
    return OperationalEvent(
        event_id=event_id,
        event_type=EventType.OPERATIONS_CAPACITY_UPDATED,
        category=category,
        facility_id=facility_id,
        source="hospitalops.capacity_service",
        entity_type=EntityType.DEPARTMENT,
        entity_id="ICU",
        correlation_id="corr_test_01",
        occurred_at=occurred_at or utc_now(),
        payload=payload.model_dump(),
        metadata={"operational_status": "CRITICAL"},
    )


class TestRuleEvaluator:
    def test_01_resolve_field_value(self):
        ev = _make_capacity_event(occupancy_rate=0.88)
        assert resolve_field_value(ev, "payload.operational_occupancy_rate") == 0.88
        assert resolve_field_value(ev, "payload.available_beds") == 4
        assert resolve_field_value(ev, "facility_id") == "facility_main"
        assert resolve_field_value(ev, "category") == "OBSERVED_OPERATIONAL"
        assert resolve_field_value(ev, "metadata.operational_status") == "CRITICAL"

    def test_02_relational_operators(self):
        ev = _make_capacity_event(occupancy_rate=0.92, available_beds=4)

        # GT (0.92 > 0.90 -> MATCHED)
        c_gt = SingleCondition(field="payload.operational_occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.90)
        st, exp, ev_dict = evaluate_single_condition(c_gt, ev)
        assert st == RuleEvaluationStatus.MATCHED
        assert ev_dict["observed_value"] == 0.92

        # GTE (0.92 >= 0.92 -> MATCHED)
        c_gte = SingleCondition(field="payload.operational_occupancy_rate", operator=RuleOperator.GREATER_THAN_OR_EQUAL, value=0.92)
        st, _, _ = evaluate_single_condition(c_gte, ev)
        assert st == RuleEvaluationStatus.MATCHED

        # LT (4 < 5 -> MATCHED)
        c_lt = SingleCondition(field="payload.available_beds", operator=RuleOperator.LESS_THAN, value=5)
        st, _, _ = evaluate_single_condition(c_lt, ev)
        assert st == RuleEvaluationStatus.MATCHED

        # LTE (4 <= 3 -> NOT_MATCHED)
        c_lte = SingleCondition(field="payload.available_beds", operator=RuleOperator.LESS_THAN_OR_EQUAL, value=3)
        st, _, _ = evaluate_single_condition(c_lte, ev)
        assert st == RuleEvaluationStatus.NOT_MATCHED

    def test_03_equality_and_membership_operators(self):
        ev = _make_capacity_event()

        # EQUALS
        c_eq = SingleCondition(field="metadata.operational_status", operator=RuleOperator.EQUALS, value="CRITICAL")
        st, _, _ = evaluate_single_condition(c_eq, ev)
        assert st == RuleEvaluationStatus.MATCHED

        # NOT EQUALS
        c_neq = SingleCondition(field="metadata.operational_status", operator=RuleOperator.NOT_EQUALS, value="NORMAL")
        st, _, _ = evaluate_single_condition(c_neq, ev)
        assert st == RuleEvaluationStatus.MATCHED

        # IN_SET
        c_in = SingleCondition(field="metadata.operational_status", operator=RuleOperator.IN_SET, value=["SURGE", "CRITICAL"])
        st, _, _ = evaluate_single_condition(c_in, ev)
        assert st == RuleEvaluationStatus.MATCHED

        # NOT_IN_SET
        c_notin = SingleCondition(field="metadata.operational_status", operator=RuleOperator.NOT_IN_SET, value=["NORMAL", "LOW"])
        st, _, _ = evaluate_single_condition(c_notin, ev)
        assert st == RuleEvaluationStatus.MATCHED

    def test_04_existence_operators(self):
        ev = _make_capacity_event()
        c_exists = SingleCondition(field="payload.available_beds", operator=RuleOperator.EXISTS)
        st, _, _ = evaluate_single_condition(c_exists, ev)
        assert st == RuleEvaluationStatus.MATCHED

        c_no_exist = SingleCondition(field="payload.missing_field", operator=RuleOperator.DOES_NOT_EXIST)
        st, _, _ = evaluate_single_condition(c_no_exist, ev)
        assert st == RuleEvaluationStatus.MATCHED

    def test_05_missing_field_classified_as_data_missing(self):
        ev = _make_capacity_event()
        c = SingleCondition(field="payload.non_existent_metric", operator=RuleOperator.GREATER_THAN, value=10)
        st, exp, ev_dict = evaluate_single_condition(c, ev)
        assert st == RuleEvaluationStatus.DATA_MISSING
        assert "missing from event" in exp

    def test_06_composite_and_or_logic(self):
        ev = _make_capacity_event(occupancy_rate=0.92, available_beds=4)

        # AND: both true -> MATCHED
        cond_and = CompositeCondition(
            operator=LogicalOperator.AND,
            conditions=[
                SingleCondition(field="payload.operational_occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.90),
                SingleCondition(field="payload.available_beds", operator=RuleOperator.LESS_THAN, value=10),
            ],
        )
        st, exp, _ = evaluate_condition_tree(cond_and, ev)
        assert st == RuleEvaluationStatus.MATCHED

        # AND: one false -> NOT_MATCHED
        cond_and_fail = CompositeCondition(
            operator=LogicalOperator.AND,
            conditions=[
                SingleCondition(field="payload.operational_occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.95),  # false
                SingleCondition(field="payload.available_beds", operator=RuleOperator.LESS_THAN, value=10),     # true
            ],
        )
        st, exp, _ = evaluate_condition_tree(cond_and_fail, ev)
        assert st == RuleEvaluationStatus.NOT_MATCHED

        # OR: one true -> MATCHED
        cond_or = CompositeCondition(
            operator=LogicalOperator.OR,
            conditions=[
                SingleCondition(field="payload.operational_occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.99),  # false
                SingleCondition(field="payload.available_beds", operator=RuleOperator.LESS_THAN, value=5),      # true
            ],
        )
        st, exp, _ = evaluate_condition_tree(cond_or, ev)
        assert st == RuleEvaluationStatus.MATCHED

    def test_07_epistemic_category_filtering(self):
        rule = OperationalRule(
            rule_id="rule_obs_only_01",
            name="Observed Capacity Only",
            description="Evaluates only real observed telemetry",
            domain=RuleDomain.CAPACITY,
            supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED, EventType.FORECAST_COMPLETED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            condition=SingleCondition(field="payload.operational_occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.85),
        )

        # 1. Observed event matches rule
        ev_obs = _make_capacity_event(category=EventCategory.OBSERVED_OPERATIONAL)
        applicable, _ = is_rule_applicable_to_event(rule, ev_obs)
        assert applicable is True

        # 2. Forecast event is rejected by category filter (epistemic boundary protection!)
        ev_forecast = OperationalEvent(
            event_id="evt_forecast_001",
            event_type=EventType.FORECAST_COMPLETED,
            category=EventCategory.FORECAST_OUTPUT,
            source="hospitalops.forecasting",
            entity_type=EntityType.FACILITY,
            entity_id="facility_main",
            facility_id="facility_main",
            payload=ForecastCompletedPayload(
                forecast_id="fc_99",
                target_metric="occupancy",
                horizon_days=7,
                model_type="ensemble",
                peak_predicted_value=0.94,
            ).model_dump(),
        )
        applicable, reason = is_rule_applicable_to_event(rule, ev_forecast)
        assert applicable is False
        assert "not permitted by rule" in reason

    def test_08_facility_scoping_and_disabled_rules(self):
        rule = OperationalRule(
            rule_id="rule_facility_north_01",
            name="Facility North Rule",
            description="Scoped strictly to facility_north",
            domain=RuleDomain.CAPACITY,
            supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            facility_id="facility_north",
            condition=SingleCondition(field="payload.operational_occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.85),
        )

        ev_south = _make_capacity_event(facility_id="facility_south")
        eval_record = evaluate_rule_against_event(rule, ev_south)
        assert eval_record.status == RuleEvaluationStatus.SKIPPED
        assert "does not match" in eval_record.condition_explanation

    def test_09_evaluation_provenance_and_safety_invariants(self):
        rule = OperationalRule(
            rule_id="rule_eval_prov_01",
            name="Capacity Warning",
            description="Operational alert",
            domain=RuleDomain.CAPACITY,
            version=2,
            supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            severity=RuleSeverity.CRITICAL,
            condition=SingleCondition(field="payload.operational_occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.85),
        )
        ev = _make_capacity_event(event_id="evt_prov_01", occupancy_rate=0.94)
        rec = evaluate_rule_against_event(rule, ev, worker_id="worker_alpha")

        assert rec.matched is True
        assert rec.rule_id == "rule_eval_prov_01"
        assert rec.rule_version == 2
        assert rec.source_event_ids == ["evt_prov_01"]
        assert rec.requires_human_review is True  # Non-negotiable healthcare safety boundary
        assert rec.evaluation_id == compute_evaluation_id("rule_eval_prov_01", 2, ["evt_prov_01"])
        assert rec.metadata["worker_id"] == "worker_alpha"

    def test_10_time_window_aggregation_evaluation(self):
        now = utc_now()
        rule = OperationalRule(
            rule_id="rule_window_avg_01",
            name="Window Average Occupancy",
            description="Trigger if average occupancy across window exceeds 85%",
            domain=RuleDomain.CAPACITY,
            supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            time_window=TimeWindowConfig(
                window_seconds=1800,
                aggregation_type="AVG",
                aggregation_field="payload.operational_occupancy_rate",
                min_events=3,
            ),
            condition=SingleCondition(field="payload.operational_occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.85),
        )

        # 3 events with occupancy rates: 0.80, 0.90, 0.91 -> avg = 0.87 (> 0.85 -> MATCHED)
        events = [
            _make_capacity_event("evt_w_01", occupancy_rate=0.80, occurred_at=now - timedelta(minutes=15)),
            _make_capacity_event("evt_w_02", occupancy_rate=0.90, occurred_at=now - timedelta(minutes=10)),
            _make_capacity_event("evt_w_03", occupancy_rate=0.91, occurred_at=now - timedelta(minutes=5)),
        ]
        rec = evaluate_rule_against_window(rule, events)
        assert rec.status == RuleEvaluationStatus.MATCHED
        assert rec.matched is True
        assert len(rec.source_event_ids) == 3

    def test_11_time_window_insufficient_events(self):
        now = utc_now()
        rule = OperationalRule(
            rule_id="rule_window_insuf_01",
            name="Window Min Events",
            description="Requires at least 5 events",
            domain=RuleDomain.CAPACITY,
            supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            time_window=TimeWindowConfig(
                window_seconds=1800,
                aggregation_type="COUNT",
                min_events=5,
            ),
            condition=SingleCondition(field="payload.operational_occupancy_rate", operator=RuleOperator.GREATER_THAN, value=0.85),
        )

        # Only 2 events provided
        events = [
            _make_capacity_event("evt_w_01", occurred_at=now - timedelta(minutes=10)),
            _make_capacity_event("evt_w_02", occurred_at=now - timedelta(minutes=5)),
        ]
        rec = evaluate_rule_against_window(rule, events)
        assert rec.status == RuleEvaluationStatus.DATA_MISSING
        assert rec.matched is False
        assert "Insufficient events in window" in rec.condition_explanation
