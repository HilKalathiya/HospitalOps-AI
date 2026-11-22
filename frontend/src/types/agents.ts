/**
 * HospitalOps AI — Agent Subsystem Types (Milestone 5, Chunk 5.1).
 */

import { CitationReference } from '../api/knowledge'

export type AgentExecutionStatus =
  | 'ACCEPTED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'REJECTED'
  | 'FAILED'
  | 'TIMED_OUT'
  | 'LIMIT_REACHED'
  | 'CANCELLED'

export type StopReason =
  | 'SUFFICIENT_EVIDENCE'
  | 'FINAL_ANSWER_READY'
  | 'OUT_OF_SCOPE'
  | 'NO_RELEVANT_TOOLS'
  | 'MAX_STEPS_REACHED'
  | 'MAX_TOOL_CALLS_REACHED'
  | 'TIMEOUT'
  | 'PROVIDER_UNAVAILABLE'
  | 'TOOL_FAILURE'

export type ProvenanceCategory = 'KNOWLEDGE' | 'FORECAST' | 'SIMULATION' | 'OPTIMIZATION'

export type OrchestrationState =
  | 'PENDING'
  | 'UNDERSTANDING'
  | 'PLANNING'
  | 'TOOL_SELECTION'
  | 'TOOL_EXECUTION'
  | 'EVIDENCE_REVIEW'
  | 'RESPONSE_GENERATION'
  | 'COMPLETED'
  | 'REJECTED'
  | 'FAILED'
  | 'CANCELLED'
  | 'TIMED_OUT'
  | 'MAX_STEPS_REACHED'
  | 'INSUFFICIENT_EVIDENCE'

export interface StateTransitionRecord {
  from_state: OrchestrationState
  to_state: OrchestrationState
  timestamp: string
  reason: string
  metadata: Record<string, unknown>
}

export interface AgentTaskPlan {
  objective: string
  task_type: string
  requires_tools: boolean
  reasoning_summary: string
  required_evidence: string[]
  candidate_tool_ids: string[]
  expected_result: string
}

export type EvidenceCategory =
  | 'OBSERVED_DATA'
  | 'FORECAST'
  | 'SIMULATION'
  | 'OPTIMIZATION'
  | 'KNOWLEDGE_POLICY'

export interface AgentEvidence {
  evidence_id: string
  tool_id: string
  tool_version: string
  execution_step: number
  category: EvidenceCategory
  summary: string
  data: Record<string, unknown>
  source_references: string[]
  is_projection: boolean
  is_hypothetical: boolean
  is_recommendation: boolean
  created_at: string
}

export interface AgentExecutionTrace {
  execution_id: string
  agent_id: string
  user_id: string
  start_time: string
  end_time?: string | null
  duration_ms: number
  initial_state: OrchestrationState
  final_state: OrchestrationState
  state_transitions: StateTransitionRecord[]
  task_plan?: AgentTaskPlan | null
  tool_calls: ToolCallRecord[]
  evidence_ids: string[]
  stop_reason: StopReason
  status: AgentExecutionStatus
}

export type ToolCategory =
  | 'KNOWLEDGE'
  | 'FORECASTING'
  | 'SIMULATION'
  | 'OPTIMIZATION'
  | 'OPERATIONS'
  | 'SYSTEM'

export type ExecutionType = 'READ_ONLY' | 'WRITE'

export type ToolErrorCode =
  | 'UNKNOWN_TOOL'
  | 'INVALID_INPUT'
  | 'UNSUPPORTED_SCHEMA_VERSION'
  | 'PERMISSION_DENIED'
  | 'TOOL_DISABLED'
  | 'APPROVAL_REQUIRED'
  | 'OUTPUT_VALIDATION_FAILED'
  | 'EXECUTION_TIMEOUT'
  | 'EXECUTION_FAILED'
  | 'OUTPUT_LIMIT_EXCEEDED'

export interface JsonSchemaObject {
  $schema?: string
  title?: string
  type?: string
  description?: string
  properties?: Record<string, Record<string, unknown>>
  required?: string[]
  [key: string]: unknown
}

export interface ToolDefinition {
  tool_id: string
  display_name: string
  category: ToolCategory
  execution_type: ExecutionType
  schema_version: string
  description: string
  required_permissions: string[]
  requires_approval: boolean
  timeout_seconds: number
  is_read_only: boolean
  tags: string[]
  input_schema_json?: JsonSchemaObject
  output_schema_json?: JsonSchemaObject
}

export interface ProvenanceItem {
  category: ProvenanceCategory
  id: string
  label: string
  details: Record<string, unknown>
}

export interface ToolCallRecord {
  step_index: number
  tool_name: string
  reason: string
  arguments: Record<string, unknown>
  status: string
  duration_ms: number
  output_summary: string
  error_message?: string | null
  error_code?: ToolErrorCode | null
  schema_version?: string
  sources_found: number
  provenance_ids: string[]
}

export interface AgentRunOptions {
  max_steps: number
  max_tool_calls: number
  timeout_seconds: number
  temperature: number
}

export const DEFAULT_AGENT_OPTIONS: AgentRunOptions = {
  max_steps: 6,
  max_tool_calls: 5,
  timeout_seconds: 45.0,
  temperature: 0.0,
}

export interface AgentRunRequest {
  agent_id: string
  task: string
  session_id?: string | null
  options?: Partial<AgentRunOptions>
}

export interface AgentRunExecutionMetadata {
  steps_completed: number
  tool_calls: number
  duration_ms: number
  stop_reason: StopReason
  model: string
  provider: string
}

export interface AgentRunResponse {
  run_id: string
  agent_id: string
  agent_name: string
  session_id?: string | null
  status: AgentExecutionStatus
  final_answer: string
  task_plan?: AgentTaskPlan | null
  sources: CitationReference[]
  provenance: ProvenanceItem[]
  evidence?: AgentEvidence[]
  tool_trace: ToolCallRecord[]
  state_transitions?: StateTransitionRecord[]
  execution: AgentRunExecutionMetadata
  limitations: string[]
  requires_human_review: boolean
  created_at: string
}

export type SessionStatus = 'ACTIVE' | 'ARCHIVED' | 'EXPIRED'

export interface AgentSession {
  session_id: string
  user_id: string
  agent_id: string
  title: string
  status: SessionStatus
  created_at: string
  updated_at: string
  last_activity_at: string
  message_count: number
  latest_execution_id?: string | null
  version: number
  metadata: Record<string, unknown>
}

export interface AgentSessionCreate {
  title?: string
  agent_id?: string
  initial_message?: string
  metadata?: Record<string, unknown>
}

export interface AgentSessionUpdate {
  title?: string
  metadata?: Record<string, unknown>
}

export type AgentMessageRole = 'USER' | 'ASSISTANT' | 'SYSTEM'
export type AgentMessageStatus = 'SENT' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'PARTIAL'

export interface AgentMessage {
  message_id: string
  session_id: string
  user_id: string
  role: AgentMessageRole
  content: string
  status: AgentMessageStatus
  execution_id?: string | null
  created_at: string
  metadata: Record<string, unknown>
}

export interface AgentMetadata {
  agent_id: string
  name: string
  role: string
  description: string
  version: string
  available_tools: string[]
  is_read_only: boolean
}

export interface AgentHealthResponse {
  status: string
  provider_configured: boolean
  provider_healthy: boolean
  provider_name: string
  model_name: string
  registered_agents_count: number
  registered_tools_count: number
  registered_tools: string[]
  agent_version: string
}

// ── Agent Memory & Preferences (Chunk 5.5) ───────────────────────────────────

export type MemoryCategory =
  | 'USER_PREFERENCE'
  | 'WORKFLOW_PREFERENCE'
  | 'EXPLICIT_USER_CONTEXT'

export type MemoryStatus =
  | 'PENDING_APPROVAL'
  | 'ACTIVE'
  | 'SUPERSEDED'
  | 'EXPIRED'
  | 'REJECTED'
  | 'DELETED'

export interface AgentMemory {
  memory_id: string
  user_id: string
  agent_id: string
  category: MemoryCategory
  key: string
  value: string
  summary: string
  status: MemoryStatus
  source_session_id?: string | null
  created_at: string
  updated_at: string
  last_used_at?: string | null
  expires_at?: string | null
  version: number
  metadata?: Record<string, unknown>
}

export interface AgentMemoryCandidate {
  memory_id: string
  user_id: string
  agent_id: string
  category: MemoryCategory
  key: string
  value: string
  summary: string
  status: MemoryStatus
  source_session_id?: string | null
  source_message_ids?: string[]
  created_at: string
  metadata?: Record<string, unknown>
}

export interface AgentMemoryCandidateCreate {
  category: MemoryCategory
  key: string
  value: string
  summary: string
  source_session_id?: string
  source_message_ids?: string[]
  metadata?: Record<string, unknown>
}

export interface AgentMemoryUpdate {
  value?: string
  summary?: string
  metadata?: Record<string, unknown>
}

export interface SuggestedTaskItem {
  id: string
  category: 'Knowledge' | 'Comparative' | 'Forecast' | 'Simulation' | 'Optimization'
  prompt: string
  label: string
}

export const SUGGESTED_AGENT_TASKS: SuggestedTaskItem[] = [
  {
    id: 'task-compare',
    category: 'Comparative',
    label: 'Compare policy with forecast',
    prompt: 'Compare the documented bed escalation policy with the latest existing ICU forecast.',
  },
  {
    id: 'task-policy',
    category: 'Knowledge',
    label: 'ICU bed escalation protocol',
    prompt: 'What is the documented ICU bed escalation process and activation threshold?',
  },
  {
    id: 'task-forecast',
    category: 'Forecast',
    label: 'Summarize ICU demand forecast',
    prompt: 'Summarize the latest existing ICU demand forecast and its forecast horizon.',
  },
  {
    id: 'task-sim',
    category: 'Simulation',
    label: 'Inspect simulation scenario',
    prompt: 'Inspect the existing simulation scenario and explain which constraints caused peak bed shortage.',
  },
  {
    id: 'task-opt',
    category: 'Optimization',
    label: 'Explain optimization allocations',
    prompt: 'Explain why the existing optimization run allocated equipment this way and identify binding bottlenecks.',
  },
]
