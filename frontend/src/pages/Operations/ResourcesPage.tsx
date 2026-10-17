import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { TopHeader } from '../../components/layout/TopHeader'
import { resourcesApi, ResourceResponse, ResourceSummary } from '../../api/resources'
import { Sliders, Filter, ArrowRight, RefreshCw } from 'lucide-react'

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

  const getStatusTag = (status: ResourceResponse['status']) => {
    switch (status) {
      case 'OPERATIONAL':
        return <span className="craft-tag active">Operational</span>
      case 'MAINTENANCE':
        return <span className="craft-tag" style={{ color: '#e8c182', borderColor: 'rgba(232,193,130,0.2)' }}>Maintenance</span>
      case 'OUT_OF_SERVICE':
        return <span className="craft-tag" style={{ color: '#ed9199', borderColor: 'rgba(237,145,153,0.2)' }}>Out of Service</span>
      default:
        return <span className="craft-tag">{status}</span>
    }
  }

  const hasData = resources.length > 0

  return (
    <div className="flex flex-col min-h-full bg-bg text-ink">
      <TopHeader 
        title="Resources" 
        subtitle="Equipment inventory and demand planning without invented telemetry"
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        breadcrumbs={[{ label: 'Resources' }]}
      />

      <div className="p-6 sm:p-8 max-w-[1490px] w-full mx-auto space-y-6">
        
        {/* 4-Metric Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pb-6 border-b border-line">
          <div className="min-w-0 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Total Resources
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
              {summary?.total_quantity ?? 0}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Tracked units
            </div>
          </div>

          <div className="min-w-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Operational Available
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-good tabular-nums leading-none">
              {summary?.available_quantity ?? 0}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Ready for allocation
            </div>
          </div>

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Reserved Units
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#d7b879] tabular-nums leading-none">
              {summary?.reserved_quantity ?? 0}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Allocated to patients
            </div>
          </div>

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Critical Level
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-accent tabular-nums leading-none">
              {summary?.critical_resources ?? 0}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              High priority assets
            </div>
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-xs text-muted flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-accent" /> Loading equipment inventory...
          </div>
        ) : hasData ? (
          <>
            {/* Filter Controls Toolbar */}
            <div className="flex flex-wrap items-center gap-3 p-3 bg-white/[0.018] border border-line rounded-[8px] text-[10.5px]">
              <span className="flex items-center gap-1.5 text-muted font-medium">
                <Filter className="w-3.5 h-3.5" /> Filter:
              </span>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-7 px-2 bg-[#171719] border border-line rounded-[5px] text-ink text-[10px] focus:outline-none focus:border-accent"
              >
                <option value="">All statuses</option>
                <option value="OPERATIONAL">Operational</option>
                <option value="MAINTENANCE">Maintenance</option>
                <option value="OUT_OF_SERVICE">Out of Service</option>
              </select>

              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="h-7 px-2 bg-[#171719] border border-line rounded-[5px] text-ink text-[10px] focus:outline-none focus:border-accent"
              >
                <option value="">All asset types</option>
                <option value="VENTILATOR">Ventilators</option>
                <option value="INFUSION_PUMP">Infusion Pumps</option>
                <option value="DIALYSIS_MACHINE">Dialysis Machines</option>
                <option value="DEFIBRILLATOR">Defibrillators</option>
              </select>
            </div>

            {/* Resources Table */}
            <section className="craft-surface overflow-hidden">
              <div className="p-4 border-b border-line flex items-center justify-between">
                <h2 className="text-[12px] font-[560] text-[#e0e0e4]">
                  Resource Inventory Ledger
                </h2>
                <span className="text-[9.5px] font-mono text-muted">
                  Displaying {resources.length} assets
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-[10.5px]">
                  <thead>
                    <tr className="border-b border-line">
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Asset ID</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Name</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Type</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Availability</th>
                      <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {resources.map((r) => (
                      <tr key={r.resource_id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-3 px-4 font-mono font-medium text-[#e0e0e4]">{r.resource_id}</td>
                        <td className="py-3 px-4 text-[#ababB3]">{r.name}</td>
                        <td className="py-3 px-4 text-[#c4c4cc] font-mono text-[9.5px]">{r.resource_type}</td>
                        <td className="py-3 px-4 tabular-nums text-muted">
                          {r.quantity_available} / {r.quantity_total}
                        </td>
                        <td className="py-3 px-4">{getStatusTag(r.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : (
          /* Unconnected / Unseeded Empty State Specimen */
          <section className="craft-surface min-h-[340px] grid place-items-center text-center p-8 sm:p-12">
            <div className="max-w-[420px]">
              <div className="w-11 h-11 border border-line-strong rounded-[10px] grid place-items-center mx-auto mb-4 text-accent bg-white/[0.025]">
                <Sliders className="w-5 h-5" />
              </div>
              <div className="text-[16px] tracking-[-0.04em] font-[560] text-ink">
                Resource inventory is not connected
              </div>
              <p className="text-[11px] text-[#8b8b94] leading-relaxed my-3 mb-5">
                When an approved operational source or live telemetry feed is configured, this workspace will display equipment availability, utilization, maintenance windows, and predicted equipment demand.
              </p>
              <Link 
                to="/datasets"
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-[6px] bg-gradient-to-b from-[#b0baff] to-[#98a5f8] text-[#14151b] font-[620] text-[10.5px] shadow-[0_2px_9px_rgba(90,103,214,0.12)] hover:bg-[#c0c7ff] transition-all"
              >
                Review data sources <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </section>
        )}

      </div>
    </div>
  )
}
