import React, { useEffect, useState } from 'react'
import Eyebrow from '../components/Eyebrow'
import SegmentCard, { Segment } from '../components/SegmentCard'

interface SegmentsPageProps {
  onCreateNew: () => void
  onViewDetail: (id: string) => void
}

const heroStyle: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
  `,
  backgroundSize: '48px 48px',
  padding: '56px 48px',
}

const heroInner: React.CSSProperties = {
  maxWidth: 'var(--max-width-dashboard)',
  margin: '0 auto',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-end',
  flexWrap: 'wrap',
  gap: 24,
}

const createBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '1.5px',
  textTransform: 'uppercase',
  backgroundColor: 'var(--gold)',
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '10px 20px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
}

const section: React.CSSProperties = {
  maxWidth: 'var(--max-width-dashboard)',
  margin: '0 auto',
  padding: '56px 48px',
}

const statRow: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
  gap: 16,
  marginBottom: 48,
}

const statCard: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius: 'var(--radius-md)',
  padding: '20px 24px',
  boxShadow: 'var(--shadow-card)',
  display: 'flex',
  alignItems: 'stretch',
  gap: 16,
}

const cardGrid: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
  gap: 20,
}

const emptyState: React.CSSProperties = {
  textAlign: 'center',
  padding: '64px 0',
  fontFamily: 'var(--fb)',
  color: 'var(--mid)',
  fontSize: 14,
}

// Stub data for Sprint 3 UI; replaced by real API call in Sprint 6
const STUB_SEGMENTS: Segment[] = [
  {
    id: 'stub-001',
    name: 'Gen Z — Madrid',
    description: 'Urban young adults with high digital engagement in fashion and electronics.',
    definition: {
      age_range: { min_age: 18, max_age: 24 },
      geo: { city: 'Madrid', country: 'Spain' },
      category_affinities: ['Electronics', 'Fashion'],
      purchase_history_days: 90,
    },
    is_stale: false,
    last_trained_at: '2026-05-05T10:00:00Z',
    created_at: '2026-05-01T09:00:00Z',
  },
  {
    id: 'stub-002',
    name: 'Home Improvers — 30-45',
    description: 'Mid-career professionals investing in their living spaces.',
    definition: {
      age_range: { min_age: 30, max_age: 45 },
      geo: null,
      category_affinities: ['Home & Garden'],
      purchase_history_days: 180,
    },
    is_stale: true,
    last_trained_at: null,
    created_at: '2026-05-03T14:00:00Z',
  },
]

export default function SegmentsPage({ onCreateNew, onViewDetail }: SegmentsPageProps): React.JSX.Element {
  const [segments, setSegments] = useState<Segment[]>(STUB_SEGMENTS)
  const total    = segments.length
  const trained  = segments.filter((s) => !s.is_stale).length
  const stale    = segments.filter((s) => s.is_stale).length

  return (
    <div>
      {/* Hero */}
      <div style={heroStyle}>
        <div style={heroInner}>
          <div>
            <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 40, fontWeight: 300, color: '#fff', lineHeight: 1.2 }}>
              Customer <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Segments</em>
            </h1>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.6)', marginTop: 8 }}>
              Define the audience profiles your simulations will test against.
            </p>
          </div>
          <button style={createBtn} onClick={onCreateNew}>+ New Segment</button>
        </div>
      </div>

      {/* Body */}
      <div style={{ backgroundColor: 'var(--light)', minHeight: '60vh' }}>
        <div style={section}>
          {/* KPI row */}
          <div style={statRow}>
            {[
              { label: 'Total Segments', value: total },
              { label: 'Trained',        value: trained },
              { label: 'Stale',          value: stale },
            ].map(({ label, value }) => (
              <div key={label} style={statCard}>
                <div style={{ width: 3, backgroundColor: 'var(--gold)', borderRadius: 2, flexShrink: 0 }} />
                <div>
                  <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 32, fontWeight: 300, color: 'var(--dark)', lineHeight: 1 }}>
                    {value}
                  </div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '3px', color: 'var(--mid)', marginTop: 6 }}>
                    {label}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Segment cards */}
          <Eyebrow>All Segments</Eyebrow>
          <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 22, fontWeight: 300, color: '#0a1628', margin: '0 0 24px' }}>
            Defined audience profiles
          </h2>

          {segments.length === 0 ? (
            <div style={emptyState}>
              <p>No segments yet.</p>
              <button style={{ ...createBtn, marginTop: 16 }} onClick={onCreateNew}>Create your first segment</button>
            </div>
          ) : (
            <div style={cardGrid}>
              {segments.map((seg) => (
                <SegmentCard key={seg.id} segment={seg} onView={onViewDetail} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
