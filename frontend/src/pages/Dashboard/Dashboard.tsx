import React, { useState, useEffect, useCallback } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { TopKpiRow } from './widgets/TopKpiRow'
import { BedCapacityPanel } from './widgets/BedCapacityPanel'
import { IcuStatusPanel } from './widgets/IcuStatusPanel'
import { ResourceUtilizationPanel } from './widgets/ResourceUtilizationPanel'
import { AdmissionTrendChart } from './widgets/AdmissionTrendChart'
import { DepartmentLoadPanel } from './widgets/DepartmentLoadPanel'
import { CapacityAttentionPanel } from './widgets/CapacityAttentionPanel'
import { RecentAdmissionsTable } from './widgets/RecentAdmissionsTable'
import { BedAvailabilityTable } from './widgets/BedAvailabilityTable'

import { useAuth } from '../../context/AuthContext'
import { bedsApi, BedSummary, BedResponse } from '../../api/beds'
import { resourcesApi, ResourceSummary } from '../../api/resources'
import { admissionsApi, AdmissionResponse } from '../../api/admissions'
import { patientsApi } from '../../api/patients'

export const Dashboard: React.FC = () => {
  const { user } = useAuth()
  
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Data states
  const [patientCount, setPatientCount] = useState<number>(0)
  const [admissionCount, setAdmissionCount] = useState<number>(0)
  const [bedsSummary, setBedsSummary] = useState<BedSummary | undefined>()
  const [resourcesSummary, setResourcesSummary] = useState<ResourceSummary | undefined>()
  const [recentAdmissions, setRecentAdmissions] = useState<AdmissionResponse[]>([])
  const [allBeds, setAllBeds] = useState<BedResponse[]>([])
  const [availableBeds, setAvailableBeds] = useState<BedResponse[]>([])

  const departmentId = user?.role === 'DOCTOR' && user.department_id ? user.department_id : undefined

  const fetchDashboardData = useCallback(async () => {
    try {
      setError(null)
      
      const [
        patientsRes,
        admissionsRes,
        bedsSumRes,
        resSumRes,
        recentAdmRes,
        allBedsRes,
        availBedsRes
      ] = await Promise.all([
        patientsApi.list({ page_size: 1 }), // Just for total count
        admissionsApi.list({ page_size: 1, department_id: departmentId }), 
        bedsApi.getSummary(departmentId),
        resourcesApi.getSummary(departmentId),
        admissionsApi.list({ page_size: 30, department_id: departmentId }), // 30 for the trend chart, slice 5 for table
        bedsApi.list({ page_size: 100, department_id: departmentId }), // For department load
        bedsApi.list({ status: 'AVAILABLE', page_size: 5, department_id: departmentId }) // For availability table
      ])

      setPatientCount(patientsRes.meta.total)
      setAdmissionCount(admissionsRes.meta.total)
      setBedsSummary(bedsSumRes)
      setResourcesSummary(resSumRes)
      setRecentAdmissions(recentAdmRes.data)
      setAllBeds(allBedsRes.data)
      setAvailableBeds(availBedsRes.data)

    } catch (err: unknown) {
      console.error('Failed to fetch dashboard data:', err)
      setError('Failed to load operational data. Please try refreshing.')
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [departmentId])

  useEffect(() => {
    fetchDashboardData()
  }, [fetchDashboardData])

  const handleRefresh = () => {
    setIsRefreshing(true)
    fetchDashboardData()
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-[#020617]">
      <TopHeader 
        title="Hospital Operations" 
        subtitle={user?.role === 'DOCTOR' ? `Department: ${user.department_id}` : 'Hospital-wide Overview'} 
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />
      
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl flex items-center justify-between">
            <span>{error}</span>
            <button onClick={handleRefresh} className="px-3 py-1 bg-white rounded-md text-sm font-medium border border-rose-200 shadow-sm hover:bg-rose-50">
              Retry
            </button>
          </div>
        )}

        {/* Top KPIs */}
        <TopKpiRow 
          isLoading={isLoading} 
          patientCount={patientCount} 
          admissionCount={admissionCount}
          bedsSummary={bedsSummary}
          resourcesSummary={resourcesSummary}
        />

        {/* First main row */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2">
            <BedCapacityPanel isLoading={isLoading} summary={bedsSummary} />
          </div>
          <div className="xl:col-span-1">
            <IcuStatusPanel isLoading={isLoading} summary={bedsSummary} />
          </div>
        </div>

        {/* Second main row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-1">
            <ResourceUtilizationPanel isLoading={isLoading} summary={resourcesSummary} />
          </div>
          <div className="xl:col-span-1">
            <AdmissionTrendChart isLoading={isLoading} admissions={recentAdmissions} />
          </div>
          <div className="xl:col-span-1">
            <DepartmentLoadPanel isLoading={isLoading} beds={allBeds} />
          </div>
        </div>

        {/* Third row: Tables and Attention */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <CapacityAttentionPanel 
              isLoading={isLoading} 
              bedsSummary={bedsSummary} 
              resourcesSummary={resourcesSummary} 
            />
          </div>
          <div className="lg:col-span-1">
            <RecentAdmissionsTable isLoading={isLoading} admissions={recentAdmissions.slice(0, 5)} />
          </div>
          <div className="lg:col-span-1">
            <BedAvailabilityTable isLoading={isLoading} beds={availableBeds} />
          </div>
        </div>
        
      </div>
    </div>
  )
}
