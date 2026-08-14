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

export const patientsApi = {
  create: (data: PatientCreate) => apiClient.post<PatientResponse>('/patients', data),
  get: (patientId: string) => apiClient.get<PatientResponse>(`/patients/${patientId}`),
  update: (patientId: string, data: PatientUpdate) => apiClient.patch<PatientResponse>(`/patients/${patientId}`, data),
  list: (params?: { page?: number; page_size?: number; department_id?: string; status?: string; search?: string }) => {
    const query = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          query.append(key, value.toString())
        }
      })
    }
    const queryString = query.toString()
    return apiClient.get<PaginatedResponse<PatientResponse>>(`/patients${queryString ? `?${queryString}` : ''}`)
  }
}
