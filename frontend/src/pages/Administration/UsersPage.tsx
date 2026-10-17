import React from 'react'
import { TopHeader } from '../../components/layout/TopHeader'
import { Badge } from '../../components/common/Badge'
import { ShieldCheck, UserCheck, Key, Lock } from 'lucide-react'

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
    <div className="flex flex-col min-h-full bg-[#F5F7F5]">
      <TopHeader 
        title="User management & role governance" 
        subtitle="Role-based access control (RBAC), department scoping, and operational permissions"
        breadcrumbs={[{ label: 'Administration' }, { label: 'User Management' }]}
      />

      <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
        
        {/* Role Matrix Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs">
            <div className="flex items-center gap-2 mb-1">
              <ShieldCheck className="w-4 h-4 text-[#176B57]" />
              <strong className="text-xs font-semibold text-[#192923]">Role-Based Access (RBAC)</strong>
            </div>
            <p className="text-xs text-[#52635B]">
              Enforced at FastAPI endpoint level via JWT claims and permission dependencies.
            </p>
          </div>

          <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs">
            <div className="flex items-center gap-2 mb-1">
              <Lock className="w-4 h-4 text-[#3A6378]" />
              <strong className="text-xs font-semibold text-[#192923]">Department Scoping</strong>
            </div>
            <p className="text-xs text-[#52635B]">
              Clinical staff access is scoped to their department (e.g. ICU, Emergency) by default.
            </p>
          </div>

          <div className="bg-white border border-[#DCE4DE] rounded-xl p-4 shadow-2xs">
            <div className="flex items-center gap-2 mb-1">
              <Key className="w-4 h-4 text-[#956316]" />
              <strong className="text-xs font-semibold text-[#192923]">Token Expiration</strong>
            </div>
            <p className="text-xs text-[#52635B]">
              Short-lived HMAC-SHA256 JWT access tokens with rotating session invalidation.
            </p>
          </div>
        </div>

        {/* User Registry Table */}
        <div className="bg-white border border-[#DCE4DE] rounded-xl shadow-2xs overflow-hidden">
          <div className="px-6 py-4 border-b border-[#E6EBE7] flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#192923] flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-[#176B57]" />
                Registered Operational Accounts
              </h2>
              <p className="text-xs text-[#52635B]">
                Accounts seeded in local authentication database for testing and operational management.
              </p>
            </div>
            <span className="text-xs font-mono text-[#52635B]">
              Total Users: <strong className="text-[#192923]">{MOCK_REGISTERED_USERS.length}</strong>
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-[#192923]">
              <thead className="bg-[#F7F9F7] border-b border-[#E6EBE7] text-[#52635B] font-semibold">
                <tr>
                  <th scope="col" className="px-6 py-3">User</th>
                  <th scope="col" className="px-6 py-3">Email Address</th>
                  <th scope="col" className="px-6 py-3">Role</th>
                  <th scope="col" className="px-6 py-3">Department Scope</th>
                  <th scope="col" className="px-6 py-3">Assigned Permissions</th>
                  <th scope="col" className="px-6 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6EBE7]">
                {MOCK_REGISTERED_USERS.map((u) => (
                  <tr key={u.id} className="hover:bg-[#F7F9F7] transition-colors">
                    <td className="px-6 py-3.5 font-medium text-[#192923]">
                      <div className="flex items-center gap-2.5">
                        <div className="w-6 h-6 rounded-full bg-[#E8F2ED] text-[#176B57] flex items-center justify-center font-bold text-2xs">
                          {u.name.charAt(0)}
                        </div>
                        <span>{u.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5 font-mono text-xs text-[#52635B]">
                      {u.email}
                    </td>
                    <td className="px-6 py-3.5">
                      <span className={`inline-block px-2 py-0.5 rounded text-2xs font-semibold ${
                        u.role === 'ADMIN' ? 'bg-[#E8F2ED] text-[#155B49]' : 'bg-[#F0F3F0] text-[#52635B]'
                      }`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-[#52635B]">
                      {u.department || 'Hospital-wide (Global)'}
                    </td>
                    <td className="px-6 py-3.5 font-mono text-xs text-[#77847D]">
                      {u.permissions.join(', ')}
                    </td>
                    <td className="px-6 py-3.5">
                      <Badge variant="success">Active</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  )
}
