import { apiClient } from './client'
import { PaginatedResponse } from './patients'

export interface BedCreate {
  department_id: string
  bed_type: 'GENERAL' | 'ICU' | 'ISOLATION' | 'EMERGENCY' | 'OTHER'
  room?: string | null
  floor?: string | null
}

export interface BedUpdate {
  status?: 'AVAILABLE' | 'OCCUPIED' | 'RESERVED' | 'MAINTENANCE' | null
  patient_id?: string | null
  reserved_until?: string | null
  room?: string | null
  floor?: string | null
}

export interface BedResponse {
  bed_id: string
  department_id: string
  bed_type: 'GENERAL' | 'ICU' | 'ISOLATION' | 'EMERGENCY' | 'OTHER'
  status: 'AVAILABLE' | 'OCCUPIED' | 'RESERVED' | 'MAINTENANCE'
  is_icu: boolean
  patient_id: string | null
  room: string | null
  floor: string | null
  reserved_until: string | null
  created_at: string
  updated_at: string
}

export interface BedSummary {
  total: number
  available: number
  occupied: number
  reserved: number
  maintenance: number
  icu_total: number
  icu_available: number
}

export const bedsApi = {
  create: (data: BedCreate) => apiClient.post<BedResponse>('/beds', data),
  get: (bedId: string) => apiClient.get<BedResponse>(`/beds/${bedId}`),
  update: (bedId: string, data: BedUpdate) => apiClient.patch<BedResponse>(`/beds/${bedId}`, data),
  list: (params?: { page?: number; page_size?: number; department_id?: string; status?: string; bed_type?: string; is_icu?: boolean; patient_id?: string }) => {
    const query = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          query.append(key, value.toString())
        }
      })
    }
    const queryString = query.toString()
    return apiClient.get<PaginatedResponse<BedResponse>>(`/beds${queryString ? `?${queryString}` : ''}`)
  },
  getSummary: (departmentId?: string) => {
    const url = departmentId ? `/beds/availability/summary?department_id=${departmentId}` : '/beds/availability/summary'
    return apiClient.get<BedSummary>(url)
  },
  reserve: (bedId: string, reservedUntil: string) => 
    apiClient.post<BedResponse>(`/beds/${bedId}/reserve?reserved_until=${reservedUntil}`),
  assign: (bedId: string, patientId: string) => 
    apiClient.post<BedResponse>(`/beds/${bedId}/assign?patient_id=${patientId}`),
  release: (bedId: string) => 
    apiClient.post<BedResponse>(`/beds/${bedId}/release`),
  maintenance: (bedId: string) => 
    apiClient.post<BedResponse>(`/beds/${bedId}/maintenance`),
}
