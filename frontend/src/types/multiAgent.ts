/**
 * HospitalOps AI — Multi-Agent Transparency Workspace Types (Milestone 5, Chunk 5.6.6).
 *
 * Strongly-typed contracts matching the backend Pydantic schemas in:
 * - backend/app/schemas/multi_agent.py
 * - backend/app/agents/multi_agent/contracts.py
 */

import { CitationReference } from '../api/knowledge'
import { AgentEvidence, ProvenanceItem } from './agents'

export type SpecialistId =
  | 'forecasting_specialist'
  | 'simulation_specialist'
  | 'optimization_specialist'
  | 'knowledge_specialist'

export type SpecialistDomain =
  | 'FORECASTING'
  | 'SIMULATION'
  | 'OPTIMIZATION'
  | 'KNOWLEDGE'

export type DelegationMode =
  | 'NONE'
  | 'SINGLE_SPECIALIST'
  | 'MULTI_SPECIALIST'

export type SpecialistExecutionStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'SUCCESS'
  | 'FAILED'
  | 'TIMED_OUT'
  | 'CANCELLED'
  | 'SKIPPED'

export type MultiAgentEventType =
  | 'PARENT_EXECUTION_STARTED'
  | 'DELEGATION_PLAN_CREATED'
  | 'SPECIALIST_STARTED'
  | 'SPECIALIST_COMPLETED'
  | 'SPECIALIST_FAILED'
  | 'SPECIALIST_TIMED_OUT'
  | 'SPECIALIST_CANCELLED'
  | 'SPECIALIST_SKIPPED'
  | 'AGGREGATION_COMPLETED'

export type AggregationStatus =
  | 'COMPLETED'
  | 'PARTIAL_SUCCESS'
  | 'FAILED'
  | 'NO_RESULTS'

export type EpistemicCategory =
  | 'OBSERVED_DATA'
  | 'FORECAST'
  | 'SIMULATION'
  | 'OPTIMIZATION'
  | 'KNOWLEDGE_POLICY'

// ── Request & Response Contracts ─────────────────────────────────────────────

export interface MultiAgentCoordinateRequest {
  task: string
  session_id?: string | null
  enable_delegation?: boolean | null
}

export interface DelegatedSpecialistSummary {
  specialist_id: string
  status: SpecialistExecutionStatus | string
  duration_ms: number
  summary: string
  tool_calls_count: number
}

export interface MultiAgentCoordinateResponse {
  run_id: string
  session_id?: string | null
  status: string
  final_answer: string
  delegation_occurred: boolean
  delegation_mode: DelegationMode | string
  specialists_invoked: string[]
  specialist_results: DelegatedSpecialistSummary[]
  evidence_categories: EpistemicCategory[] | string[]
  sources: CitationReference[]
  provenance: ProvenanceItem[]
  conflicts: string[]
  is_partial_result: boolean
  trace_id?: string | null
  limitations: string[]
  requires_human_review: boolean
  created_at: string
}

export interface SpecialistSummaryResponse {
  specialist_id: string
  display_name: string
  domain: SpecialistDomain | string
  description: string
  enabled: boolean
}

// ── Delegation Plan & Execution Trace Contracts ──────────────────────────────

export interface DelegationRequest {
  parent_execution_id: string
  delegation_id: string
  target_specialist_id: SpecialistId | string
  task_description: string
  context_evidence_ids: string[]
  timeout_seconds: number
  max_evidence_items: number
  max_output_chars: number
  requested_at: string
}

export interface DelegationPlan {
  parent_execution_id: string
  plan_id: string
  delegations: DelegationRequest[]
  max_depth: number
  total_timeout_seconds: number
  dependencies: Record<string, string[]>
  created_at: string
}

export interface MultiAgentTraceEvent {
  event_id: string
  parent_execution_id: string
  delegation_id?: string | null
  specialist_id?: SpecialistId | string | null
  event_type: MultiAgentEventType | string
  timestamp: string
  duration_ms: number
  details: Record<string, unknown>
}

export interface SpecialistResult {
  specialist_id: SpecialistId | string
  delegation_id: string
  status: SpecialistExecutionStatus | string
  summary: string
  evidence: AgentEvidence[]
  evidence_ids: string[]
  citations: CitationReference[]
  provenance: ProvenanceItem[]
  duration_ms: number
  tool_calls_count: number
  epistemic_category?: EpistemicCategory | string | null
  error_code?: string | null
  error_message?: string | null
  is_fallback: boolean
  started_at: string
  ended_at?: string | null
}

export interface AggregatedSpecialistResult {
  parent_execution_id: string
  plan_id: string
  status: AggregationStatus | string
  is_partial_result: boolean
  specialist_results: SpecialistResult[]
  successful_contributors: string[]
  unsuccessful_contributors: string[]
  conflicts_or_inconsistencies: string[]
  aggregated_evidence: AgentEvidence[]
  all_evidence_ids: string[]
  all_provenance: ProvenanceItem[]
  all_citations: CitationReference[]
  duration_ms: number
  requires_human_review: boolean
  aggregated_at: string
}

export interface MultiAgentTraceResponse {
  trace_id: string
  parent_execution_id: string
  user_id: string
  plan: DelegationPlan
  events: MultiAgentTraceEvent[]
  total_events: number
  aggregated_result?: AggregatedSpecialistResult | null
  total_duration_ms: number
  requires_human_review: boolean
  created_at: string
  completed_at?: string | null
}

// ── Suggested Operational Inquiries for the Workspace ────────────────────────

export interface SuggestedInquiry {
  id: string
  title: string
  description: string
  prompt: string
  expectedDelegation: DelegationMode
  domains: SpecialistDomain[]
}

export const SUGGESTED_MULTI_AGENT_INQUIRIES: SuggestedInquiry[] = [
  {
    id: 'inq-multi-surge',
    title: 'Admission Surge & ICU Projections',
    description: 'Cross-specialist forecasting and what-if simulation under 15% admission surge',
    prompt:
      'What is the latest 7-day ICU bed demand forecast, and what happens to peak bed shortages if admissions increase by 15%?',
    expectedDelegation: 'MULTI_SPECIALIST',
    domains: ['FORECASTING', 'SIMULATION'],
  },
  {
    id: 'inq-opt-policy',
    title: 'Surge Bed Reallocation & SOP Alignment',
    description: 'Mathematical optimization solution cross-referenced against hospital escalation policy',
    prompt:
      'Explain the recommended surge bed reallocation from the latest optimization run, and verify if it complies with the hospital bed overflow protocol.',
    expectedDelegation: 'MULTI_SPECIALIST',
    domains: ['OPTIMIZATION', 'KNOWLEDGE'],
  },
  {
    id: 'inq-forecast-single',
    title: 'Weekly ICU Capacity Trajectory',
    description: 'Focused statistical and deep-learning census forecasting inquiry',
    prompt:
      'Summarize the latest ICU census forecast and highlight the projected peak occupancy date and confidence interval.',
    expectedDelegation: 'SINGLE_SPECIALIST',
    domains: ['FORECASTING'],
  },
  {
    id: 'inq-policy-single',
    title: 'Code Yellow Escalation Protocol',
    description: 'RAG knowledge retrieval for hospital standard operating procedure',
    prompt:
      'What are the mandatory clinical staffing ratios and activation criteria for Code Yellow bed overflow?',
    expectedDelegation: 'SINGLE_SPECIALIST',
    domains: ['KNOWLEDGE'],
  },
]
