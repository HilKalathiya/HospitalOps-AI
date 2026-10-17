import React, { useState, useEffect, useCallback } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { patientsApi, PatientResponse } from '../../api/patients'
import { admissionsApi, AdmissionResponse } from '../../api/admissions'
import { Shield, RefreshCw } from 'lucide-react'

export const PatientsPage: React.FC = () => {
  const [tab, setTab] = useState<'clinical' | 'operational'>('clinical')
  const [patients, setPatients] = useState<PatientResponse[]>([])
  const [admissions, setAdmissions] = useState<AdmissionResponse[]>([])
  const [loading, setLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const loadOperational = useCallback(async () => {
    try {
      setLoading(true)
      const [patRes, admRes] = await Promise.allSettled([
        patientsApi.list({ page: 1, page_size: 50 }),
        admissionsApi.list({ page: 1, page_size: 50 })
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
  }, [])

  useEffect(() => {
    if (tab === 'operational') {
      loadOperational()
    }
  }, [tab, loadOperational])

  const handleRefresh = () => {
    setIsRefreshing(true)
    if (tab === 'operational') {
      loadOperational()
    } else {
      setTimeout(() => setIsRefreshing(false), 300)
    }
  }

  return (
    <div className="flex flex-col min-h-full bg-bg text-ink">
      <TopHeader 
        title="Clinical prediction & cohorts" 
        subtitle="Stay-level modeling built on MIMIC-IV — not a live electronic health record"
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        breadcrumbs={[{ label: 'Clinical prediction' }]}
      />

      <div className="p-6 sm:p-8 max-w-[1490px] w-full mx-auto space-y-6">
        
        {/* Notice on MIMIC-IV Clinical Protection */}
        <div className="flex items-start gap-3 p-3.5 rounded-[7px] bg-accent/[0.04] border border-accent/[0.12] text-xs">
          <Shield className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
          <div className="text-[10px] leading-relaxed">
            <strong className="text-[#d0d3ee] font-[560] block mb-0.5">
              Local clinical research data boundary
            </strong>
            <p className="text-[#8e91a8]">
              MIMIC-IV v3.1 credentialed data is stored strictly on local disk and excluded from version control and cloud logging. This interface is for retrospective research validation and must not imply bedside clinical decision support.
            </p>
          </div>
        </div>

        {/* 4-Metric Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pb-6 border-b border-line">
          <div className="min-w-0 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Ingestion Stream
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] leading-none">
              Chunked
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Memory-bounded (5,000 stays/chunk)
            </div>
          </div>

          <div className="min-w-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Natural Key
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-accent font-mono leading-none">
              stay_id
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Unique per ICU encounter
            </div>
          </div>

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Feature Grain
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-good leading-none">
              Stay-Level
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              No cross-patient date aggregation
            </div>
          </div>

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Model Milestone
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#d7b879] leading-none">
              Next ML Chunk
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Adapter ready in backend
            </div>
          </div>
        </div>

        {/* View Selection Tabs */}
        <div className="flex items-center gap-4 border-b border-line text-[10.5px]">
          <button
            onClick={() => setTab('clinical')}
            className={`pb-2.5 font-medium transition-colors relative ${
              tab === 'clinical' ? 'text-ink font-semibold' : 'text-muted hover:text-ink'
            }`}
          >
            MIMIC-IV ICU Stays (Synthetic Layout Preview)
            {tab === 'clinical' && (
              <span className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-accent rounded-full" />
            )}
          </button>
          <button
            onClick={() => setTab('operational')}
            className={`pb-2.5 font-medium transition-colors relative ${
              tab === 'operational' ? 'text-ink font-semibold' : 'text-muted hover:text-ink'
            }`}
          >
            Live Operational Cohort (/api/v1/patients)
            {tab === 'operational' && (
              <span className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-accent rounded-full" />
            )}
          </button>
        </div>

        {tab === 'clinical' ? (
          /* Clinical MIMIC-IV Layout Worklist (Using Synthetic Review Fixtures) */
          <section className="craft-surface overflow-hidden">
            <div className="p-4 border-b border-line flex items-center justify-between">
              <div>
                <h2 className="text-[12px] font-[560] text-[#e0e0e4]">
                  ICU Stay Clinical Worklist
                </h2>
                <p className="text-[9.5px] text-[#777780] mt-0.5">
                  Synthetic test records for UI validation. Runtime clinical queries execute strictly against local MongoDB.
                </p>
              </div>
              <span className="craft-tag legacy">Synthetic Fixtures</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-[10.5px]">
                <thead>
                  <tr className="border-b border-line">
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Stay Identifier</th>
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">First Care Unit</th>
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Length of Stay (los)</th>
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Mortality Flag</th>
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4 text-right">Model Pipeline</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  <tr className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-[#e0e0e4]">SYN-STAY-3001</td>
                    <td className="py-3 px-4 text-[#ababB3]">Medical Intensive Care Unit (MICU)</td>
                    <td className="py-3 px-4 font-mono text-accent">3.62 days</td>
                    <td className="py-3 px-4"><span className="craft-tag active">Survived (0)</span></td>
                    <td className="py-3 px-4 text-right"><span className="craft-tag">Awaiting Training</span></td>
                  </tr>
                  <tr className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-[#e0e0e4]">SYN-STAY-3002</td>
                    <td className="py-3 px-4 text-[#ababB3]">Surgical Intensive Care Unit (SICU)</td>
                    <td className="py-3 px-4 font-mono text-accent">1.25 days</td>
                    <td className="py-3 px-4"><span className="craft-tag active">Survived (0)</span></td>
                    <td className="py-3 px-4 text-right"><span className="craft-tag">Awaiting Training</span></td>
                  </tr>
                  <tr className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-[#e0e0e4]">SYN-STAY-3003</td>
                    <td className="py-3 px-4 text-[#ababB3]">Coronary Care Unit (CCU)</td>
                    <td className="py-3 px-4 font-mono text-accent">7.40 days</td>
                    <td className="py-3 px-4"><span className="craft-tag legacy">Expired (1)</span></td>
                    <td className="py-3 px-4 text-right"><span className="craft-tag">Awaiting Training</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        ) : (
          /* Live Operational Cohort */
          <section className="craft-surface overflow-hidden">
            <div className="p-4 border-b border-line flex items-center justify-between">
              <h2 className="text-[12px] font-[560] text-[#e0e0e4]">
                Active Operational Cohort
              </h2>
              <span className="text-[9.5px] font-mono text-muted">
                {patients.length} Registered Patients · {admissions.length} Admissions
              </span>
            </div>

            {loading ? (
              <div className="py-12 text-center text-xs text-muted flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-accent" /> Loading operational cohorts...
              </div>
            ) : patients.length === 0 ? (
              <div className="py-12 text-center text-xs text-muted">
                Operational patient collection is empty.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[10.5px]">
                  <thead>
                    <tr className="border-b border-line">
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Patient MRN</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Gender / Age</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Severity</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {patients.map((p) => (
                      <tr key={p.patient_id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-3 px-4 text-[#e0e0e4] font-medium">
                          <div>{p.name}</div>
                          <span className="text-[9px] font-mono text-muted block">{p.patient_id}</span>
                        </td>
                        <td className="py-3 px-4 text-[#ababB3]">{p.gender}</td>
                        <td className="py-3 px-4">
                          <span className="craft-tag">{p.severity}</span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="craft-tag active">{p.admission_status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

      </div>
    </div>
  )
}
