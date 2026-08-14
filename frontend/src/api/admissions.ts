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

export const admissionsApi = {
  create: (data: AdmissionCreate) => apiClient.post<AdmissionResponse>('/admissions', data),
  get: (admissionId: string) => apiClient.get<AdmissionResponse>(`/admissions/${admissionId}`),
  update: (admissionId: string, data: AdmissionUpdate) => apiClient.patch<AdmissionResponse>(`/admissions/${admissionId}`, data),
  list: (params?: { page?: number; page_size?: number; department_id?: string; patient_id?: string; status?: string }) => {
    const query = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          query.append(key, value.toString())
        }
      })
    }
    const queryString = query.toString()
    return apiClient.get<PaginatedResponse<AdmissionResponse>>(`/admissions${queryString ? `?${queryString}` : ''}`)
  }
}
