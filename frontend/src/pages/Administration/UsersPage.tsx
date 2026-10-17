import React from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { ShieldCheck, UserCheck, Key } from 'lucide-react'

interface UserItem {
  id: string
  email: string
  name: string
  role: 'ADMIN' | 'DOCTOR' | 'MANAGER' | 'NURSE' | 'ANALYST'
  department: string | null
  status: 'ACTIVE' | 'SUSPENDED'
  permissions: string[]
}

const MOCK_REGISTERED_USERS: UserItem[] = [
  {
    id: 'usr_001',
    email: 'admin@hospitalops.local',
    name: 'Administrator',
    role: 'ADMIN',
    department: null,
    status: 'ACTIVE',
    permissions: ['* (Superuser access)']
  },
  {
    id: 'usr_002',
    email: 'doctor@hospitalops.local',
    name: 'Dr. Sarah Mitchell',
    role: 'DOCTOR',
    department: 'ICU',
    status: 'ACTIVE',
    permissions: ['beds.read', 'beds.manage', 'patients.read', 'patients.write']
  },
  {
    id: 'usr_003',
    email: 'manager@hospitalops.local',
    name: 'Robert Vance',
    role: 'MANAGER',
    department: 'OPERATIONS',
    status: 'ACTIVE',
    permissions: ['beds.read', 'resources.read', 'resources.manage', 'forecasts.read']
  },
  {
    id: 'usr_004',
    email: 'nurse@hospitalops.local',
    name: 'Elena Rostova',
    role: 'NURSE',
    department: 'EMERGENCY',
    status: 'ACTIVE',
    permissions: ['beds.read', 'patients.read']
  }
]

export const UsersPage: React.FC = () => {
  return (
    <div className="flex flex-col min-h-full bg-bg text-ink">
      <TopHeader 
        title="User management & role governance" 
        subtitle="Role-based access control (RBAC), department scoping, and operational permissions"
        breadcrumbs={[{ label: 'Administration' }, { label: 'Users' }]}
      />

      <div className="p-6 sm:p-8 max-w-[1490px] w-full mx-auto space-y-6">
        
        {/* Security Overview Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="craft-surface p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-[8px] bg-accent/[0.1] border border-accent/20 flex items-center justify-center text-accent">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[9px] uppercase tracking-[0.085em] text-muted font-medium">Role System</span>
              <strong className="block text-[13px] font-[560] text-ink">Strict RBAC Enforced</strong>
            </div>
          </div>

          <div className="craft-surface p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-[8px] bg-good/[0.1] border border-good/20 flex items-center justify-center text-good">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[9px] uppercase tracking-[0.085em] text-muted font-medium">Active Profiles</span>
              <strong className="block text-[13px] font-[560] text-ink">4 Seeded System Accounts</strong>
            </div>
          </div>

          <div className="craft-surface p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-[8px] bg-white/[0.04] border border-line flex items-center justify-center text-muted">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[9px] uppercase tracking-[0.085em] text-muted font-medium">Authentication</span>
              <strong className="block text-[13px] font-[560] text-ink">JWT + HttpOnly Cookie</strong>
            </div>
          </div>
        </div>

        {/* User Accounts Table */}
        <section className="craft-surface overflow-hidden">
          <div className="p-4 border-b border-line flex items-center justify-between">
            <div>
              <h2 className="text-[12px] font-[560] text-[#e0e0e4]">
                Configured Personnel Directory
              </h2>
              <p className="text-[9.5px] text-[#777780] mt-0.5">
                Profiles governed by FastAPI authorization policies
              </p>
            </div>
            <span className="craft-tag active">ACTIVE PROFILES</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[10.5px]">
              <thead>
                <tr className="border-b border-line">
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Name / ID</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Email Address</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">System Role</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Department Scope</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4">Permissions</th>
                  <th className="text-[8px] uppercase tracking-[0.085em] text-[#777780] font-[580] py-3 px-4 text-right">Account State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {MOCK_REGISTERED_USERS.map((u) => (
                  <tr key={u.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-4 text-[#e0e0e4] font-medium">
                      <div>{u.name}</div>
                      <span className="text-[9px] font-mono text-muted block">{u.id}</span>
                    </td>
                    <td className="py-3 px-4 text-[#ababB3] font-mono text-[10px]">{u.email}</td>
                    <td className="py-3 px-4">
                      <span className="craft-tag active">{u.role}</span>
                    </td>
                    <td className="py-3 px-4 text-muted">
                      {u.department || 'Global / Unrestricted'}
                    </td>
                    <td className="py-3 px-4 text-muted text-[9.5px]">
                      {u.permissions.join(', ')}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span className="craft-tag active">Active</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

      </div>
    </div>
  )
}
