import React, { useState } from 'react'
import { useNavigate, useLocation, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiClient } from '../api/client'

export const Login: React.FC = () => {
  const [email, setEmail] = useState('admin@hospitalops.local')
  const [password, setPassword] = useState('adminpassword123')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const { isAuthenticated, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Redirect to originally requested page or dashboard
  const from = location.state?.from?.pathname || '/'

  if (isAuthenticated) {
    return <Navigate to={from} replace />
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      const response = await apiClient.post<{ access_token: string }>('/auth/login', {
        email,
        password,
      })
      await login(response.access_token)
      navigate(from, { replace: true })
    } catch (err) {
      console.error('Login error:', err)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const apiError = (err as any)?.apiError
      setError(apiError?.detail || 'Invalid email or password')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--color-bg-primary)' }}>
      <div className="w-full max-w-md p-8 rounded-2xl shadow-lg border" style={{ background: 'var(--color-bg-card)', borderColor: 'var(--color-border)' }}>
        
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-xl mb-4 shadow-sm"
            style={{ background: 'linear-gradient(135deg, var(--color-accent-primary), var(--color-accent-secondary))' }}>
            H
          </div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>
            HospitalOps AI
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Sign in to access your operational intelligence
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg text-sm bg-red-50 text-red-600 border border-red-200">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-primary)' }}>
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2"
              style={{
                background: 'var(--color-bg-primary)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-primary)',
              }}
              placeholder="you@hospitalops.local"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: 'var(--color-text-primary)' }}>
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2"
              style={{
                background: 'var(--color-bg-primary)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-primary)',
              }}
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 rounded-lg text-white font-medium shadow-sm transition-opacity hover:opacity-90 disabled:opacity-70 mt-2"
            style={{ background: 'var(--color-accent-primary)' }}
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t text-xs text-center" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
          <p>Demo accounts:</p>
          <p className="mt-1 font-mono bg-gray-50 dark:bg-gray-800 p-1 rounded inline-block">admin@hospitalops.local</p>
        </div>
      </div>
    </div>
  )
}
