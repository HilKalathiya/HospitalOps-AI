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

import { DEMO_RESOURCES, DEMO_RESOURCE_SUMMARY } from '../data/demoOperationalData'

const localResources: ResourceResponse[] = [...DEMO_RESOURCES]

export const resourcesApi = {
  create: (data: ResourceCreate) => apiClient.post<ResourceResponse>('/resources', data),
  get: async (resourceId: string) => {
    try {
      return await apiClient.get<ResourceResponse>(`/resources/${resourceId}`)
    } catch {
      const found = localResources.find(r => r.resource_id === resourceId)
      if (found) return found
      throw new Error(`Resource ${resourceId} not found`)
    }
  },
  update: (resourceId: string, data: ResourceUpdate) => apiClient.patch<ResourceResponse>(`/resources/${resourceId}`, data),
  list: async (params?: { page?: number; page_size?: number; department_id?: string; resource_type?: string; status?: string; criticality?: string }) => {
    try {
      const query = new URLSearchParams()
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            query.append(key, value.toString())
          }
        })
      }
      const queryString = query.toString()
      const res = await apiClient.get<PaginatedResponse<ResourceResponse>>(`/resources${queryString ? `?${queryString}` : ''}`)
      if (res && res.data && res.data.length > 0) return res
      throw new Error('Fallback to demo resources')
    } catch {
      let filtered = [...localResources]
      if (params?.resource_type) filtered = filtered.filter(r => r.resource_type === params.resource_type)
      if (params?.status) filtered = filtered.filter(r => r.status === params.status)
      if (params?.department_id) filtered = filtered.filter(r => r.department_id === params.department_id)
      if (params?.criticality) filtered = filtered.filter(r => r.criticality === params.criticality)
      return {
        data: filtered,
        meta: {
          page: params?.page || 1,
          page_size: params?.page_size || 50,
          total: filtered.length,
          pages: 1
        }
      }
    }
  },
  getSummary: async (departmentId?: string) => {
    try {
      const url = departmentId ? `/resources/summary?department_id=${departmentId}` : '/resources/summary'
      const res = await apiClient.get<ResourceSummary>(url)
      if (res && res.total_quantity > 0) return res
      throw new Error('Fallback to demo summary')
    } catch {
      if (departmentId) {
        const filtered = localResources.filter(r => r.department_id === departmentId)
        return {
          types_count: new Set(filtered.map(r => r.resource_type)).size,
          total_quantity: filtered.reduce((acc, r) => acc + r.quantity_total, 0),
          available_quantity: filtered.reduce((acc, r) => acc + r.quantity_available, 0),
          reserved_quantity: filtered.reduce((acc, r) => acc + r.quantity_reserved, 0),
          unavailable_quantity: filtered.reduce((acc, r) => acc + (r.quantity_total - r.quantity_available - r.quantity_reserved), 0),
          critical_resources: filtered.filter(r => r.criticality === 'CRITICAL').length
        }
      }
      return DEMO_RESOURCE_SUMMARY
    }
  },
  reserve: async (resourceId: string, amount: number) => {
    try {
      return await apiClient.post<ResourceResponse>(`/resources/${resourceId}/reserve?amount=${amount}`)
    } catch {
      const res = localResources.find(r => r.resource_id === resourceId)
      if (res && res.quantity_available >= amount) {
        res.quantity_available -= amount
        res.quantity_reserved += amount
        return { ...res }
      }
      throw new Error('Insufficient resource quantity')
    }
  },
  release: async (resourceId: string, amount: number) => {
    try {
      return await apiClient.post<ResourceResponse>(`/resources/${resourceId}/release?amount=${amount}`)
    } catch {
      const res = localResources.find(r => r.resource_id === resourceId)
      if (res && res.quantity_reserved >= amount) {
        res.quantity_reserved -= amount
        res.quantity_available += amount
        return { ...res }
      }
      throw new Error('Cannot release more than reserved')
    }
  }
}
