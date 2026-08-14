import React, { createContext, useContext, useEffect, useState } from 'react'
import { apiClient } from '../api/client'

export interface User {
  user_id: string
  email: string
  name: string
  role: string
  department_id: string | null
  is_active: boolean
  last_login_at: string | null
  permissions: string[]
}

interface AuthContextType {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (token: string) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (permission: string) => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Load user profile when we get a token (or on mount if we had one)
  const fetchUser = async () => {
    try {
      const data = await apiClient.get<User>('/auth/me')
      setUser(data)
    } catch (error) {
      console.error('Failed to fetch user profile:', error)
      setUser(null)
      setToken(null)
    }
  }

  // Attempt initial session restore (e.g. from refresh cookie)
  useEffect(() => {
    let mounted = true

    const tryRestoreSession = async () => {
      try {
        const { access_token } = await apiClient.post<{ access_token: string }>('/auth/refresh')
        if (mounted) {
          setToken(access_token)
        }
      } catch {
        // Normal if there's no active session
      } finally {
        if (mounted) {
          setIsLoading(false)
        }
      }
    }

    tryRestoreSession()

    return () => {
      mounted = false
    }
  }, [])

  // Refetch user profile when token changes
  useEffect(() => {
    if (token) {
      fetchUser()
    } else {
      setUser(null)
    }
  }, [token])

  const login = async (newToken: string) => {
    setToken(newToken)
  }

  const logout = async () => {
    try {
      await apiClient.post('/auth/logout')
    } catch (error) {
      console.error('Logout failed:', error)
    } finally {
      setToken(null)
      setUser(null)
    }
  }

  const hasPermission = (permission: string): boolean => {
    return user?.permissions.includes(permission) ?? false
  }

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    hasPermission,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
