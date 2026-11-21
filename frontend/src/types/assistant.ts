import { KnowledgeAnswerResponse } from '../api/knowledge'

export interface AssistantQueryConfig {
  topK: number
  tokenBudget: number
  maxSources: number
  categoryFilter: string
  accessFilter: string
  temperature: number
  requireCitations: boolean
}

export const DEFAULT_QUERY_CONFIG: AssistantQueryConfig = {
  topK: 5,
  tokenBudget: 2048,
  maxSources: 5,
  categoryFilter: '',
  accessFilter: '',
  temperature: 0.1,
  requireCitations: true,
}

export interface SuggestedQuestionItem {
  prompt: string
  label: string
  category: string
}

export const SUGGESTED_OPERATIONAL_QUESTIONS: SuggestedQuestionItem[] = [
  {
    category: 'Surge Protocol',
    label: 'Bed escalation thresholds',
    prompt: 'What are the documented bed escalation procedures when hospital occupancy exceeds 85%?',
  },
  {
    category: 'Equipment SOP',
    label: 'Ventilator shortage protocol',
    prompt: 'What is the standard operating procedure for reporting mechanical ventilator shortages across ICUs?',
  },
  {
    category: 'Infection Control',
    label: 'Respiratory isolation rules',
    prompt: 'Which infection control guidelines and PPE protocols apply to negative-pressure respiratory isolation units?',
  },
  {
    category: 'Staffing & Triage',
    label: 'Charge nurse roles',
    prompt: 'What operational responsibilities and shift escalation duties are designated to the unit charge nurse?',
  },
  {
    category: 'Emergency Surge',
    label: 'ED overflow diversion',
    prompt: 'Which clinical and operational criteria trigger emergency department diversion during admission surges?',
  },
]

export interface SessionHistoryItem {
  id: string
  question: string
  response: KnowledgeAnswerResponse
  timestamp: string
}
