import { apiClient } from './client'
import { PaginatedResponse } from './patients'

export interface AdmissionCreate {
  patient_id: string
  department_id: string
  bed_id?: string | null
  admission_type: 'EMERGENCY' | 'ELECTIVE' | 'TRANSFER' | 'OTHER'
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  icu_required?: boolean
  admitted_at?: string
  notes?: string | null
}

export interface AdmissionUpdate {
  bed_id?: string | null
  severity?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null
  icu_required?: boolean | null
  status?: 'ACTIVE' | 'DISCHARGED' | 'CANCELLED' | null
  discharged_at?: string | null
  notes?: string | null
}

export interface AdmissionResponse {
  admission_id: string
  patient_id: string
  department_id: string
  bed_id: string | null
  admission_type: 'EMERGENCY' | 'ELECTIVE' | 'TRANSFER' | 'OTHER'
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  emergency: boolean
  icu_required: boolean
  admitted_at: string
  discharged_at: string | null
  status: 'ACTIVE' | 'DISCHARGED' | 'CANCELLED'
  notes: string | null
  created_at: string
  updated_at: string
}

import { DEMO_ADMISSIONS } from '../data/demoOperationalData'

const localAdmissions: AdmissionResponse[] = [...DEMO_ADMISSIONS]

export const admissionsApi = {
  create: (data: AdmissionCreate) => apiClient.post<AdmissionResponse>('/admissions', data),
  get: async (admissionId: string) => {
    try {
      return await apiClient.get<AdmissionResponse>(`/admissions/${admissionId}`)
    } catch {
      const found = localAdmissions.find(a => a.admission_id === admissionId)
      if (found) return found
      throw new Error(`Admission ${admissionId} not found`)
    }
  },
  update: (admissionId: string, data: AdmissionUpdate) => apiClient.patch<AdmissionResponse>(`/admissions/${admissionId}`, data),
  list: async (params?: { page?: number; page_size?: number; department_id?: string; patient_id?: string; status?: string }) => {
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
      const res = await apiClient.get<PaginatedResponse<AdmissionResponse>>(`/admissions${queryString ? `?${queryString}` : ''}`)
      if (res && res.data && res.data.length > 0) return res
      throw new Error('Fallback to demo admissions')
    } catch {
      let filtered = [...localAdmissions]
      if (params?.department_id) filtered = filtered.filter(a => a.department_id === params.department_id)
      if (params?.patient_id) filtered = filtered.filter(a => a.patient_id === params.patient_id)
      if (params?.status) filtered = filtered.filter(a => a.status === params.status)
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
  }
}
