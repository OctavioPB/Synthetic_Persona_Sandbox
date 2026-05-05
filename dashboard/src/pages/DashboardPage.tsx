import React from 'react'
import Eyebrow from '../components/Eyebrow'

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
}

const heroTitle: React.CSSProperties = {
  fontFamily: "'Fraunces', Georgia, serif",
  fontSize: 48,
  fontWeight: 300,
  color: '#ffffff',
  lineHeight: 1.2,
  marginBottom: 16,
}

const heroSub: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 14,
  color: 'rgba(255,255,255,0.6)',
  lineHeight: 1.75,
  maxWidth: 580,
  marginBottom: 40,
}

const statRow: React.CSSProperties = {
  display: 'flex',
  gap: 40,
  flexWrap: 'wrap',
}

const statItem: React.CSSProperties = {
  borderLeft: '2px solid var(--gold)',
  paddingLeft: 18,
}

const statValue: React.CSSProperties = {
  fontFamily: "'Fraunces', Georgia, serif",
  fontSize: 34,
  fontWeight: 300,
  color: 'var(--gold-light)',
  lineHeight: 1,
  marginBottom: 8,
}

const statLabel: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 12,
  color: 'rgba(255,255,255,0.5)',
  lineHeight: 1.55,
}

const section: React.CSSProperties = {
  maxWidth: 'var(--max-width-dashboard)',
  margin: '0 auto',
  padding: '56px 48px',
  borderBottom: '1px solid var(--primary-10)',
}

const cardGrid: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
  gap: 24,
  marginTop: 28,
}

const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius: 'var(--radius-md)',
  padding: '28px',
  boxShadow: 'var(--shadow-card)',
}

const accentBar: React.CSSProperties = {
  width: 36,
  height: 3,
  backgroundColor: 'var(--gold)',
  borderRadius: 2,
  margin: '6px 0 12px',
}

const cardTitle: React.CSSProperties = {
  fontFamily: "'Fraunces', Georgia, serif",
  fontSize: 16,
  fontWeight: 400,
  color: 'var(--dark)',
  marginBottom: 8,
}

const cardBody: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 13,
  color: '#475569',
  lineHeight: 1.7,
}

export default function DashboardPage(): React.JSX.Element {
  return (
    <div>
      {/* Hero */}
      <div style={heroStyle}>
        <div style={heroInner}>
          <h1 style={heroTitle}>
            Simulate before you <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>spend.</em>
          </h1>
          <p style={heroSub}>
            Test campaigns against AI-powered digital twins of your customer segments —
            before a single dollar reaches the ad platform.
          </p>
          <div style={statRow}>
            {[
              { value: '—', label: 'Simulation Runs' },
              { value: '—', label: 'Active Segments' },
              { value: '—', label: 'Avg. Conversion Score' },
            ].map((s) => (
              <div key={s.label} style={statItem}>
                <div style={statValue}>{s.value}</div>
                <div style={statLabel}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Getting started */}
      <div style={{ backgroundColor: 'var(--light)', padding: '0 0 48px' }}>
        <div style={section}>
          <Eyebrow>Platform Status</Eyebrow>
          <h2
            style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: 22,
              fontWeight: 300,
              color: '#0a1628',
              margin: '0 0 4px',
            }}
          >
            Sprint 1 — Infrastructure
          </h2>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 0 }}>
            Foundation services are being configured. Dashboard features will unlock as each sprint completes.
          </p>

          <div style={cardGrid}>
            {[
              { num: '01', title: 'Infrastructure', body: 'Kafka, PostgreSQL, Redis, and Qdrant are configured via Docker Compose and ready for local development.' },
              { num: '02', title: 'API Layer', body: 'FastAPI backend is live at /health. Persona and simulation endpoints will be added in Sprint 4.' },
              { num: '03', title: 'Segment Engine', body: 'Customer segment definitions, embeddings, and behavioral data pipelines are planned for Sprint 3.' },
              { num: '04', title: 'Persona AI', body: 'LLM-powered persona inference with conversion scoring will be implemented in Sprint 4.' },
            ].map(({ num, title, body }) => (
              <div key={num} style={card}>
                <div
                  style={{
                    fontFamily: "'Fraunces', Georgia, serif",
                    fontSize: 44,
                    fontWeight: 300,
                    color: '#f1f5f9',
                    lineHeight: 1,
                    marginBottom: 2,
                    userSelect: 'none',
                  }}
                >
                  {num}
                </div>
                <div style={accentBar} />
                <div style={cardTitle}>{title}</div>
                <div style={cardBody}>{body}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
