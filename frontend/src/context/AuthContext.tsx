import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import api from '../api/client'

interface AuthContextValue {
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem('token')
  )

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<{ access_token: string }>('/auth/login', {
      email,
      password,
    })
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
  }, [])

  const register = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<{ access_token: string }>('/auth/register', {
      email,
      password,
    })
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
