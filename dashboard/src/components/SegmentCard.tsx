import React from 'react'

export interface Segment {
  id: string
  name: string
  description: string | null
  definition: {
    category_affinities: string[]
    purchase_history_days: number
    age_range?: { min_age: number; max_age: number } | null
    geo?: { country?: string | null; city?: string | null } | null
  }
  is_stale: boolean
  last_trained_at: string | null
  created_at: string
}

interface SegmentCardProps {
  segment: Segment
  onView: (id: string) => void
}

const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius: 'var(--radius-md)',
  padding: '24px 28px',
  boxShadow: 'var(--shadow-card)',
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  cursor: 'pointer',
  transition: 'box-shadow 0.15s',
}

const topBar: React.CSSProperties = {
  height: 3,
  backgroundColor: 'var(--gold)',
  borderRadius: 2,
  marginBottom: 4,
}

const segmentName: React.CSSProperties = {
  fontFamily: "'Fraunces', Georgia, serif",
  fontSize: 17,
  fontWeight: 400,
  color: 'var(--dark)',
}

const meta: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 12,
  color: 'var(--mid)',
  lineHeight: 1.6,
}

const tagRow: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
  marginTop: 4,
}

const tag: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 9,
  fontWeight: 700,
  letterSpacing: '1.5px',
  textTransform: 'uppercase',
  color: 'var(--primary)',
  backgroundColor: 'var(--primary-10)',
  borderRadius: 4,
  padding: '3px 8px',
}

function StatusBadge({ stale }: { stale: boolean }): React.JSX.Element {
  const style: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 5,
    fontSize: 10,
    fontFamily: 'var(--fb)',
    fontWeight: 500,
    borderRadius: 20,
    padding: '4px 12px',
    backgroundColor: stale ? '#fef0e6' : '#e0f7ef',
    color: stale ? '#7a3800' : '#0d5c3a',
  }
  return (
    <span style={style}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: stale ? '#f07020' : '#27b97c', flexShrink: 0 }} />
      {stale ? 'Stale' : 'Trained'}
    </span>
  )
}

export default function SegmentCard({ segment, onView }: SegmentCardProps): React.JSX.Element {
  const cats = segment.definition.category_affinities ?? []
  const geo  = segment.definition.geo
  const age  = segment.definition.age_range

  return (
    <div style={card} onClick={() => onView(segment.id)} role="button" tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onView(segment.id)}>
      <div style={topBar} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <span style={segmentName}>{segment.name}</span>
        <StatusBadge stale={segment.is_stale} />
      </div>
      {segment.description && <p style={meta}>{segment.description}</p>}
      <div style={meta}>
        {age && <span>Age {age.min_age}–{age.max_age} · </span>}
        {geo?.city && <span>{geo.city}{geo.country ? `, ${geo.country}` : ''} · </span>}
        <span>Window: {segment.definition.purchase_history_days}d</span>
      </div>
      {cats.length > 0 && (
        <div style={tagRow}>
          {cats.map((c) => <span key={c} style={tag}>{c}</span>)}
        </div>
      )}
    </div>
  )
}
