import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const API = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'
const TOKEN_KEY = 'cc_token'

export interface User {
  id: number
  firstName: string | null
  lastName: string | null
  name: string
  email: string
  createdAt: string
}

interface SignupInput {
  firstName: string
  lastName: string
  email: string
  password: string
  confirmPassword: string
}

interface AuthValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (input: SignupInput) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

/** Reads the error message the API sends, falling back to something readable. */
async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') return body.detail
  } catch {
    /* response had no JSON body */
  }
  return fallback
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Restore the session on load if a token is already in localStorage.
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setLoading(false)
      return
    }
    fetch(`${API}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('invalid session'))))
      .then((u: User) => setUser(u))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthValue>(
    () => ({
      user,
      loading,

      async login(email, password) {
        const res = await fetch(`${API}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        })
        if (!res.ok) throw new Error(await readError(res, 'Could not log in.'))
        const data = (await res.json()) as { token: string; user: User }
        localStorage.setItem(TOKEN_KEY, data.token)
        setUser(data.user)
      },

      async signup(input) {
        const res = await fetch(`${API}/api/auth/signup`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(input),
        })
        if (!res.ok) throw new Error(await readError(res, 'Could not create the account.'))
        const data = (await res.json()) as { token: string; user: User }
        localStorage.setItem(TOKEN_KEY, data.token)
        setUser(data.user)
      },

      async logout() {
        const token = localStorage.getItem(TOKEN_KEY)
        localStorage.removeItem(TOKEN_KEY)
        setUser(null)
        if (token) {
          await fetch(`${API}/api/auth/logout`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
          }).catch(() => undefined)
        }
      },
    }),
    [user, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
