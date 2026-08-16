import React from 'react'
import { KpiCard } from '../../../components/dashboard/KpiCard'
import { KpiSkeleton } from '../../../components/ui/Skeleton'
import { Users, Activity, Bed, Thermometer, Package } from 'lucide-react'
import { BedSummary } from '../../../api/beds'
import { ResourceSummary } from '../../../api/resources'

interface TopKpiRowProps {
  isLoading: boolean
  patientCount?: number
  admissionCount?: number
  bedsSummary?: BedSummary
  resourcesSummary?: ResourceSummary
}

export const TopKpiRow: React.FC<TopKpiRowProps> = ({
  isLoading,
  patientCount,
  admissionCount,
  bedsSummary,
  resourcesSummary
}) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => <KpiSkeleton key={i} />)}
      </div>
    )
  }

  const activePatients = patientCount ?? 0
  const activeAdmissions = admissionCount ?? 0
  const availableBeds = bedsSummary?.available ?? 0
  const availableIcu = bedsSummary?.icu_available ?? 0
  const availableResources = resourcesSummary?.available_quantity ?? 0

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <KpiCard
        title="Active Patients"
        value={activePatients}
        subtitle="Currently admitted"
        icon={Users}
        colorScheme="indigo"
      />
      <KpiCard
        title="Active Admissions"
        value={activeAdmissions}
        subtitle="Undergoing care"
        icon={Activity}
        colorScheme="cyan"
      />
      <KpiCard
        title="Available Beds"
        value={availableBeds}
        subtitle={`Out of ${bedsSummary?.total ?? 0} total`}
        icon={Bed}
        colorScheme={availableBeds > 0 ? 'emerald' : 'rose'}
      />
      <KpiCard
        title="ICU Availability"
        value={availableIcu}
        subtitle={`Out of ${bedsSummary?.icu_total ?? 0} total`}
        icon={Thermometer}
        colorScheme={availableIcu > 0 ? 'amber' : 'rose'}
      />
      <KpiCard
        title="Available Resources"
        value={availableResources}
        subtitle={`${resourcesSummary?.critical_resources ?? 0} critical items active`}
        icon={Package}
        colorScheme="indigo"
      />
    </div>
  )
}
