"""
HospitalOps AI — Operational Rule Contracts & Validation Tests (Milestone 6, Chunk 6.2).

Tests:
- Valid rule definitions and fields
- Prohibited clinical diagnostic attributes rejection
- AST injection prevention (no __, class, dict, globals)
- Operator and value type consistency
- Condition tree depth and count bounding
- Time window configuration constraints
- Category epistemic boundary specification
"""

import pytest

from app.events.contracts import EventCategory, EventType
from app.rules.contracts import (
    MAX_CONDITIONS_TOTAL,
    CompositeCondition,
    LogicalOperator,
    OperationalRule,
    RuleDomain,
    RuleOperator,
    RuleSeverity,
    SingleCondition,
    TimeWindowConfig,
)
from app.rules.exceptions import RuleValidationError


class TestRuleContracts:
    def test_01_valid_single_condition_rule(self):
        rule = OperationalRule(
            rule_id="rule_icu_capacity_01",
            name="ICU High Occupancy Warning",
            description="Warns when ICU operational occupancy rate exceeds 85%",
            domain=RuleDomain.CAPACITY,
            version=1,
            is_active=True,
            supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            facility_id="facility_main",
            severity=RuleSeverity.HIGH,
            condition=SingleCondition(
                field="payload.occupancy_rate",
                operator=RuleOperator.GREATER_THAN,
                value=0.85,
            ),
            provenance_policy_ref="POLICY_CAPACITY_SEC_4",
        )
        assert rule.rule_id == "rule_icu_capacity_01"
        assert rule.version == 1
        assert rule.severity == RuleSeverity.HIGH
        assert rule.condition.field == "payload.occupancy_rate"

    def test_02_prohibited_clinical_field_rejection(self):
        with pytest.raises(RuleValidationError) as exc:
            SingleCondition(
                field="payload.patient_diagnosis",
                operator=RuleOperator.EQUALS,
                value="Sepsis",
            )
        assert "prohibited internal or clinical attributes" in str(exc.value)

    def test_03_prohibited_ast_injection_patterns(self):
        for bad_field in ["__class__", "payload.__dict__", "metadata.globals", "payload.builtins"]:
            with pytest.raises(RuleValidationError) as exc:
                SingleCondition(
                    field=bad_field,
                    operator=RuleOperator.EXISTS,
                )
            assert "prohibited internal or clinical attributes" in str(exc.value)

    def test_04_invalid_field_root(self):
        with pytest.raises(RuleValidationError) as exc:
            SingleCondition(
                field="invalid_root.subfield",
                operator=RuleOperator.EQUALS,
                value=10,
            )
        assert "permitted root fields" in str(exc.value)

    def test_05_operator_value_validation(self):
        # IN_SET requires list/set
        with pytest.raises(RuleValidationError) as exc:
            SingleCondition(
                field="payload.status",
                operator=RuleOperator.IN_SET,
                value="not_a_list",
            )
        assert "requires a non-empty list/set value" in str(exc.value)

        # EQUALS requires non-null target
        with pytest.raises(RuleValidationError) as exc:
            SingleCondition(
                field="payload.available_beds",
                operator=RuleOperator.EQUALS,
                value=None,
            )
        assert "requires a non-null target comparison value" in str(exc.value)

    def test_06_excessive_condition_nesting_depth(self):
        # Create a tree deeper than MAX_CONDITION_DEPTH (3)
        c4 = SingleCondition(field="payload.a", operator=RuleOperator.EQUALS, value=1)
        c3 = CompositeCondition(operator=LogicalOperator.AND, conditions=[c4])
        c2 = CompositeCondition(operator=LogicalOperator.AND, conditions=[c3])
        with pytest.raises(RuleValidationError) as exc:
            CompositeCondition(operator=LogicalOperator.AND, conditions=[c2])
        assert "exceeds maximum permitted nesting depth" in str(exc.value)

    def test_07_excessive_condition_count(self):
        conditions = [
            SingleCondition(field=f"payload.f_{i}", operator=RuleOperator.EQUALS, value=i)
            for i in range(MAX_CONDITIONS_TOTAL + 1)
        ]
        with pytest.raises((RuleValidationError, ValueError)) as exc:
            CompositeCondition(operator=LogicalOperator.AND, conditions=conditions)
        assert "at most 10 items" in str(exc.value) or "exceeds maximum permitted" in str(exc.value)

    def test_08_empty_allowed_categories_rejection(self):
        with pytest.raises((RuleValidationError, ValueError)) as exc:
            OperationalRule(
                rule_id="rule_bad_cat",
                name="Bad Category Rule",
                description="Rule with empty categories",
                domain=RuleDomain.CAPACITY,
                supported_event_types=[EventType.OPERATIONS_CAPACITY_UPDATED],
                allowed_categories=[],
                condition=SingleCondition(
                    field="payload.available_beds",
                    operator=RuleOperator.LESS_THAN,
                    value=5,
                ),
            )
        assert "at least 1 item" in str(exc.value) or "allowed_categories" in str(exc.value)

    def test_09_time_window_validation(self):
        # Exceeds max window (24h)
        with pytest.raises((RuleValidationError, ValueError)):
            TimeWindowConfig(window_seconds=100000)

        # Aggregation without field
        with pytest.raises(RuleValidationError) as exc:
            TimeWindowConfig(window_seconds=3600, aggregation_type="AVG", aggregation_field=None)
        assert "aggregation_field is required" in str(exc.value)

    def test_10_illustrative_rule_flagging(self):
        rule = OperationalRule(
            rule_id="rule_demo_surge_01",
            name="Demo Surge Rule",
            description="Illustrative demonstration threshold for training",
            domain=RuleDomain.THROUGHPUT,
            supported_event_types=[EventType.OPERATIONS_ADMISSION_RECORDED],
            allowed_categories=[EventCategory.OBSERVED_OPERATIONAL],
            severity=RuleSeverity.MEDIUM,
            condition=SingleCondition(
                field="payload.admitted_count",
                operator=RuleOperator.GREATER_THAN,
                value=25,
            ),
            is_illustrative=True,
        )
        assert rule.is_illustrative is True
