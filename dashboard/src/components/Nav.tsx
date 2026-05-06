import React from 'react'
import { type Page } from '../App'

interface NavProps {
  currentPage: Page
  onNavigate: (page: Page) => void
}

const navStyle: React.CSSProperties = {
  backgroundColor: 'rgba(0,51,102,0.97)',
  backdropFilter: 'blur(12px)',
  height: 52,
  position: 'sticky',
  top: 0,
  zIndex: 100,
  borderBottom: '1px solid rgba(255,255,255,0.08)',
  padding: '0 40px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
}

const appTitleStyle: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 9,
  letterSpacing: '3px',
  textTransform: 'uppercase',
  color: 'rgba(255,255,255,0.4)',
}

const navLinkBase: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: 'rgba(255,255,255,0.45)',
  cursor: 'pointer',
  fontFamily: 'var(--fb)',
  fontSize: 9,
  letterSpacing: '2px',
  textTransform: 'uppercase',
  padding: '5px 8px',
  borderRadius: 6,
  transition: 'color 0.15s',
}

const navLinkActive: React.CSSProperties = {
  color: 'var(--gold-light)',
  backgroundColor: 'rgba(201,168,76,0.12)',
}

const pages: Array<{ id: Page; label: string }> = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'segments',  label: 'Segments'  },
]

export default function Nav({ currentPage, onNavigate }: NavProps): React.JSX.Element {
  return (
    <nav style={navStyle}>
      {/* OPB Monogram */}
      <span>
        <span style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, color: '#ffffff' }}>
          O
        </span>
        <em style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, fontStyle: 'italic', color: 'var(--gold-light)' }}>
          PB
        </em>
      </span>

      {/* App title */}
      <span style={appTitleStyle}>Synthetic Persona Sandbox</span>

      {/* Nav links */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {pages.map(({ id, label }) => (
          <button
            key={id}
            style={currentPage === id ? { ...navLinkBase, ...navLinkActive } : navLinkBase}
            onClick={() => onNavigate(id)}
          >
            {label}
          </button>
        ))}
      </div>
    </nav>
  )
}
