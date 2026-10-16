import React, { createContext, useContext, useEffect, useState } from 'react'
import { apiClient, setAccessToken } from '../api/client'

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

  // Load user profile when we get a token
  const fetchUser = async (authToken?: string) => {
    try {
      if (authToken) {
        setAccessToken(authToken)
      }
      const data = await apiClient.get<User>('/auth/me')
      setUser(data)
      return data
    } catch (error) {
      console.error('Failed to fetch user profile:', error)
      setUser(null)
      setToken(null)
      setAccessToken(null)
      return null
    }
  }

  // Attempt initial session restore (e.g. from refresh cookie)
  useEffect(() => {
    let mounted = true

    const tryRestoreSession = async () => {
      try {
        const { access_token } = await apiClient.post<{ access_token: string }>('/auth/refresh')
        if (mounted && access_token) {
          setAccessToken(access_token)
          setToken(access_token)
          const profile = await apiClient.get<User>('/auth/me')
          if (mounted) {
            setUser(profile)
          }
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

  const login = async (newToken: string) => {
    setAccessToken(newToken)
    setToken(newToken)
    const userProfile = await fetchUser(newToken)
    if (!userProfile) {
      throw new Error('Could not load user profile')
    }
  }

  const logout = async () => {
    try {
      await apiClient.post('/auth/logout')
    } catch (error) {
      console.error('Logout failed:', error)
    } finally {
      setAccessToken(null)
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
    isLoading: isLoading || (!!token && !user),
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
