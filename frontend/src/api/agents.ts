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
  AgentHealthResponse,
  AgentMetadata,
  AgentRunRequest,
  AgentRunResponse,
  ToolDefinition,
} from '../types/agents'

interface ApiResponse<T> {
  status: string
  data: T
}

export const agentApi = {
  /**
   * Execute an operational inquiry with an authorized agent.
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
}
