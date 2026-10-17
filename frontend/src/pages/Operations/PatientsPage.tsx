import React, { useState, useEffect, useCallback } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { Badge } from '../../components/common/Badge'
import { EmptyState } from '../../components/common/EmptyState'
import { Select } from '../../components/common/Select'
import { patientsApi, PatientResponse } from '../../api/patients'
import { admissionsApi, AdmissionResponse } from '../../api/admissions'
import { ShieldCheck, Filter } from 'lucide-react'

export const PatientsPage: React.FC = () => {
  const [tab, setTab] = useState<'patients' | 'admissions'>('patients')
  const [patients, setPatients] = useState<PatientResponse[]>([])
  const [admissions, setAdmissions] = useState<AdmissionResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [departmentFilter, setDepartmentFilter] = useState<string>('')

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [patRes, admRes] = await Promise.allSettled([
        patientsApi.list({ page: 1, page_size: 50, department_id: departmentFilter || undefined }),
        admissionsApi.list({ page: 1, page_size: 50, department_id: departmentFilter || undefined })
      ])

      if (patRes.status === 'fulfilled') {
        setPatients(patRes.value.data)
      }
      if (admRes.status === 'fulfilled') {
        setAdmissions(admRes.value.data)
      }
    } catch (err: unknown) {
      console.error('Failed to load operational cohorts:', err)
    } finally {
      setLoading(false)
      setIsRefreshing(false)
    }
  }, [departmentFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleRefresh = () => {
    setIsRefreshing(true)
    loadData()
  }

  const getSeverityBadge = (sev: string | null | undefined) => {
    switch (sev) {
      case 'CRITICAL':
        return <Badge variant="danger">Critical</Badge>
      case 'HIGH':
        return <Badge variant="warning">High</Badge>
      case 'MEDIUM':
        return <Badge variant="neutral">Medium</Badge>
      case 'LOW':
        return <Badge variant="success">Low</Badge>
      default:
        return <span className="text-gray-400">—</span>
    }
  }

  return (
    <div className="flex flex-col min-h-full bg-[#F5F7F5]">
      <TopHeader 
        title="Patients & admissions registry" 
        subtitle="Operational intake tracking and clinical encounter status"
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        breadcrumbs={[{ label: 'Operations' }, { label: 'Patients & Admissions' }]}
      />

      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        
        {/* Data Minimization Disclosure Banner */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-[#176B57] flex-shrink-0 mt-0.5" />
          <div className="text-xs text-[#52635B] space-y-1">
            <strong className="text-[#192923] block font-semibold">
              Data Minimization Principle & EHR Boundary Disclosure
            </strong>
            <p>
              HospitalOps AI tracks facility-level admission flow and bed assignments. In compliance with operational security and HIPAA data minimization, this platform does not record bedside telemetry, real-time vitals, or clinical progress notes. Patient records are tied strictly to operational intake events.
            </p>
          </div>
        </div>

        {/* Tab Switcher & Filter Toolbar */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTab('patients')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                tab === 'patients'
                  ? 'bg-[#176B57] text-white font-semibold'
                  : 'bg-[#F0F3F0] text-[#52635B] hover:text-[#192923]'
              }`}
            >
              Patient Cohort ({patients.length})
            </button>
            <button
              onClick={() => setTab('admissions')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                tab === 'admissions'
                  ? 'bg-[#176B57] text-white font-semibold'
                  : 'bg-[#F0F3F0] text-[#52635B] hover:text-[#192923]'
              }`}
            >
              Admission Encounters ({admissions.length})
            </button>
          </div>

          <div className="flex items-center gap-3">
            <Filter className="w-3.5 h-3.5 text-[#52635B]" />
            <Select
              value={departmentFilter}
              onChange={(val) => setDepartmentFilter(val)}
              options={[
                { value: '', label: 'All Departments' },
                { value: 'EMERGENCY', label: 'Emergency (ED)' },
                { value: 'ICU', label: 'Intensive Care Unit (ICU)' },
                { value: 'GENERAL', label: 'General Ward' },
                { value: 'SURGERY', label: 'Surgery' },
              ]}
              triggerClassName="w-48"
              align="right"
            />
          </div>
        </div>

        {/* Tables */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl shadow-2xs overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-xs text-[#77847D]">
              Querying operational registry from API...
            </div>
          ) : tab === 'patients' ? (
            patients.length === 0 ? (
              <div className="p-8">
                <EmptyState 
                  title="No Registered Patients in Local Database"
                  description="The local operational database currently contains zero patient records. You can seed synthetic demo patients using the backend CLI."
                  actionLabel="Seed Demo Patients"
                  onAction={() => {
                    alert('Run backend CLI in local terminal:\n.venv\\Scripts\\python.exe -m app.cli seed-demo')
                  }}
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-[#192923]">
                  <thead className="bg-[#F7F9F7] border-b border-[#E6EBE7] text-[#52635B] font-semibold">
                    <tr>
                      <th scope="col" className="px-6 py-3">Patient Identifier</th>
                      <th scope="col" className="px-6 py-3">Name</th>
                      <th scope="col" className="px-6 py-3">Department</th>
                      <th scope="col" className="px-6 py-3">Diagnosis Category</th>
                      <th scope="col" className="px-6 py-3">Severity</th>
                      <th scope="col" className="px-6 py-3">Status</th>
                      <th scope="col" className="px-6 py-3">Admitted At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E6EBE7]">
                    {patients.map((p) => (
                      <tr key={p.patient_id} className="hover:bg-[#F7F9F7] transition-colors">
                        <td className="px-6 py-3.5 font-mono text-[#192923]">
                          {p.patient_id}
                        </td>
                        <td className="px-6 py-3.5 font-medium text-[#192923]">
                          {p.name}
                        </td>
                        <td className="px-6 py-3.5 text-[#52635B]">
                          {p.department_id || 'General'}
                        </td>
                        <td className="px-6 py-3.5 text-[#52635B]">
                          {p.diagnosis_category || 'Unspecified'}
                        </td>
                        <td className="px-6 py-3.5">
                          {getSeverityBadge(p.severity)}
                        </td>
                        <td className="px-6 py-3.5">
                          <span className={`inline-block px-2 py-0.5 rounded text-2xs font-semibold ${
                            p.admission_status === 'ADMITTED' 
                              ? 'bg-[#EAF4EE] text-[#24704F]' 
                              : 'bg-[#F0F3F0] text-[#52635B]'
                          }`}>
                            {p.admission_status}
                          </span>
                        </td>
                        <td className="px-6 py-3.5 font-mono text-xs text-[#52635B]">
                          {p.admitted_at ? new Date(p.admitted_at).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ) : (
            admissions.length === 0 ? (
              <div className="p-8">
                <EmptyState 
                  title="No Active Admission Encounters"
                  description="The local operational database has no recorded admission records. Seed demo data to preview active admissions."
                  actionLabel="Seed Demo Admissions"
                  onAction={() => {
                    alert('Run backend CLI in local terminal:\n.venv\\Scripts\\python.exe -m app.cli seed-demo')
                  }}
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-[#192923]">
                  <thead className="bg-[#F7F9F7] border-b border-[#E6EBE7] text-[#52635B] font-semibold">
                    <tr>
                      <th scope="col" className="px-6 py-3">Admission ID</th>
                      <th scope="col" className="px-6 py-3">Patient ID</th>
                      <th scope="col" className="px-6 py-3">Department</th>
                      <th scope="col" className="px-6 py-3">Bed Assigned</th>
                      <th scope="col" className="px-6 py-3">Type</th>
                      <th scope="col" className="px-6 py-3">Severity</th>
                      <th scope="col" className="px-6 py-3">Admission Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E6EBE7]">
                    {admissions.map((a) => (
                      <tr key={a.admission_id} className="hover:bg-[#F7F9F7] transition-colors">
                        <td className="px-6 py-3.5 font-mono text-[#192923]">
                          {a.admission_id}
                        </td>
                        <td className="px-6 py-3.5 font-mono text-[#52635B]">
                          {a.patient_id}
                        </td>
                        <td className="px-6 py-3.5 text-[#52635B]">
                          {a.department_id}
                        </td>
                        <td className="px-6 py-3.5 font-mono text-[#192923]">
                          {a.bed_id || <span className="text-[#77847D]">Unallocated</span>}
                        </td>
                        <td className="px-6 py-3.5 text-xs font-semibold text-[#52635B]">
                          {a.admission_type}
                        </td>
                        <td className="px-6 py-3.5">
                          {getSeverityBadge(a.severity)}
                        </td>
                        <td className="px-6 py-3.5 font-mono text-xs text-[#52635B]">
                          {new Date(a.admitted_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </div>

      </div>
    </div>
  )
}
