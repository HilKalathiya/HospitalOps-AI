import React from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export const DashboardShell: React.FC = () => {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-[#020617] text-gray-900 dark:text-gray-100 font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col h-full min-w-0">
        {/* We let individual pages render TopHeader so they can pass specific title/refresh actions */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
