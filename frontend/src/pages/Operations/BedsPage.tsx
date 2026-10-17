import React, { useState, useEffect, useCallback } from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { Badge } from '../../components/common/Badge'
import { EmptyState } from '../../components/common/EmptyState'
import { Select } from '../../components/common/Select'
import { bedsApi, BedResponse, BedSummary } from '../../api/beds'
import { Filter } from 'lucide-react'

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

  const handleRelease = async (bedId: string) => {
    try {
      await bedsApi.release(bedId)
      loadData()
    } catch {
      alert('Unable to release bed.')
    }
  }

  const getStatusBadge = (status: BedResponse['status']) => {
    switch (status) {
      case 'AVAILABLE':
        return <Badge variant="success">Available</Badge>
      case 'OCCUPIED':
        return <Badge variant="warning">Occupied</Badge>
      case 'RESERVED':
        return <Badge variant="info">Reserved</Badge>
      case 'MAINTENANCE':
        return <Badge variant="danger">Maintenance</Badge>
      default:
        return <Badge variant="neutral">{status}</Badge>
    }
  }

  return (
    <div className="flex flex-col min-h-full bg-[#F5F7F5]">
      <TopHeader 
        title="Bed inventory & facility capacity" 
        subtitle="Operational bed allocation, status management, and ICU tracking"
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        breadcrumbs={[{ label: 'Operations' }, { label: 'Beds' }]}
      />

      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        
        {error && (
          <div className="p-3 bg-[#F9ECEB] border border-[#F9ECEB] text-[#A83F3D] rounded-lg text-xs font-medium">
            {error}
          </div>
        )}
        
        {/* Metric Summary Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-3 shadow-2xs">
            <span className="text-xs text-[#52635B] uppercase font-semibold block">Total Capacity</span>
            <strong className="text-lg font-semibold text-[#192923] font-mono tabular-nums">
              {summary?.total || 0}
            </strong>
          </div>
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-3 shadow-2xs">
            <span className="text-xs text-[#24704F] uppercase font-semibold block">Available</span>
            <strong className="text-lg font-semibold text-[#24704F] font-mono tabular-nums">
              {summary?.available || 0}
            </strong>
          </div>
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-3 shadow-2xs">
            <span className="text-xs text-[#956316] uppercase font-semibold block">Occupied</span>
            <strong className="text-lg font-semibold text-[#956316] font-mono tabular-nums">
              {summary?.occupied || 0}
            </strong>
          </div>
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-3 shadow-2xs">
            <span className="text-xs text-[#3A6378] uppercase font-semibold block">Reserved</span>
            <strong className="text-lg font-semibold text-[#3A6378] font-mono tabular-nums">
              {summary?.reserved || 0}
            </strong>
          </div>
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-3 shadow-2xs">
            <span className="text-xs text-[#A83F3D] uppercase font-semibold block">Maintenance</span>
            <strong className="text-lg font-semibold text-[#A83F3D] font-mono tabular-nums">
              {summary?.maintenance || 0}
            </strong>
          </div>
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-3 shadow-2xs">
            <span className="text-xs text-[#155B49] uppercase font-semibold block">ICU Available</span>
            <strong className="text-lg font-semibold text-[#155B49] font-mono tabular-nums">
              {summary?.icu_available || 0} / {summary?.icu_total || 0}
            </strong>
          </div>
        </div>

        {/* Filters Toolbar */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-[#52635B]" />
              <span className="text-xs font-semibold text-[#52635B] uppercase tracking-wider">Filters:</span>
            </div>

            <Select
              value={statusFilter}
              onChange={(val) => setStatusFilter(val)}
              options={[
                { value: '', label: 'All Statuses' },
                { value: 'AVAILABLE', label: 'Available (Ready)' },
                { value: 'OCCUPIED', label: 'Occupied' },
                { value: 'RESERVED', label: 'Reserved' },
                { value: 'MAINTENANCE', label: 'Maintenance' },
              ]}
              triggerClassName="w-36"
            />

            <Select
              value={departmentFilter}
              onChange={(val) => setDepartmentFilter(val)}
              options={[
                { value: '', label: 'All Departments' },
                { value: 'EMERGENCY', label: 'Emergency (ED)' },
                { value: 'ICU', label: 'Intensive Care Unit (ICU)' },
                { value: 'GENERAL', label: 'General Ward' },
                { value: 'SURGERY', label: 'Surgery' },
                { value: 'CARDIOLOGY', label: 'Cardiology' },
              ]}
              triggerClassName="w-48"
            />

            <label className="flex items-center gap-2 text-xs font-medium text-[#192923] cursor-pointer ml-1">
              <input
                type="checkbox"
                checked={icuOnly}
                onChange={(e) => setIcuOnly(e.target.checked)}
                className="rounded border-[#DCE4DE] text-[#176B57] focus:ring-[#3D8C79]"
              />
              <span>ICU-capable only</span>
            </label>
          </div>

          <span className="text-xs font-mono text-[#52635B]">
            Showing <strong>{beds.length}</strong> matching units
          </span>
        </div>

        {/* Table / Empty State */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl shadow-2xs overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-xs text-[#77847D]">
              Loading operational bed records from API...
            </div>
          ) : beds.length === 0 ? (
            <div className="p-8">
              <EmptyState 
                title="No Operational Bed Records"
                description="The local operational database has no bed entries matching the selected criteria. To populate with realistic simulated beds, execute the seed command."
                actionLabel="Seed Demo Operational Beds"
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
                    <th scope="col" className="px-6 py-3">Bed Identifier</th>
                    <th scope="col" className="px-6 py-3">Department</th>
                    <th scope="col" className="px-6 py-3">Bed Type</th>
                    <th scope="col" className="px-6 py-3">ICU Capability</th>
                    <th scope="col" className="px-6 py-3">Room / Floor</th>
                    <th scope="col" className="px-6 py-3">Operational Status</th>
                    <th scope="col" className="px-6 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6EBE7]">
                  {beds.map((b) => (
                    <tr key={b.bed_id} className="hover:bg-[#F7F9F7] transition-colors">
                      <td className="px-6 py-3.5 font-mono font-medium text-[#192923]">
                        {b.bed_id}
                      </td>
                      <td className="px-6 py-3.5 font-medium text-[#52635B]">
                        {b.department_id}
                      </td>
                      <td className="px-6 py-3.5 text-[#52635B]">
                        {b.bed_type}
                      </td>
                      <td className="px-6 py-3.5">
                        {b.is_icu ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#155B49] bg-[#E8F2ED] px-1.5 py-0.5 rounded">
                            Yes (ICU)
                          </span>
                        ) : (
                          <span className="text-xs text-[#77847D]">No</span>
                        )}
                      </td>
                      <td className="px-6 py-3.5 text-[#52635B] font-mono text-xs">
                        {b.room ? `Room ${b.room}` : '—'} {b.floor ? `(Fl. ${b.floor})` : ''}
                      </td>
                      <td className="px-6 py-3.5">
                        {getStatusBadge(b.status)}
                      </td>
                      <td className="px-6 py-3.5 text-right space-x-2">
                        {b.status === 'AVAILABLE' && (
                          <button
                            onClick={() => handleMaintenance(b.bed_id)}
                            className="px-2.5 py-1 text-xs font-medium text-[#A83F3D] hover:bg-[#F9ECEB] rounded border border-[#A83F3D]/20 transition-colors"
                          >
                            Set Maintenance
                          </button>
                        )}
                        {(b.status === 'OCCUPIED' || b.status === 'RESERVED') && (
                          <button
                            onClick={() => handleRelease(b.bed_id)}
                            className="px-2.5 py-1 text-xs font-medium text-[#155B49] hover:bg-[#E8F2ED] rounded border border-[#176B57]/20 transition-colors"
                          >
                            Release
                          </button>
                        )}
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
