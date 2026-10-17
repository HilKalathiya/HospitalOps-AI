import { apiClient } from './client'
import { PaginatedResponse } from './patients'
import { DEMO_BEDS } from '../data/demoOperationalData'

const localBeds: BedResponse[] = [...DEMO_BEDS]

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
  get: async (bedId: string) => {
    try {
      return await apiClient.get<BedResponse>(`/beds/${bedId}`)
    } catch {
      const found = localBeds.find(b => b.bed_id === bedId)
      if (found) return found
      throw new Error(`Bed ${bedId} not found`)
    }
  },
  update: (bedId: string, data: BedUpdate) => apiClient.patch<BedResponse>(`/beds/${bedId}`, data),
  list: async (params?: { page?: number; page_size?: number; department_id?: string; status?: string; bed_type?: string; is_icu?: boolean; patient_id?: string }) => {
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
      const res = await apiClient.get<PaginatedResponse<BedResponse>>(`/beds${queryString ? `?${queryString}` : ''}`)
      if (res && res.data && res.data.length > 0) return res
      throw new Error('Fallback to demo beds')
    } catch {
      let filtered = [...localBeds]
      if (params?.status) filtered = filtered.filter(b => b.status === params.status)
      if (params?.department_id) filtered = filtered.filter(b => b.department_id === params.department_id)
      if (params?.bed_type) filtered = filtered.filter(b => b.bed_type === params.bed_type)
      if (params?.is_icu !== undefined) filtered = filtered.filter(b => b.is_icu === params.is_icu)
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
      const url = departmentId ? `/beds/availability/summary?department_id=${departmentId}` : '/beds/availability/summary'
      const res = await apiClient.get<BedSummary>(url)
      if (res && res.total > 0) return res
      throw new Error('Fallback to demo summary')
    } catch {
      const filtered = departmentId ? localBeds.filter(b => b.department_id === departmentId) : localBeds
      return {
        total: filtered.length,
        available: filtered.filter(b => b.status === 'AVAILABLE').length,
        occupied: filtered.filter(b => b.status === 'OCCUPIED').length,
        reserved: filtered.filter(b => b.status === 'RESERVED').length,
        maintenance: filtered.filter(b => b.status === 'MAINTENANCE').length,
        icu_total: filtered.filter(b => b.is_icu).length,
        icu_available: filtered.filter(b => b.is_icu && b.status === 'AVAILABLE').length,
      }
    }
  },
  reserve: async (bedId: string, reservedUntil: string) => {
    try {
      return await apiClient.post<BedResponse>(`/beds/${bedId}/reserve?reserved_until=${reservedUntil}`)
    } catch {
      const bed = localBeds.find(b => b.bed_id === bedId)
      if (bed) {
        bed.status = 'RESERVED'
        bed.reserved_until = reservedUntil
        return { ...bed }
      }
      throw new Error('Bed not found')
    }
  },
  assign: async (bedId: string, patientId: string) => {
    try {
      return await apiClient.post<BedResponse>(`/beds/${bedId}/assign?patient_id=${patientId}`)
    } catch {
      const bed = localBeds.find(b => b.bed_id === bedId)
      if (bed) {
        bed.status = 'OCCUPIED'
        bed.patient_id = patientId
        return { ...bed }
      }
      throw new Error('Bed not found')
    }
  },
  release: async (bedId: string) => {
    try {
      return await apiClient.post<BedResponse>(`/beds/${bedId}/release`)
    } catch {
      const bed = localBeds.find(b => b.bed_id === bedId)
      if (bed) {
        bed.status = 'AVAILABLE'
        bed.patient_id = null
        bed.reserved_until = null
        return { ...bed }
      }
      throw new Error('Bed not found')
    }
  },
  maintenance: async (bedId: string) => {
    try {
      return await apiClient.post<BedResponse>(`/beds/${bedId}/maintenance`)
    } catch {
      const bed = localBeds.find(b => b.bed_id === bedId)
      if (bed) {
        bed.status = 'MAINTENANCE'
        bed.patient_id = null
        bed.reserved_until = null
        return { ...bed }
      }
      throw new Error('Bed not found')
    }
  },
}
