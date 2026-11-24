"""
HospitalOps AI — Operational Rule Engine & Real-Time Event Processing (Milestone 6, Chunk 6.2).
"""

from app.rules.consumer import OperationalEventConsumer
from app.rules.contracts import (
    CompositeCondition,
    EventProcessingRecord,
    LogicalOperator,
    OperationalRule,
    ProcessingStatus,
    RuleDomain,
    RuleEvaluationRecord,
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
from app.rules.exceptions import (
    RuleConflictError,
    RuleEngineError,
    RuleEvaluationError,
    RuleNotFoundError,
    RulePersistenceError,
    RuleValidationError,
)
from app.rules.service import OperationalRuleService

__all__ = [
    "CompositeCondition",
    "EventProcessingRecord",
    "LogicalOperator",
    "OperationalEventConsumer",
    "OperationalRule",
    "OperationalRuleService",
    "ProcessingStatus",
    "RuleConflictError",
    "RuleDomain",
    "RuleEngineError",
    "RuleEvaluationError",
    "RuleEvaluationRecord",
    "RuleEvaluationStatus",
    "RuleNotFoundError",
    "RuleOperator",
    "RulePersistenceError",
    "RuleSeverity",
    "RuleValidationError",
    "SingleCondition",
    "TimeWindowConfig",
    "compute_evaluation_id",
    "evaluate_condition_tree",
    "evaluate_rule_against_event",
    "evaluate_rule_against_window",
    "evaluate_single_condition",
    "is_rule_applicable_to_event",
    "resolve_field_value",
]
