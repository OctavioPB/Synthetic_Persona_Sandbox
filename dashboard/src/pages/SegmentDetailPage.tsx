import React from 'react'
import Eyebrow from '../components/Eyebrow'
import { Segment } from '../components/SegmentCard'

interface SegmentDetailPageProps {
  segment: Segment
  onBack:  () => void
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

const section: React.CSSProperties = {
  maxWidth: 'var(--max-width-dashboard)',
  margin: '0 auto',
  padding: '48px 48px',
  borderBottom: '1px solid var(--primary-10)',
}

const backBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 9,
  fontWeight: 700,
  letterSpacing: '2px',
  textTransform: 'uppercase',
  background: 'none',
  border: '1px solid rgba(255,255,255,0.2)',
  borderRadius: 6,
  color: 'rgba(255,255,255,0.5)',
  padding: '6px 12px',
  cursor: 'pointer',
  marginBottom: 24,
}

const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius: 'var(--radius-md)',
  padding: '28px',
  boxShadow: 'var(--shadow-card)',
}

const defRow: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
  gap: 16,
  marginTop: 24,
}

const defItem: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderLeft: '3px solid var(--gold)',
  borderRadius: '0 8px 8px 0',
  padding: '12px 16px',
  boxShadow: '0 1px 3px rgba(0,51,102,0.07)',
}

const defLabel: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 9,
  fontWeight: 700,
  letterSpacing: '1.5px',
  textTransform: 'uppercase',
  color: 'var(--gold)',
  marginBottom: 4,
}

const defValue: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 14,
  color: 'var(--dark)',
  fontWeight: 500,
}

const triggerBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: '1.5px',
  textTransform: 'uppercase',
  backgroundColor: 'var(--gold)',
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '9px 18px',
  cursor: 'pointer',
}

function formatDate(iso: string | null): string {
  if (!iso) return 'Never'
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function SegmentDetailPage({ segment, onBack }: SegmentDetailPageProps): React.JSX.Element {
  const { definition } = segment
  const cats = definition.category_affinities ?? []

  return (
    <div>
      {/* Hero */}
      <div style={heroStyle}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto' }}>
          <button style={backBtn} onClick={onBack}>← Back to Segments</button>
          <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 40, fontWeight: 300, color: '#fff', lineHeight: 1.2 }}>
            {segment.name.split(' ').map((word, i) =>
              i === 0
                ? <em key={i} style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>{word} </em>
                : <span key={i}>{word} </span>
            )}
          </h1>
          {segment.description && (
            <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', marginTop: 8, maxWidth: 580 }}>
              {segment.description}
            </p>
          )}
          {/* Stat row */}
          <div style={{ display: 'flex', gap: 40, marginTop: 32, flexWrap: 'wrap' }}>
            {[
              { label: 'Status',        value: segment.is_stale ? 'Stale' : 'Trained' },
              { label: 'Last Trained',  value: formatDate(segment.last_trained_at) },
              { label: 'Window',        value: `${definition.purchase_history_days}d` },
              { label: 'Categories',    value: cats.length > 0 ? cats.length.toString() : 'All' },
            ].map(({ label, value }) => (
              <div key={label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
                <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 24, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>
                  {value}
                </div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'rgba(255,255,255,0.45)', lineHeight: 1.55, marginTop: 6 }}>
                  {label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Body */}
      <div style={{ backgroundColor: 'var(--light)' }}>
        {/* Definition */}
        <div style={section}>
          <Eyebrow>Segment Definition</Eyebrow>
          <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 22, fontWeight: 300, color: '#0a1628', margin: '0 0 4px' }}>
            Demographic & behavioral filters
          </h2>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
            These filters determine which behavioral events are included in the feature matrix.
          </p>
          <div style={defRow}>
            {definition.age_range && (
              <div style={defItem}>
                <div style={defLabel}>Age Range</div>
                <div style={defValue}>{definition.age_range.min_age} – {definition.age_range.max_age} years</div>
              </div>
            )}
            {definition.geo?.city && (
              <div style={defItem}>
                <div style={defLabel}>Geography</div>
                <div style={defValue}>{definition.geo.city}{definition.geo.country ? `, ${definition.geo.country}` : ''}</div>
              </div>
            )}
            <div style={defItem}>
              <div style={defLabel}>Lookback Window</div>
              <div style={defValue}>{definition.purchase_history_days} days</div>
            </div>
            {cats.length > 0 && (
              <div style={defItem}>
                <div style={defLabel}>Category Affinities</div>
                <div style={defValue}>{cats.join(', ')}</div>
              </div>
            )}
          </div>
        </div>

        {/* Persona Explorer — affinities */}
        {cats.length > 0 && (
          <div style={section}>
            <Eyebrow>Persona Explorer</Eyebrow>
            <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 22, fontWeight: 300, color: '#0a1628', margin: '0 0 4px' }}>
              Category affinities
            </h2>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 24 }}>
              Ranked by relative strength. Position 1 = highest behavioral affinity for this segment.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {cats.map((cat, i) => {
                const pct = Math.round(100 - (i / cats.length) * 55)
                return (
                  <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{ width: 28, fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, color: 'var(--primary-30)', lineHeight: 1, flexShrink: 0, textAlign: 'right' }}>
                      {i + 1}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 500, color: 'var(--dark)' }}>{cat}</span>
                        <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>{pct}%</span>
                      </div>
                      <div style={{ height: 6, backgroundColor: 'var(--primary-10)', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{
                          width: `${pct}%`,
                          height: '100%',
                          backgroundColor: i === 0 ? 'var(--gold)' : 'var(--primary-60)',
                          borderRadius: 4,
                          transition: 'width 0.6s ease',
                        }} />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Embedding status */}
        <div style={{ ...section, borderBottom: 'none' }}>
          <Eyebrow>Persona Embedding</Eyebrow>
          <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 22, fontWeight: 300, color: '#0a1628', margin: '0 0 4px' }}>
            Qdrant vector store
          </h2>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 24 }}>
            Embeddings are computed by the <code style={{ fontFamily: 'Courier New', fontSize: 12 }}>extract_segment_data</code> Airflow DAG using the all-MiniLM-L6-v2 model.
          </p>
          <div style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
              <div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
                  {segment.is_stale
                    ? 'No embedding available — trigger the DAG to generate one.'
                    : `Embedding generated on ${formatDate(segment.last_trained_at)}.`}
                </div>
              </div>
              <button
                style={triggerBtn}
                onClick={() => alert(`Trigger extract_segment_data DAG for segment ${segment.id}`)}
              >
                {segment.is_stale ? 'Generate Embedding' : 'Re-train'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
