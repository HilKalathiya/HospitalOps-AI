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
  status: AgentExecutionStatus
  final_answer: string
  sources: CitationReference[]
  provenance: ProvenanceItem[]
  tool_trace: ToolCallRecord[]
  execution: AgentRunExecutionMetadata
  limitations: string[]
  requires_human_review: boolean
  created_at: string
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
