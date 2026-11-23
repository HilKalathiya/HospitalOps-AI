/**
 * HospitalOps AI — Multi-Agent REST API Client (Milestone 5, Chunk 5.6.6).
 *
 * Exposes typed client methods for the supervisor-and-specialist multi-agent subsystem:
 * - POST /api/v1/agent/multi-agent/coordinate
 * - GET  /api/v1/agent/multi-agent/traces/{trace_id}
 * - GET  /api/v1/agent/multi-agent/specialists
 */

import { apiClient } from './client'
import {
  MultiAgentCoordinateRequest,
  MultiAgentCoordinateResponse,
  MultiAgentTraceResponse,
  SpecialistSummaryResponse,
} from '../types/multiAgent'

interface ApiResponse<T> {
  status: string
  data: T
  meta?: {
    request_id?: string
  }
}

export const multiAgentApi = {
  /**
   * Submit an operational inquiry to the primary supervisor agent with bounded specialist delegation.
   */
  async coordinate(
    request: MultiAgentCoordinateRequest
  ): Promise<MultiAgentCoordinateResponse> {
    const response = await apiClient.post<ApiResponse<MultiAgentCoordinateResponse>>(
      '/agent/multi-agent/coordinate',
      request
    )
    return response.data
  },

  /**
   * Retrieve an authorized, sanitized multi-agent execution trace by unique trace ID.
   * Access is secured server-side; cross-user requests receive 404 without information disclosure.
   */
  async getTrace(
    traceId: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<MultiAgentTraceResponse> {
    const searchParams = new URLSearchParams()
    if (limit) searchParams.set('limit', String(limit))
    if (offset) searchParams.set('offset', String(offset))
    const query = searchParams.toString() ? `?${searchParams.toString()}` : ''

    const response = await apiClient.get<ApiResponse<MultiAgentTraceResponse>>(
      `/agent/multi-agent/traces/${encodeURIComponent(traceId)}${query}`
    )
    return response.data
  },

  /**
   * Retrieve the catalogue of registered domain specialists (Forecasting, Simulation, Optimization, Knowledge).
   */
  async listSpecialists(): Promise<SpecialistSummaryResponse[]> {
    const response = await apiClient.get<ApiResponse<SpecialistSummaryResponse[]>>(
      '/agent/multi-agent/specialists'
    )
    return response.data
  },
}
