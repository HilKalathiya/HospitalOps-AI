import { apiClient } from './client'

export interface PatientCreate {
  name: string
  external_patient_id?: string | null
  date_of_birth?: string | null
  gender?: 'MALE' | 'FEMALE' | 'OTHER' | 'UNKNOWN'
  diagnosis_category?: string | null
  severity?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null
  department_id?: string | null
  icu_required?: boolean
}

export interface PatientUpdate {
  diagnosis_category?: string | null
  severity?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null
  department_id?: string | null
  icu_required?: boolean | null
  admission_status?: 'ADMITTED' | 'DISCHARGED' | 'DECEASED' | null
  admitted_at?: string | null
  discharged_at?: string | null
}

export interface PatientResponse {
  patient_id: string
  external_patient_id: string | null
  name: string
  date_of_birth: string | null
  gender: 'MALE' | 'FEMALE' | 'OTHER' | 'UNKNOWN'
  diagnosis_category: string | null
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null
  department_id: string | null
  icu_required: boolean
  admission_status: 'ADMITTED' | 'DISCHARGED' | 'DECEASED'
  admitted_at: string | null
  discharged_at: string | null
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: {
    page: number
    page_size: number
    total: number
    pages: number
  }
}

import { DEMO_PATIENTS } from '../data/demoOperationalData'

const localPatients: PatientResponse[] = [...DEMO_PATIENTS]

export const patientsApi = {
  create: (data: PatientCreate) => apiClient.post<PatientResponse>('/patients', data),
  get: async (patientId: string) => {
    try {
      return await apiClient.get<PatientResponse>(`/patients/${patientId}`)
    } catch {
      const found = localPatients.find(p => p.patient_id === patientId)
      if (found) return found
      throw new Error(`Patient ${patientId} not found`)
    }
  },
  update: (patientId: string, data: PatientUpdate) => apiClient.patch<PatientResponse>(`/patients/${patientId}`, data),
  list: async (params?: { page?: number; page_size?: number; department_id?: string; status?: string; search?: string }) => {
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
      const res = await apiClient.get<PaginatedResponse<PatientResponse>>(`/patients${queryString ? `?${queryString}` : ''}`)
      if (res && res.data && res.data.length > 0) return res
      throw new Error('Fallback to demo patients')
    } catch {
      let filtered = [...localPatients]
      if (params?.department_id) filtered = filtered.filter(p => p.department_id === params.department_id)
      if (params?.status) filtered = filtered.filter(p => p.admission_status === params.status)
      if (params?.search) {
        const q = params.search.toLowerCase()
        filtered = filtered.filter(p => p.name.toLowerCase().includes(q) || p.patient_id.toLowerCase().includes(q))
      }
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
