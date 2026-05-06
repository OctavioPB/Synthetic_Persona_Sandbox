import React, { useState } from 'react'
import { api } from '../services/api'
import { useAuthStore } from '../store/authStore'

const _AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED === 'true'

function _parseJwtUser(token: string) {
  try {
    const [, payload] = token.split('.')
    const d = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
    return { sub: d.sub as string, email: d.email as string, role: d.role as string, orgId: d.org_id as string }
  } catch { return null }
}

export default function LoginPage(): React.ReactElement {
  const setAuth = useAuthStore((s) => s.setAuth)
  const [email, setEmail] = useState('dev@localhost')
  const [role, setRole] = useState('admin')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleDevLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const resp = await api.auth.devToken({ email, role })
      const user = _parseJwtUser(resp.access_token)
      if (!user) throw new Error('Invalid token returned from server.')
      setAuth(resp.access_token, user)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed.')
    } finally {
      setLoading(false)
    }
  }

  const containerStyle: React.CSSProperties = {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--light)',
  }

  const cardStyle: React.CSSProperties = {
    background: 'var(--white)',
    borderRadius: 12,
    boxShadow: 'var(--shadow-card)',
    padding: '2.5rem 2rem',
    width: '100%',
    maxWidth: 400,
  }

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: '0.8rem',
    fontWeight: 600,
    color: 'var(--mid)',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.55rem 0.75rem',
    borderRadius: 6,
    border: '1px solid var(--primary-20)',
    background: 'var(--light)',
    color: 'var(--dark)',
    fontSize: '0.9rem',
    marginBottom: '1rem',
    boxSizing: 'border-box',
  }

  const btnStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.65rem',
    borderRadius: 6,
    border: 'none',
    background: 'var(--primary)',
    color: '#fff',
    fontWeight: 700,
    fontSize: '0.95rem',
    cursor: loading ? 'not-allowed' : 'pointer',
    opacity: loading ? 0.7 : 1,
  }

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--primary)' }}>
            Synthetic Persona Sandbox
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--mid)', marginTop: 4 }}>
            {_AUTH_REQUIRED ? 'Sign in to continue' : 'Dev login (AUTH_REQUIRED=false)'}
          </div>
        </div>

        {_AUTH_REQUIRED ? (
          <div style={{ textAlign: 'center', color: 'var(--mid)', fontSize: '0.9rem' }}>
            <p>Configure your identity provider and set</p>
            <code style={{ background: 'var(--primary-10)', padding: '2px 6px', borderRadius: 4 }}>
              VITE_AUTH_REQUIRED=true
            </code>
            <p style={{ marginTop: 12 }}>to enable SSO login.</p>
          </div>
        ) : (
          <form onSubmit={handleDevLogin}>
            <label style={labelStyle}>Email</label>
            <input
              style={inputStyle}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <label style={labelStyle}>Role</label>
            <select
              style={{ ...inputStyle, cursor: 'pointer' }}
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="admin">admin</option>
              <option value="marketer">marketer</option>
              <option value="analyst">analyst</option>
              <option value="viewer">viewer</option>
            </select>

            {error && (
              <div style={{
                color: '#e53e3e',
                fontSize: '0.82rem',
                marginBottom: '0.75rem',
                padding: '0.5rem',
                background: 'rgba(229,62,62,0.08)',
                borderRadius: 6,
              }}>
                {error}
              </div>
            )}

            <button type="submit" style={btnStyle} disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in (dev)'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
