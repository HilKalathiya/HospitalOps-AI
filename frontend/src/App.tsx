/**
 * HospitalOps AI — Application shell
 *
 * Implements react-router-dom and authentication guards.
 */

import React from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { Login } from './pages/Login'

const Dashboard: React.FC = () => {
  const { user, logout } = useAuth()

  return (
    <main
      className="min-h-screen flex flex-col items-center justify-center px-4"
      style={{ background: 'var(--color-bg-primary)' }}
    >
      {/* Status badge */}
      <div className="mb-8 flex items-center gap-2">
        <span
          className="inline-block w-2 h-2 rounded-full animate-pulse"
          style={{ background: 'var(--color-accent-success)' }}
          aria-hidden="true"
        />
        <span
          className="text-xs font-semibold tracking-widest uppercase"
          style={{ color: 'var(--color-accent-success)' }}
        >
          System Online
        </span>
      </div>

      {/* Logo / wordmark */}
      <div className="mb-3 flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-sm"
          style={{
            background: 'linear-gradient(135deg, var(--color-accent-primary), var(--color-accent-secondary))',
          }}
          aria-hidden="true"
        >
          H
        </div>
        <h1
          className="text-3xl font-bold tracking-tight"
          style={{ color: 'var(--color-text-primary)' }}
        >
          HospitalOps AI
        </h1>
      </div>

      {/* Tagline */}
      <p
        className="text-lg mb-12"
        style={{ color: 'var(--color-text-secondary)' }}
      >
        Operational Intelligence Platform
      </p>

      {/* Foundation status card */}
      <div
        className="rounded-2xl border p-8 max-w-md w-full text-center mb-8"
        style={{
          background: 'var(--color-bg-card)',
          borderColor: 'var(--color-border)',
        }}
      >
        <div
          className="inline-block rounded-lg px-3 py-1 text-xs font-semibold mb-4"
          style={{
            background: 'rgba(59,130,246,0.12)',
            color: 'var(--color-accent-primary)',
          }}
        >
          Chunk 1.2 — Authentication & RBAC
        </div>
        <p
          className="text-sm leading-relaxed mb-4"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          Welcome, <span className="font-semibold text-blue-600 dark:text-blue-400">{user?.name}</span>
        </p>
        <div className="flex flex-col text-xs text-left gap-2 p-4 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
          <div><span className="font-semibold w-24 inline-block">Role:</span> {user?.role}</div>
          <div><span className="font-semibold w-24 inline-block">Email:</span> {user?.email}</div>
          <div><span className="font-semibold w-24 inline-block">Permissions:</span> {user?.permissions.length} total</div>
        </div>
      </div>

      <button
        onClick={logout}
        className="px-6 py-2 rounded-lg text-sm font-medium border shadow-sm transition-colors hover:bg-gray-50 dark:hover:bg-gray-800"
        style={{ color: 'var(--color-text-secondary)', borderColor: 'var(--color-border)' }}
      >
        Sign Out
      </button>
    </main>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />

          {/* Protected Routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Dashboard />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
