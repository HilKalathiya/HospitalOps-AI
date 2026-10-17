import React, { useState, useEffect, useCallback } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { bedsApi, BedResponse, BedSummary } from '../../api/beds'
import { Filter, BedDouble, RefreshCw } from 'lucide-react'

export const BedsPage: React.FC = () => {
  const [beds, setBeds] = useState<BedResponse[]>([])
  const [summary, setSummary] = useState<BedSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [departmentFilter, setDepartmentFilter] = useState<string>('')
  const [icuOnly, setIcuOnly] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      setError(null)
      const [listRes, summaryRes] = await Promise.all([
        bedsApi.list({
          page: 1,
          page_size: 50,
          status: statusFilter || undefined,
          department_id: departmentFilter || undefined,
          is_icu: icuOnly ? true : undefined,
        }),
        bedsApi.getSummary(departmentFilter || undefined)
      ])
      setBeds(listRes.data)
      setSummary(summaryRes)
    } catch (err: unknown) {
      console.error('Failed to load beds:', err)
      setError('Unable to load operational bed data. Confirm backend API connection.')
    } finally {
      setLoading(false)
      setIsRefreshing(false)
    }
  }, [statusFilter, departmentFilter, icuOnly])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleRefresh = () => {
    setIsRefreshing(true)
    loadData()
  }

  const handleMaintenance = async (bedId: string) => {
    try {
      await bedsApi.maintenance(bedId)
      loadData()
    } catch {
      alert('Unable to place bed into maintenance. Only AVAILABLE beds can enter maintenance.')
    }
  }

  const getStatusTag = (status: BedResponse['status']) => {
    switch (status) {
      case 'AVAILABLE':
        return <span className="craft-tag active">Available</span>
      case 'OCCUPIED':
        return <span className="craft-tag legacy">Occupied</span>
      case 'RESERVED':
        return <span className="craft-tag" style={{ color: '#aab4ff', borderColor: 'rgba(170,180,255,0.2)' }}>Reserved</span>
      case 'MAINTENANCE':
        return <span className="craft-tag" style={{ color: '#ed9199', borderColor: 'rgba(237,145,153,0.2)' }}>Maintenance</span>
      default:
        return <span className="craft-tag">{status}</span>
    }
  }

  return (
    <div className="flex flex-col min-h-full bg-bg text-ink">
      <TopHeader 
        title="Capacity & beds" 
        subtitle="Bed inventory layout for facilities with a verified operational source"
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        breadcrumbs={[{ label: 'Capacity & beds' }]}
      />

      <div className="p-6 sm:p-8 max-w-[1490px] w-full mx-auto space-y-6">
        
        {/* Notice on Real Data Connection */}
        <div className="flex items-start gap-3 p-3.5 rounded-[7px] bg-white/[0.02] border border-line text-xs">
          <BedDouble className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
          <div className="text-[10px] leading-relaxed">
            <strong className="text-[#d0d3ee] font-[560] block mb-0.5">
              Live operational inventory
            </strong>
            <p className="text-muted">
              Inventory state is populated from the operational MongoDB collections via <code className="font-mono text-accent">/api/v1/beds</code>.
            </p>
          </div>
        </div>

        {/* 4-Metric Aligned Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pb-6 border-b border-line">
          <div className="min-w-0 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Total Capacity
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#f0f0f2] tabular-nums leading-none">
              {summary?.total ?? 0}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Operational beds
            </div>
          </div>

          <div className="min-w-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Available Beds
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-good tabular-nums leading-none">
              {summary?.available ?? 0}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Ready for admission
            </div>
          </div>

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6 pr-4">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              Occupied Beds
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-[#d7b879] tabular-nums leading-none">
              {summary?.occupied ?? 0}
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Active patient stays
            </div>
          </div>

          <div className="min-w-0 border-t pt-4 md:pt-0 md:border-t-0 md:border-l md:border-line md:pl-6">
            <div className="text-[9px] uppercase tracking-[0.085em] text-[#85858e] font-[580]">
              ICU Available
            </div>
            <div className="mt-2.5 text-[23px] tracking-[-0.055em] font-[560] text-accent tabular-nums leading-none">
              {summary?.icu_available ?? 0} <span className="text-[14px] text-muted">/ {summary?.icu_total ?? 0}</span>
            </div>
            <div className="mt-2 text-[10px] text-[#85858d]">
              Critical care ready
            </div>
          </div>
        </div>

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
            <option value="AVAILABLE">Available</option>
            <option value="OCCUPIED">Occupied</option>
            <option value="RESERVED">Reserved</option>
            <option value="MAINTENANCE">Maintenance</option>
          </select>

          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="h-7 px-2 bg-[#171719] border border-line rounded-[5px] text-ink text-[10px] focus:outline-none focus:border-accent"
          >
            <option value="">All departments</option>
            <option value="ICU">ICU</option>
            <option value="EMERGENCY">Emergency</option>
            <option value="GENERAL">General Ward</option>
            <option value="SURGERY">Surgery</option>
          </select>

          <label className="flex items-center gap-2 cursor-pointer ml-auto text-[10px] text-muted">
            <input
              type="checkbox"
              checked={icuOnly}
              onChange={(e) => setIcuOnly(e.target.checked)}
              className="rounded bg-[#171719] border-line text-accent focus:ring-0"
            />
            <span>ICU Dedicated Only</span>
          </label>
        </div>

        {/* Beds Table */}
        <section className="craft-surface overflow-hidden">
          <div className="p-4 border-b border-line flex items-center justify-between">
            <h2 className="text-[12px] font-[560] text-[#e0e0e4]">
              Bed Inventory Ledger
            </h2>
            <span className="text-[9.5px] font-mono text-muted">
              Displaying {beds.length} units
            </span>
          </div>

          {loading ? (
            <div className="py-12 text-center text-xs text-muted flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-accent" /> Loading inventory...
            </div>
          ) : error ? (
            <div className="p-6 text-center text-xs text-[#ed9199]">
              {error}
            </div>
          ) : beds.length === 0 ? (
            <div className="py-12 text-center text-xs text-muted">
              No beds found matching the selected filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[10.5px]">
                <thead>
                  <tr className="border-b border-line">
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Bed Identifier</th>
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Department</th>
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Type</th>
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Room / Floor</th>
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Status</th>
                    <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {beds.map((b) => (
                    <tr key={b.bed_id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-[#e0e0e4]">{b.bed_id}</td>
                      <td className="py-3 px-4 text-[#ababB3]">{b.department_id}</td>
                      <td className="py-3 px-4 text-[#c4c4cc]">
                        {b.bed_type} {b.is_icu && <span className="text-[8.5px] text-accent font-semibold ml-1">[ICU]</span>}
                      </td>
                      <td className="py-3 px-4 text-muted font-mono text-[9.5px]">
                        Room {b.room || '—'} · Floor {b.floor || '—'}
                      </td>
                      <td className="py-3 px-4">{getStatusTag(b.status)}</td>
                      <td className="py-3 px-4 text-right">
                        {b.status === 'AVAILABLE' ? (
                          <button
                            onClick={() => handleMaintenance(b.bed_id)}
                            className="px-2 py-1 text-[9px] bg-white/[0.04] hover:bg-white/[0.08] text-muted hover:text-ink rounded-[4px] border border-line transition-colors"
                          >
                            Set Maintenance
                          </button>
                        ) : (
                          <span className="text-[9px] text-[#55555e]">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

      </div>
    </div>
  )
}
