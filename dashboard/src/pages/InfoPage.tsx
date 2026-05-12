import React, { useState } from 'react'
import Eyebrow from '../components/Eyebrow'

// ── Shared styles ─────────────────────────────────────────────────────────────

const heroStyle: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
  `,
  backgroundSize: '48px 48px',
  padding: '48px 48px 0',
}

const contentWrap: React.CSSProperties = {
  maxWidth: 'var(--max-width-dashboard)',
  margin: '0 auto',
}

const bodyWrap: React.CSSProperties = {
  maxWidth: 'var(--max-width-dashboard)',
  margin: '0 auto',
  padding: '48px 48px',
}

const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius: 12,
  padding: '32px',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  border: '1px solid var(--primary-10)',
}

const sectionTitle: React.CSSProperties = {
  fontFamily: "'Fraunces', Georgia, serif",
  fontSize: 22,
  fontWeight: 300,
  color: 'var(--dark)',
  margin: '0 0 6px',
}

const bodyText: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 14,
  color: '#475569',
  lineHeight: 1.75,
  margin: '0 0 16px',
}

// ── Tab bar (matches Analytics page) ─────────────────────────────────────────

type View = 'business' | 'engineering'

function TabBar({ active, onChange }: { active: View; onChange: (v: View) => void }): React.JSX.Element {
  const tabs: Array<{ id: View; label: string }> = [
    { id: 'business',    label: 'Business View'    },
    { id: 'engineering', label: 'Engineering View' },
  ]
  return (
    <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.1)', marginTop: 32 }}>
      {tabs.map(({ id, label }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          style={{
            background: 'none',
            border: 'none',
            borderBottom: `2px solid ${active === id ? 'var(--gold-light)' : 'transparent'}`,
            cursor: 'pointer',
            padding: '10px 20px',
            marginBottom: -1,
            fontFamily: 'var(--fb)',
            fontSize: 11,
            fontWeight: 500,
            letterSpacing: '1.5px',
            textTransform: 'uppercase',
            color: active === id ? 'var(--gold-light)' : 'rgba(255,255,255,0.4)',
            transition: 'color 0.15s',
          }}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

// ── Business View ─────────────────────────────────────────────────────────────

function CampaignFlowDiagram(): React.JSX.Element {
  const steps = [
    { n: '01', title: 'Define Segment',  sub: 'Age, geo, category affinity, purchase history'  },
    { n: '02', title: 'Build Campaign',  sub: 'Ad copy, price change, or promo stimulus'        },
    { n: '03', title: 'Run Simulation',  sub: 'LLM evaluates persona response in real time'      },
    { n: '04', title: 'Read Results',    sub: 'Sentiment, conversion score, verbatim response'  },
    { n: '05', title: 'Launch Confident', sub: 'Validated creative reaches the real channel'    },
  ]

  return (
    <div style={{ overflowX: 'auto', paddingBottom: 8 }}>
      <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, minWidth: 700 }}>
        {steps.map((s, i) => (
          <React.Fragment key={s.n}>
            <div style={{
              flex: 1,
              backgroundColor: i === 4 ? 'var(--primary)' : 'var(--light)',
              border: `1.5px solid ${i === 4 ? 'var(--primary)' : 'var(--primary-10)'}`,
              borderRadius: 10,
              padding: '20px 16px',
              textAlign: 'center',
            }}>
              <div style={{
                fontFamily: "'Fraunces', Georgia, serif",
                fontSize: 28,
                fontWeight: 300,
                color: i === 4 ? 'var(--gold-light)' : 'var(--primary-30)',
                lineHeight: 1,
                marginBottom: 8,
              }}>
                {s.n}
              </div>
              <div style={{
                fontFamily: 'var(--fb)',
                fontSize: 12,
                fontWeight: 600,
                color: i === 4 ? '#fff' : 'var(--dark)',
                marginBottom: 6,
              }}>
                {s.title}
              </div>
              <div style={{
                fontFamily: 'var(--fb)',
                fontSize: 11,
                color: i === 4 ? 'rgba(255,255,255,0.6)' : 'var(--mid)',
                lineHeight: 1.5,
              }}>
                {s.sub}
              </div>
            </div>
            {i < steps.length - 1 && (
              <div style={{ display: 'flex', alignItems: 'center', padding: '0 4px', flexShrink: 0 }}>
                <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
                  <path d="M0 8H16M16 8L10 2M16 8L10 14" stroke="var(--primary-30)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}

function ValuePillar({ icon, title, body }: { icon: string; title: string; body: string }): React.JSX.Element {
  return (
    <div style={{ ...card, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize: 28 }}>{icon}</div>
      <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 18, fontWeight: 400, color: 'var(--dark)' }}>
        {title}
      </div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.7 }}>
        {body}
      </div>
    </div>
  )
}

function BusinessView(): React.JSX.Element {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 40 }}>

      {/* What it is */}
      <div style={card}>
        <Eyebrow>What it is</Eyebrow>
        <h2 style={sectionTitle}>A simulation layer between strategy and spend</h2>
        <p style={bodyText}>
          The Synthetic Persona Sandbox is a marketing simulation platform that models how specific
          customer segments will respond to a campaign stimulus — before that campaign reaches a live
          channel. It creates AI-powered digital twins of customer segments derived from real
          behavioural data: purchase history, browsing patterns, geographic profile, and category
          affinity. Each twin is a probabilistic model of a real audience cohort, not a persona card
          on a slide deck.
        </p>
        <p style={{ ...bodyText, marginBottom: 0 }}>
          A marketer defines a target segment, selects or writes a campaign stimulus (ad copy, a
          price change, a promotional code), and runs a simulation. The platform returns a verbatim
          response from the synthetic persona, a sentiment classification, and a calibrated
          conversion score. The entire cycle runs in seconds.
        </p>
      </div>

      {/* How it works */}
      <div style={card}>
        <Eyebrow>How it works</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 24 }}>The five-step simulation cycle</h2>
        <CampaignFlowDiagram />
        <p style={{ ...bodyText, marginTop: 20, marginBottom: 0, fontSize: 12, color: 'var(--mid)' }}>
          Each step is executed in the platform. No external tools, no engineering handoff, no
          waiting for a data team to build a cohort. The loop from hypothesis to validated result
          typically takes under five minutes.
        </p>
      </div>

      {/* Business justification */}
      <div>
        <Eyebrow>Business case</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 24 }}>Why this exists</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
          <ValuePillar
            icon="⏱"
            title="Speed to insight"
            body="A/B tests require live traffic, statistical significance windows of days or weeks, and a risk of real conversion loss during the experiment. Simulations return a directional signal in seconds. Teams can iterate on 20 variants in the time a single A/B test takes to reach significance."
          />
          <ValuePillar
            icon="€"
            title="Cost before commitment"
            body="Paid media spend on a poorly matched creative is a sunk cost. This platform surfaces poor-fit stimuli before budget is allocated. The unit economics are straightforward: simulations cost milliseconds of compute; mis-targeted ad impressions cost real CPM."
          />
          <ValuePillar
            icon="🎯"
            title="Segment precision"
            body="Broad audience targeting wastes spend on segments with low propensity to convert. Simulating against tightly defined cohorts — Gen Z in Madrid, parents in Valencia — validates both the creative and the targeting before activation, reducing wasted reach."
          />
        </div>
      </div>

      {/* Use cases */}
      <div style={card}>
        <Eyebrow>Use cases</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 20 }}>Where teams apply it</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {[
            {
              title: 'Pre-launch creative validation',
              body: 'Before a campaign goes live, run each creative variant against the target segment. Identify which headline, offer, or CTA generates the highest simulated conversion score. Carry only validated variants into paid activation.',
            },
            {
              title: 'Pricing and promotion testing',
              body: "Price sensitivity varies sharply by segment. A 20% discount resonates with Gen Z deal-seekers but may erode perceived value for premium-oriented millennials. Test the discount threshold against each cohort before publishing the promotion.",
            },
            {
              title: 'Seasonal campaign planning',
              body: 'Summer launches, back-to-school, flash sales — simulate early. Build a ranked library of stimuli per segment before the campaign calendar opens. Reduce reactive decisions under deadline pressure.',
            },
            {
              title: 'New segment exploration',
              body: "Entering a new geography or demographic? Define the segment from available data, build hypotheses about what messaging will convert, and validate them before allocating budget to a channel you haven't tested against that cohort.",
            },
          ].map(({ title, body }) => (
            <div key={title} style={{
              backgroundColor: 'var(--light)',
              borderRadius: 10,
              padding: '20px 22px',
              borderLeft: '3px solid var(--gold)',
            }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)', marginBottom: 8 }}>
                {title}
              </div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.65 }}>
                {body}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Limitations */}
      <div style={{ ...card, borderLeft: '3px solid var(--gold)' }}>
        <Eyebrow>Honest framing</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 12 }}>What this platform does not replace</h2>
        <p style={bodyText}>
          Simulation is a directional filter, not a guarantee. The synthetic persona is a
          probabilistic model trained on historical behavioural data. It cannot account for
          exogenous events (news cycles, competitor moves, supply shocks), nor for the precise
          creative rendering in a native ad environment. A high conversion score in simulation
          means the creative is well-matched to the segment's modelled preferences — it does not
          mean the live campaign will hit that exact rate.
        </p>
        <p style={{ ...bodyText, marginBottom: 0 }}>
          The correct use of simulation is to eliminate obviously poor candidates before spend,
          and to rank variants for prioritised testing. It compresses the A/B testing funnel —
          it does not eliminate the need for live validation of the final winner.
        </p>
      </div>

    </div>
  )
}

// ── Engineering View ──────────────────────────────────────────────────────────

function ArchDiagram(): React.JSX.Element {
  const layers = [
    {
      label: 'Presentation',
      color: '#27B97C',
      bg: 'rgba(39,185,124,0.06)',
      border: 'rgba(39,185,124,0.25)',
      items: ['React 18 + TypeScript', 'Vite 5', 'Zustand', 'Custom hooks'],
      note: 'SPA — no SSR',
    },
    {
      label: 'API Layer',
      color: 'var(--primary)',
      bg: 'rgba(0,51,102,0.05)',
      border: 'var(--primary-30)',
      items: ['FastAPI (Python 3.11)', 'Pydantic v2', 'SQLAlchemy async', 'JWT + API Key auth'],
      note: 'REST + WebSocket',
    },
    {
      label: 'Async Jobs',
      color: '#7C4DBD',
      bg: 'rgba(124,77,189,0.06)',
      border: 'rgba(124,77,189,0.25)',
      items: ['ARQ worker', 'Redis queue', 'Simulation task runner'],
      note: 'Non-blocking simulation dispatch',
    },
    {
      label: 'Data Layer',
      color: 'var(--gold)',
      bg: 'rgba(201,168,76,0.06)',
      border: 'rgba(201,168,76,0.3)',
      items: ['PostgreSQL (primary store)', 'Redis (cache + queue)', 'Qdrant (vector store)'],
      note: 'Kafka for event ingestion',
    },
    {
      label: 'AI Layer',
      color: '#E8470A',
      bg: 'rgba(232,71,10,0.05)',
      border: 'rgba(232,71,10,0.2)',
      items: ['Anthropic Claude API', 'claude-sonnet-4-6', 'Structured JSON output'],
      note: 'Persona inference + scoring',
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {layers.map((l, i) => (
        <React.Fragment key={l.label}>
          <div style={{
            backgroundColor: l.bg,
            border: `1.5px solid ${l.border}`,
            borderRadius: 10,
            padding: '16px 20px',
            display: 'grid',
            gridTemplateColumns: '120px 1fr auto',
            alignItems: 'center',
            gap: 20,
          }}>
            <div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '2px', color: l.color, fontWeight: 700 }}>
                {l.label}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {l.items.map((item) => (
                <span key={item} style={{
                  fontFamily: "'Courier New', monospace",
                  fontSize: 12,
                  backgroundColor: 'var(--white)',
                  border: `1px solid ${l.border}`,
                  borderRadius: 5,
                  padding: '3px 9px',
                  color: 'var(--dark)',
                }}>
                  {item}
                </span>
              ))}
            </div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', whiteSpace: 'nowrap' }}>
              {l.note}
            </div>
          </div>
          {i < layers.length - 1 && (
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <svg width="16" height="14" viewBox="0 0 16 14" fill="none">
                <path d="M8 0V10M8 10L3 5M8 10L13 5" stroke="var(--primary-30)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
          )}
        </React.Fragment>
      ))}
    </div>
  )
}

function DataFlowDiagram(): React.JSX.Element {
  const nodes = [
    { id: 'browser', label: 'Browser', sub: 'React SPA', color: '#27B97C' },
    { id: 'api',     label: 'FastAPI',  sub: 'REST / WS',  color: 'var(--primary)' },
    { id: 'queue',   label: 'ARQ / Redis', sub: 'Job queue', color: '#7C4DBD' },
    { id: 'db',      label: 'PostgreSQL', sub: 'Persistence', color: 'var(--gold)' },
    { id: 'llm',     label: 'Claude API', sub: 'Inference', color: '#E8470A' },
  ]

  const flows = [
    { from: 'Browser',    to: 'FastAPI',      label: 'POST /simulate/run',      dir: '→' },
    { from: 'FastAPI',    to: 'PostgreSQL',   label: 'INSERT run (status=pending)', dir: '→' },
    { from: 'FastAPI',    to: 'ARQ / Redis',  label: 'Enqueue task',            dir: '→' },
    { from: 'ARQ / Redis', to: 'Claude API',  label: 'Persona inference call',  dir: '→' },
    { from: 'Claude API', to: 'ARQ / Redis',  label: 'Scored response JSON',    dir: '→' },
    { from: 'ARQ / Redis', to: 'PostgreSQL',  label: 'UPDATE run (status=completed)', dir: '→' },
    { from: 'Browser',    to: 'FastAPI',      label: 'WS: live progress stream', dir: '↔' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Nodes */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        {nodes.map((n) => (
          <div key={n.id} style={{
            border: `1.5px solid ${n.color}`,
            borderRadius: 8,
            padding: '10px 18px',
            backgroundColor: 'var(--white)',
            textAlign: 'center',
            minWidth: 110,
          }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: n.color }}>{n.label}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginTop: 2 }}>{n.sub}</div>
          </div>
        ))}
      </div>

      {/* Flow table */}
      <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--primary-10)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '120px 24px 140px 1fr', backgroundColor: 'var(--primary)', padding: '10px 16px', gap: 12 }}>
          {['From', '', 'To', 'Message'].map((h) => (
            <span key={h} style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '2px', color: 'rgba(255,255,255,0.5)' }}>{h}</span>
          ))}
        </div>
        {flows.map((f, i) => (
          <div key={i} style={{
            display: 'grid',
            gridTemplateColumns: '120px 24px 140px 1fr',
            padding: '10px 16px',
            gap: 12,
            backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--light)',
            alignItems: 'center',
          }}>
            <span style={{ fontFamily: "'Courier New'", fontSize: 12, color: 'var(--dark)' }}>{f.from}</span>
            <span style={{ fontFamily: "'Courier New'", fontSize: 14, color: 'var(--primary-30)', textAlign: 'center' }}>{f.dir}</span>
            <span style={{ fontFamily: "'Courier New'", fontSize: 12, color: 'var(--dark)' }}>{f.to}</span>
            <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{f.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

interface StackRow { tech: string; role: string; why: string }

function StackTable({ rows, accent }: { rows: StackRow[]; accent: string }): React.JSX.Element {
  return (
    <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--primary-10)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '160px 180px 1fr', backgroundColor: 'var(--primary)', padding: '10px 16px', gap: 16 }}>
        {['Technology', 'Role', 'Justification'].map((h) => (
          <span key={h} style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '2px', color: 'rgba(255,255,255,0.5)' }}>{h}</span>
        ))}
      </div>
      {rows.map((r, i) => (
        <div key={r.tech} style={{
          display: 'grid',
          gridTemplateColumns: '160px 180px 1fr',
          padding: '12px 16px',
          gap: 16,
          backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--light)',
          alignItems: 'start',
        }}>
          <span style={{ fontFamily: "'Courier New'", fontSize: 12, color: accent, fontWeight: 700 }}>{r.tech}</span>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>{r.role}</span>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569', lineHeight: 1.6 }}>{r.why}</span>
        </div>
      ))}
    </div>
  )
}

function EngineeringView(): React.JSX.Element {
  const frontendStack: StackRow[] = [
    { tech: 'React 18',     role: 'UI framework',        why: 'Concurrent rendering and the hooks model enable the real-time WebSocket update pattern without a class component lifecycle. Mature ecosystem with no framework lock-in.' },
    { tech: 'TypeScript',   role: 'Type safety',         why: 'All API response shapes, store slices, and component props are statically typed. Eliminates the runtime type errors that caused the stimulus_type/latency_ms issues in analytics.' },
    { tech: 'Vite 5',       role: 'Build + dev server',  why: 'Significantly faster HMR than webpack/CRA. Native ESM in development means 50ms–200ms hot-reload instead of full rebundling.' },
    { tech: 'Zustand',      role: 'Client state',        why: 'Minimal API, no boilerplate, no Provider wrapping. Auth token and campaign form state are the only global state; Zustand is proportionate to that scope. Redux would be over-engineered.' },
  ]

  const backendStack: StackRow[] = [
    { tech: 'FastAPI',        role: 'Web framework',       why: 'Native async/await, automatic OpenAPI schema generation from Pydantic models, dependency injection for auth and DB sessions. Python 3.11+ type hints propagate directly into the request/response models.' },
    { tech: 'Pydantic v2',    role: 'Data validation',     why: 'v2 rewrites the core in Rust; validation throughput is ~5-17× faster than v1. All request bodies, ORM responses, and simulation payloads are Pydantic models.' },
    { tech: 'SQLAlchemy 2',   role: 'ORM',                 why: 'Native async support via asyncpg. The 2.0 mapped_column API provides typed ORM fields without metaclass magic. Multi-tenant row isolation is enforced at the ORM query layer via org_id filters.' },
    { tech: 'ARQ',            role: 'Task queue',          why: 'Redis-backed async job queue built for asyncio. Simulation runs are dispatched as background tasks so the API call returns immediately with a run ID, and the frontend polls or streams via WebSocket.' },
    { tech: 'JWT + API keys', role: 'Auth',                why: 'Two credential types cover both human users (short-lived JWTs) and machine callers (hashed API keys with role scoping). AUTH_REQUIRED env flag allows the entire auth layer to be bypassed in development without code changes.' },
  ]

  const dataStack: StackRow[] = [
    { tech: 'PostgreSQL',  role: 'Primary datastore',    why: 'JSONB columns for stimulus and llm_metadata payloads avoid schema migrations for each new stimulus type while keeping full SQL query capability. Row-level multi-tenancy via org_id on every table.' },
    { tech: 'Redis',       role: 'Cache + queue broker',  why: 'Dual-purpose: ARQ uses it as the job queue backend, and the API uses it for short-lived response caching (segment lists, stats). Single infrastructure component for two concerns.' },
    { tech: 'Qdrant',      role: 'Vector store',         why: 'Persona embeddings are stored in Qdrant for nearest-neighbour segment lookup. Chosen over pgvector for production-grade ANN index performance at scale and native filtering on payload fields.' },
    { tech: 'Kafka',       role: 'Event ingestion',       why: 'Navigation and purchase events are high-throughput append-only streams. Kafka decouples the event producers (web app, mobile) from the segment model consumers, and provides at-least-once delivery guarantees for behavioural data.' },
  ]

  const aiStack: StackRow[] = [
    { tech: 'claude-sonnet-4-6', role: 'Persona inference', why: 'Sonnet 4.6 balances response quality with latency and cost. Opus would increase cost 5× with marginal accuracy gain on structured scoring tasks. Haiku lacks the reasoning depth needed for nuanced verbatim response generation.' },
    { tech: 'Structured output',  role: 'Scoring format',   why: 'The simulation prompt instructs Claude to return a JSON object with sentiment, likelihood_to_convert, and verbatim_response. Structured output eliminates post-processing parsing errors and enforces a stable contract between the LLM and the ORM model.' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 40 }}>

      {/* Architecture overview */}
      <div style={card}>
        <Eyebrow>Architecture</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 6 }}>Five-layer system</h2>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          The platform is a five-layer stack. Each layer has a single, well-defined responsibility.
          The presentation layer is a browser-only React SPA. The API layer is a stateless FastAPI
          service. Long-running tasks are offloaded to an ARQ worker process. Persistence is split
          across three stores by data shape. Inference is delegated entirely to the Anthropic API.
        </p>
        <ArchDiagram />
      </div>

      {/* Data flow */}
      <div style={card}>
        <Eyebrow>Data Flow</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 6 }}>Simulation request lifecycle</h2>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          A simulation run passes through six hops from browser to result. The API returns
          immediately after enqueuing the job. The browser receives live progress via a
          WebSocket connection held open for the duration of the task. The worker writes the
          final result to PostgreSQL; the frontend reads it on completion.
        </p>
        <DataFlowDiagram />
      </div>

      {/* Multi-tenancy */}
      <div style={card}>
        <Eyebrow>Security</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 12 }}>Multi-tenancy model</h2>
        <p style={{ ...bodyText, marginBottom: 0 }}>
          Every table in PostgreSQL carries an <code style={{ fontFamily: "'Courier New'", fontSize: 13, backgroundColor: 'var(--light)', padding: '1px 6px', borderRadius: 4 }}>org_id</code> UUID column.
          All queries in the ORM layer append a <code style={{ fontFamily: "'Courier New'", fontSize: 13, backgroundColor: 'var(--light)', padding: '1px 6px', borderRadius: 4 }}>WHERE org_id = :current_org</code> predicate derived from the
          JWT or API key claims. There is no shared state between organisations at the database
          layer. Role-based access is enforced in the <code style={{ fontFamily: "'Courier New'", fontSize: 13, backgroundColor: 'var(--light)', padding: '1px 6px', borderRadius: 4 }}>require(Permission.X)</code> FastAPI dependency
          injected into each route — the RBAC check runs before any DB operation is attempted.
        </p>
      </div>

      {/* Tech stack tables */}
      <div>
        <Eyebrow>Frontend stack</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 20 }}>Presentation layer</h2>
        <StackTable rows={frontendStack} accent="#27B97C" />
      </div>

      <div>
        <Eyebrow>Backend stack</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 20 }}>API and worker layer</h2>
        <StackTable rows={backendStack} accent="var(--primary-60)" />
      </div>

      <div>
        <Eyebrow>Data stack</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 20 }}>Persistence and streaming layer</h2>
        <StackTable rows={dataStack} accent="var(--gold)" />
      </div>

      <div>
        <Eyebrow>AI stack</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 20 }}>Inference layer</h2>
        <StackTable rows={aiStack} accent="#E8470A" />
      </div>

      {/* Design decisions */}
      <div style={card}>
        <Eyebrow>Design decisions</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 20 }}>Key architectural choices</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[
            {
              decision: 'Async-first API',
              detail: 'Every route in FastAPI uses async def. SQLAlchemy sessions are acquired via the async_sessionmaker with asyncpg as the PostgreSQL driver. This means a single uvicorn worker can handle many concurrent requests without blocking on I/O — critical when simulation tasks are in-flight and the WebSocket connection is open simultaneously.',
            },
            {
              decision: 'JSONB for stimulus and metadata',
              detail: 'Stimulus payloads vary by type: ad_copy has headline/body/cta fields; price_change has original_price/new_price; promo has promo_code/discount_type. Storing these in a JSONB column avoids a polymorphic table design (stimulus_ad_copy, stimulus_price_change, ...) while keeping the data queryable. The type discriminator field inside the JSON is sufficient for filtering and aggregation.',
            },
            {
              decision: 'Stateless API + Redis session',
              detail: 'The FastAPI process holds no in-memory state between requests. JWT validation is stateless by definition. The ARQ job queue and result cache live in Redis, which is external to the API process. This means the API can be scaled horizontally to multiple instances without sticky sessions or shared memory.',
            },
            {
              decision: 'LLM not in the request path for list endpoints',
              detail: 'The Claude API is only called during simulation runs — never for CRUD operations on segments or campaigns. List and detail endpoints are pure database reads. This keeps p99 latency for non-simulation endpoints under 50ms regardless of Anthropic API availability.',
            },
          ].map(({ decision, detail }) => (
            <div key={decision} style={{
              borderLeft: '3px solid var(--primary-30)',
              paddingLeft: 20,
            }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: 'var(--dark)', marginBottom: 6 }}>
                {decision}
              </div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.7 }}>
                {detail}
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function InfoPage(): React.JSX.Element {
  const [view, setView] = useState<View>('business')

  return (
    <div>
      {/* Hero */}
      <div style={heroStyle}>
        <div style={contentWrap}>
          <Eyebrow light>Platform Information</Eyebrow>
          <h1 style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 36,
            fontWeight: 300,
            color: '#fff',
            lineHeight: 1.2,
            margin: '8px 0 4px',
          }}>
            Synthetic Persona{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Sandbox</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: 0 }}>
            Business rationale and engineering reference.
          </p>
          <TabBar active={view} onChange={setView} />
        </div>
      </div>

      {/* Body */}
      <div style={{ backgroundColor: 'var(--light)', minHeight: '70vh' }}>
        <div style={bodyWrap}>
          {view === 'business'    && <BusinessView    />}
          {view === 'engineering' && <EngineeringView />}
        </div>
      </div>
    </div>
  )
}
