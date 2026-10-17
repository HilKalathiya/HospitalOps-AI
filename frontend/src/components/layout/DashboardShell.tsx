import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export const DashboardShell: React.FC = () => {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden bg-[#171717] text-[#f0f0f1] font-sans antialiased">
      <Sidebar 
        mobileOpen={mobileSidebarOpen} 
        onCloseMobile={() => setMobileSidebarOpen(false)} 
      />
      
      <div 
        className="flex-1 flex flex-col h-full min-w-0 overflow-hidden"
        style={{
          background: 'radial-gradient(ellipse 68% 55% at 72% -12%, rgba(95, 106, 180, 0.055), transparent 75%), #171717'
        }}
      >
        <main className="flex-1 overflow-y-auto flex flex-col">
          <Outlet context={{ toggleMobileMenu: () => setMobileSidebarOpen(prev => !prev) }} />
        </main>
      </div>
    </div>
  )
}
