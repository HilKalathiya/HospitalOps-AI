import React from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

interface ProtectedRouteProps {
  requiredPermission?: string
  requiredRole?: string
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  requiredPermission,
  requiredRole,
}) => {
  const { isAuthenticated, isLoading, user, hasPermission } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--color-bg-primary)' }}>
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-t-blue-500 rounded-full animate-spin" style={{ borderColor: 'var(--color-border)', borderTopColor: 'var(--color-accent-primary)' }}></div>
          <p style={{ color: 'var(--color-text-secondary)' }}>Loading session...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    // Redirect to login page but save the attempted URL
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requiredRole && user?.role !== requiredRole) {
    // Optionally redirect to a specific "Unauthorized" page or return a simple message
    return (
      <div className="min-h-screen flex items-center justify-center p-4 text-center" style={{ background: 'var(--color-bg-primary)' }}>
        <div className="rounded-xl border p-8 max-w-md w-full" style={{ background: 'var(--color-bg-card)', borderColor: 'var(--color-border)' }}>
          <h2 className="text-xl font-bold mb-2 text-red-500">Access Denied</h2>
          <p style={{ color: 'var(--color-text-secondary)' }}>You do not have the required role ({requiredRole}) to view this page.</p>
        </div>
      </div>
    )
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 text-center" style={{ background: 'var(--color-bg-primary)' }}>
        <div className="rounded-xl border p-8 max-w-md w-full" style={{ background: 'var(--color-bg-card)', borderColor: 'var(--color-border)' }}>
          <h2 className="text-xl font-bold mb-2 text-red-500">Permission Denied</h2>
          <p style={{ color: 'var(--color-text-secondary)' }}>You do not have the required permission ({requiredPermission}) to perform this action.</p>
        </div>
      </div>
    )
  }

  return <Outlet />
}
