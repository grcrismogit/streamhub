import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setAuthToken, setUnauthorizedHandler, type User } from '../api'

const STORAGE_KEY = 'streamhub.session'

interface Session {
  token: string
  expiresAt: number // epoch ms
  user: User
}

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const session = JSON.parse(raw) as Session
    if (!session.token || session.expiresAt <= Date.now()) return null
    return session
  } catch {
    return null
  }
}

function writeSession(session: Session | null) {
  try {
    if (session) localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* modo privado / almacenamiento bloqueado: la sesión vive solo en memoria */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => {
    const s = readSession()
    setAuthToken(s?.token ?? null) // disponible desde el primer render
    return s
  })

  const applySession = useCallback((s: Session | null) => {
    setAuthToken(s?.token ?? null)
    writeSession(s)
    setSession(s)
  }, [])

  const logout = useCallback(() => applySession(null), [applySession])

  // Si la API responde 401 (token vencido), cerramos sesión automáticamente.
  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(null)
  }, [logout])

  // Cierre automático al llegar la expiración del token.
  useEffect(() => {
    if (!session) return
    const timeout = window.setTimeout(logout, Math.max(0, session.expiresAt - Date.now()))
    return () => window.clearTimeout(timeout)
  }, [session, logout])

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login(email, password)
      applySession({
        token: res.access_token,
        expiresAt: Date.now() + res.expires_in * 1000,
        user: res.user,
      })
    },
    [applySession],
  )

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      await api.register({ name, email, password })
      await login(email, password)
    },
    [login],
  )

  const refreshUser = useCallback(async () => {
    const current = readSession()
    if (!current) return
    const user = await api.me()
    applySession({ ...current, user })
  }, [applySession])

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      isAuthenticated: Boolean(session),
      login,
      register,
      logout,
      refreshUser,
    }),
    [session, login, register, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// oxlint-disable-next-line react/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}
