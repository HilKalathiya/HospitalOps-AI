import React, { useState, useEffect, useCallback } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { Badge } from '../../components/common/Badge'
import { EmptyState } from '../../components/common/EmptyState'
import { Select } from '../../components/common/Select'
import { resourcesApi, ResourceResponse, ResourceSummary } from '../../api/resources'
import { Filter } from 'lucide-react'

export const ResourcesPage: React.FC = () => {
  const [resources, setResources] = useState<ResourceResponse[]>([])
  const [summary, setSummary] = useState<ResourceSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')

  const loadData = useCallback(async () => {
    try {
      const [listRes, sumRes] = await Promise.all([
        resourcesApi.list({
          page: 1,
          page_size: 50,
          resource_type: typeFilter || undefined,
          status: statusFilter || undefined
        }),
        resourcesApi.getSummary()
      ])
      setResources(listRes.data)
      setSummary(sumRes)
    } catch (err: unknown) {
      console.error('Failed to load resources:', err)
    } finally {
      setLoading(false)
      setIsRefreshing(false)
    }
  }, [typeFilter, statusFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleRefresh = () => {
    setIsRefreshing(true)
    loadData()
  }

  const getStatusBadge = (status: ResourceResponse['status']) => {
    switch (status) {
      case 'OPERATIONAL':
        return <Badge variant="success">Operational</Badge>
      case 'MAINTENANCE':
        return <Badge variant="warning">Maintenance</Badge>
      case 'OUT_OF_SERVICE':
        return <Badge variant="danger">Out of Service</Badge>
      default:
        return <Badge variant="neutral">{status}</Badge>
    }
  }

  const getCriticalityBadge = (crit: ResourceResponse['criticality']) => {
    switch (crit) {
      case 'CRITICAL':
        return <Badge variant="danger">Critical</Badge>
      case 'HIGH':
        return <Badge variant="warning">High</Badge>
      case 'MEDIUM':
        return <Badge variant="neutral">Medium</Badge>
      case 'LOW':
        return <Badge variant="neutral">Low</Badge>
      default:
        return null
    }
  }

  return (
    <div className="flex flex-col min-h-full bg-[#F5F7F5]">
      <TopHeader 
        title="Resource allocation & equipment inventory" 
        subtitle="Operational inventory of ventilators, monitors, and critical clinical equipment"
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        breadcrumbs={[{ label: 'Operations' }, { label: 'Resources' }]}
      />

      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        
        {/* Metric Summary Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs">
            <span className="text-xs text-[#52635B] uppercase font-semibold block">Total Fleet Count</span>
            <strong className="text-xl font-semibold text-[#192923] font-mono tabular-nums">
              {summary?.total_quantity || 0}
            </strong>
          </div>
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs">
            <span className="text-xs text-[#24704F] uppercase font-semibold block">Operational / Available</span>
            <strong className="text-xl font-semibold text-[#24704F] font-mono tabular-nums">
              {summary?.available_quantity || 0}
            </strong>
          </div>
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs">
            <span className="text-xs text-[#956316] uppercase font-semibold block">Reserved Allocation</span>
            <strong className="text-xl font-semibold text-[#956316] font-mono tabular-nums">
              {summary?.reserved_quantity || 0}
            </strong>
          </div>
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs">
            <span className="text-xs text-[#A83F3D] uppercase font-semibold block">Critical Resources</span>
            <strong className="text-xl font-semibold text-[#A83F3D] font-mono tabular-nums">
              {summary?.critical_resources || 0}
            </strong>
          </div>
        </div>

        {/* Filter bar */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-[#52635B]" />
              <span className="text-xs font-semibold text-[#52635B] uppercase tracking-wider">Filters:</span>
            </div>

            <Select
              value={typeFilter}
              onChange={(val) => setTypeFilter(val)}
              options={[
                { value: '', label: 'All Equipment Types' },
                { value: 'VENTILATOR', label: 'Ventilators (Invasive/NIV)' },
                { value: 'MONITOR', label: 'Monitors (Telemetry)' },
                { value: 'OXYGEN', label: 'Oxygen Delivery' },
                { value: 'STAFFING', label: 'Clinical Staffing' },
                { value: 'EQUIPMENT', label: 'Specialized Equipment' },
              ]}
              triggerClassName="w-48"
            />

            <Select
              value={statusFilter}
              onChange={(val) => setStatusFilter(val)}
              options={[
                { value: '', label: 'All Operational Statuses' },
                { value: 'OPERATIONAL', label: 'Operational' },
                { value: 'MAINTENANCE', label: 'Under Maintenance' },
                { value: 'OUT_OF_SERVICE', label: 'Out of Service' },
              ]}
              triggerClassName="w-48"
            />
          </div>

          <span className="text-xs font-mono text-[#52635B]">
            Showing <strong>{resources.length}</strong> equipment categories
          </span>
        </div>

        {/* Inventory Table / Empty State */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl shadow-2xs overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-xs text-[#77847D]">
              Loading operational resource inventory from API...
            </div>
          ) : resources.length === 0 ? (
            <div className="p-8">
              <EmptyState 
                title="No Operational Equipment Records"
                description="The local operational database has no resource catalog entries. Seed local demo equipment via backend CLI."
                actionLabel="Seed Demo Operational Equipment"
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
                    <th scope="col" className="px-6 py-3">Resource / Model Name</th>
                    <th scope="col" className="px-6 py-3">Type</th>
                    <th scope="col" className="px-6 py-3">Department</th>
                    <th scope="col" className="px-6 py-3 text-right">Total Units</th>
                    <th scope="col" className="px-6 py-3 text-right">Available</th>
                    <th scope="col" className="px-6 py-3 text-right">Reserved</th>
                    <th scope="col" className="px-6 py-3">Criticality</th>
                    <th scope="col" className="px-6 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6EBE7]">
                  {resources.map((r) => (
                    <tr key={r.resource_id} className="hover:bg-[#F7F9F7] transition-colors">
                      <td className="px-6 py-3.5 font-medium text-[#192923]">
                        <span className="font-semibold block">{r.name}</span>
                        <span className="text-2xs text-[#77847D] font-mono">ID: {r.resource_id}</span>
                      </td>
                      <td className="px-6 py-3.5 font-mono text-xs text-[#52635B]">
                        {r.resource_type}
                      </td>
                      <td className="px-6 py-3.5 text-[#52635B]">
                        {r.department_id || 'Hospital-wide'}
                      </td>
                      <td className="px-6 py-3.5 text-right font-mono font-semibold text-[#192923] tabular-nums">
                        {r.quantity_total} {r.unit || ''}
                      </td>
                      <td className="px-6 py-3.5 text-right font-mono font-semibold text-[#24704F] tabular-nums">
                        {r.quantity_available}
                      </td>
                      <td className="px-6 py-3.5 text-right font-mono text-[#956316] tabular-nums">
                        {r.quantity_reserved}
                      </td>
                      <td className="px-6 py-3.5">
                        {getCriticalityBadge(r.criticality)}
                      </td>
                      <td className="px-6 py-3.5">
                        {getStatusBadge(r.status)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
