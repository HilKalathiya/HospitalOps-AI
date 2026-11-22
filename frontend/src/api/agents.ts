/**
 * HospitalOps AI — Agent Subsystem API Client (Milestone 5, Chunk 5.1).
 *
 * Provides typed methods to interact with the backend agent runtime:
 * - Run agent with bounded execution
 * - Fetch agent framework health and readiness
 * - List registered agents and inspect tool configurations
 */

import { apiClient } from './client'
import {
  AgentExecutionTrace,
  AgentHealthResponse,
  AgentMemory,
  AgentMemoryCandidate,
  AgentMemoryCandidateCreate,
  AgentMemoryUpdate,
  AgentMessage,
  AgentMetadata,
  AgentRunRequest,
  AgentRunResponse,
  AgentSession,
  AgentSessionCreate,
  AgentSessionUpdate,
  MemoryCategory,
  SessionStatus,
  ToolDefinition,
} from '../types/agents'

interface ApiResponse<T> {
  status: string
  data: T
}

export const agentApi = {
  /**
   * Execute an operational inquiry via the Agent Orchestration Engine (Chunk 5.3).
   */
  async executeAgent(request: AgentRunRequest): Promise<AgentRunResponse> {
    const response = await apiClient.post<ApiResponse<AgentRunResponse>>(
      '/agents/execute',
      request
    )
    return response.data
  },

  /**
   * Retrieve an auditable sequential execution trace by run ID (Chunk 5.3).
   */
  async getExecutionTrace(executionId: string): Promise<AgentExecutionTrace> {
    const response = await apiClient.get<ApiResponse<AgentExecutionTrace>>(
      `/agents/traces/${executionId}`
    )
    return response.data
  },

  /**
   * Execute an operational inquiry with an authorized agent (Legacy/Direct).
   */
  async runAgent(request: AgentRunRequest): Promise<AgentRunResponse> {
    const response = await apiClient.post<ApiResponse<AgentRunResponse>>(
      '/agents/run',
      request
    )
    return response.data
  },

  /**
   * Check agent framework health, active provider, and registered tool counts.
   */
  async getAgentHealth(): Promise<AgentHealthResponse> {
    const response = await apiClient.get<ApiResponse<AgentHealthResponse>>(
      '/agents/health'
    )
    return response.data
  },

  /**
   * List all registered agents available to the caller.
   */
  async listAgents(): Promise<AgentMetadata[]> {
    const response = await apiClient.get<ApiResponse<AgentMetadata[]>>(
      '/agents'
    )
    return response.data
  },

  /**
   * Retrieve metadata for a specific agent.
   */
  async getAgentDetail(agentId: string): Promise<AgentMetadata> {
    const response = await apiClient.get<ApiResponse<AgentMetadata>>(
      `/agents/${agentId}`
    )
    return response.data
  },

  /**
   * Discover registered tools and their standardized contracts/schemas (Chunk 5.2).
   */
  async listTools(params?: {
    category?: string
    tag?: string
    include_schemas?: boolean
  }): Promise<ToolDefinition[]> {
    const searchParams = new URLSearchParams()
    if (params?.category) searchParams.set('category', params.category)
    if (params?.tag) searchParams.set('tag', params.tag)
    if (params?.include_schemas !== undefined) {
      searchParams.set('include_schemas', String(params.include_schemas))
    }
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    const response = await apiClient.get<ApiResponse<ToolDefinition[]>>(
      `/agents/tools${query}`
    )
    return response.data
  },

  /**
   * Retrieve full contract and input/output JSON schemas for a specific tool (Chunk 5.2).
   */
  async getToolDetail(toolId: string): Promise<ToolDefinition> {
    const response = await apiClient.get<ApiResponse<ToolDefinition>>(
      `/agents/tools/${toolId}`
    )
    return response.data
  },

  /**
   * Create a new persistent conversational session (Chunk 5.4).
   */
  async createSession(payload: AgentSessionCreate): Promise<AgentSession> {
    const response = await apiClient.post<ApiResponse<AgentSession>>(
      '/agents/sessions',
      payload
    )
    return response.data
  },

  /**
   * List conversational sessions for the authenticated user (Chunk 5.4).
   */
  async listSessions(params?: {
    status?: SessionStatus
    page?: number
    page_size?: number
  }): Promise<AgentSession[]> {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.set('status', params.status)
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    const response = await apiClient.get<ApiResponse<AgentSession[]>>(
      `/agents/sessions${query}`
    )
    return response.data
  },

  /**
   * Retrieve session metadata (Chunk 5.4).
   */
  async getSession(sessionId: string): Promise<AgentSession> {
    const response = await apiClient.get<ApiResponse<AgentSession>>(
      `/agents/sessions/${sessionId}`
    )
    return response.data
  },

  /**
   * Update session attributes like custom title (Chunk 5.4).
   */
  async updateSession(
    sessionId: string,
    payload: AgentSessionUpdate
  ): Promise<AgentSession> {
    const response = await apiClient.patch<ApiResponse<AgentSession>>(
      `/agents/sessions/${sessionId}`,
      payload
    )
    return response.data
  },

  /**
   * Transition session status to ARCHIVED (Chunk 5.4).
   */
  async archiveSession(sessionId: string): Promise<AgentSession> {
    const response = await apiClient.post<ApiResponse<AgentSession>>(
      `/agents/sessions/${sessionId}/archive`
    )
    return response.data
  },

  /**
   * Restore an archived session back to ACTIVE (Chunk 5.4).
   */
  async restoreSession(sessionId: string): Promise<AgentSession> {
    const response = await apiClient.post<ApiResponse<AgentSession>>(
      `/agents/sessions/${sessionId}/restore`
    )
    return response.data
  },

  /**
   * Permanently delete a session and its message history (Chunk 5.4).
   */
  async deleteSession(
    sessionId: string
  ): Promise<{ session_id: string; status: string }> {
    const response = await apiClient.delete<
      ApiResponse<{ session_id: string; status: string }>
    >(`/agents/sessions/${sessionId}`)
    return response.data
  },

  /**
   * List chronological message history for a session (Chunk 5.4).
   */
  async listMessages(
    sessionId: string,
    params?: { page?: number; page_size?: number }
  ): Promise<AgentMessage[]> {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    const response = await apiClient.get<ApiResponse<AgentMessage[]>>(
      `/agents/sessions/${sessionId}/messages${query}`
    )
    return response.data
  },

  /**
   * Post a user message and execute a conversational turn within a session (Chunk 5.4).
   */
  async postSessionMessage(
    sessionId: string,
    content: string
  ): Promise<AgentRunResponse> {
    const response = await apiClient.post<ApiResponse<AgentRunResponse>>(
      `/agents/sessions/${sessionId}/messages`,
      { content }
    )
    return response.data
  },

  // ── Agent Memory & Preferences (Chunk 5.5) ───────────────────────────────────

  /**
   * List pending memory candidates awaiting user review and approval.
   */
  async listPendingMemories(params?: {
    page?: number
    page_size?: number
  }): Promise<AgentMemoryCandidate[]> {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    const response = await apiClient.get<ApiResponse<AgentMemoryCandidate[]>>(
      `/agents/memories/pending${query}`
    )
    return response.data
  },

  /**
   * Manually register an operational preference or context candidate.
   */
  async createMemoryCandidate(
    payload: AgentMemoryCandidateCreate
  ): Promise<AgentMemoryCandidate> {
    const response = await apiClient.post<ApiResponse<AgentMemoryCandidate>>(
      '/agents/memories/candidate',
      payload
    )
    return response.data
  },

  /**
   * Explicitly approve a memory candidate to ACTIVE status.
   */
  async approveMemory(memoryId: string): Promise<AgentMemory> {
    const response = await apiClient.post<ApiResponse<AgentMemory>>(
      `/agents/memories/${memoryId}/approve`
    )
    return response.data
  },

  /**
   * Reject a pending memory candidate.
   */
  async rejectMemory(memoryId: string): Promise<AgentMemoryCandidate> {
    const response = await apiClient.post<ApiResponse<AgentMemoryCandidate>>(
      `/agents/memories/${memoryId}/reject`
    )
    return response.data
  },

  /**
   * List approved active agent memories.
   */
  async listActiveMemories(params?: {
    category?: MemoryCategory
    page?: number
    page_size?: number
  }): Promise<AgentMemory[]> {
    const searchParams = new URLSearchParams()
    if (params?.category) searchParams.set('category', params.category)
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.page_size) searchParams.set('page_size', String(params.page_size))
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''
    const response = await apiClient.get<ApiResponse<AgentMemory[]>>(
      `/agents/memories${query}`
    )
    return response.data
  },

  /**
   * Retrieve a specific active memory.
   */
  async getMemory(memoryId: string): Promise<AgentMemory> {
    const response = await apiClient.get<ApiResponse<AgentMemory>>(
      `/agents/memories/${memoryId}`
    )
    return response.data
  },

  /**
   * Update value or summary of an active memory.
   */
  async updateMemory(
    memoryId: string,
    payload: AgentMemoryUpdate
  ): Promise<AgentMemory> {
    const response = await apiClient.patch<ApiResponse<AgentMemory>>(
      `/agents/memories/${memoryId}`,
      payload
    )
    return response.data
  },

  /**
   * Soft-delete an agent memory.
   */
  async deleteMemory(
    memoryId: string
  ): Promise<{ memory_id: string; status: string }> {
    const response = await apiClient.delete<
      ApiResponse<{ memory_id: string; status: string }>
    >(`/agents/memories/${memoryId}`)
    return response.data
  },
}
