import { apiClient } from './client'
import { PaginatedResponse } from './patients'

export interface ResourceCreate {
  name: string
  resource_type: 'VENTILATOR' | 'MONITOR' | 'OXYGEN' | 'STAFFING' | 'EQUIPMENT' | 'OTHER'
  department_id?: string | null
  quantity_total: number
  quantity_available: number
  quantity_reserved?: number
  unit?: string | null
  criticality?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
}

export interface ResourceUpdate {
  name?: string | null
  quantity_total?: number | null
  quantity_available?: number | null
  quantity_reserved?: number | null
  status?: 'OPERATIONAL' | 'MAINTENANCE' | 'OUT_OF_SERVICE' | null
  criticality?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null
}

export interface ResourceResponse {
  resource_id: string
  name: string
  resource_type: 'VENTILATOR' | 'MONITOR' | 'OXYGEN' | 'STAFFING' | 'EQUIPMENT' | 'OTHER'
  department_id: string | null
  quantity_total: number
  quantity_available: number
  quantity_reserved: number
  unit: string | null
  status: 'OPERATIONAL' | 'MAINTENANCE' | 'OUT_OF_SERVICE'
  criticality: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  created_at: string
  updated_at: string
}

export interface ResourceSummary {
  types_count: number
  total_quantity: number
  available_quantity: number
  reserved_quantity: number
  unavailable_quantity: number
  critical_resources: number
}

export const resourcesApi = {
  create: (data: ResourceCreate) => apiClient.post<ResourceResponse>('/resources', data),
  get: (resourceId: string) => apiClient.get<ResourceResponse>(`/resources/${resourceId}`),
  update: (resourceId: string, data: ResourceUpdate) => apiClient.patch<ResourceResponse>(`/resources/${resourceId}`, data),
  list: (params?: { page?: number; page_size?: number; department_id?: string; resource_type?: string; status?: string; criticality?: string }) => {
    const query = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          query.append(key, value.toString())
        }
      })
    }
    const queryString = query.toString()
    return apiClient.get<PaginatedResponse<ResourceResponse>>(`/resources${queryString ? `?${queryString}` : ''}`)
  },
  getSummary: (departmentId?: string) => {
    const url = departmentId ? `/resources/summary?department_id=${departmentId}` : '/resources/summary'
    return apiClient.get<ResourceSummary>(url)
  },
  reserve: (resourceId: string, amount: number) => 
    apiClient.post<ResourceResponse>(`/resources/${resourceId}/reserve?amount=${amount}`),
  release: (resourceId: string, amount: number) => 
    apiClient.post<ResourceResponse>(`/resources/${resourceId}/release?amount=${amount}`)
}
