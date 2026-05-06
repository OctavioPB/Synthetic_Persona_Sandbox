import { create } from 'zustand'

export interface AuthUser {
  sub: string
  email: string
  role: string
  orgId: string
}

interface AuthState {
  token: string | null
  user: AuthUser | null
  setAuth: (token: string, user: AuthUser) => void
  clearAuth: () => void
}

function _parseJwtPayload(token: string): AuthUser | null {
  try {
    const [, payload] = token.split('.')
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
    return {
      sub: decoded.sub as string,
      email: decoded.email as string,
      role: decoded.role as string,
      orgId: decoded.org_id as string,
    }
  } catch {
    return null
  }
}

const _STORAGE_KEY = 'spb_auth_token'

function _loadPersistedToken(): { token: string | null; user: AuthUser | null } {
  try {
    const raw = localStorage.getItem(_STORAGE_KEY)
    if (!raw) return { token: null, user: null }
    const user = _parseJwtPayload(raw)
    if (!user) return { token: null, user: null }
    return { token: raw, user }
  } catch {
    return { token: null, user: null }
  }
}

const _persisted = _loadPersistedToken()

export const useAuthStore = create<AuthState>()((set) => ({
  token: _persisted.token,
  user: _persisted.user,

  setAuth: (token, user) => {
    try { localStorage.setItem(_STORAGE_KEY, token) } catch { /* ignore */ }
    set({ token, user })
  },

  clearAuth: () => {
    try { localStorage.removeItem(_STORAGE_KEY) } catch { /* ignore */ }
    set({ token: null, user: null })
  },
}))
