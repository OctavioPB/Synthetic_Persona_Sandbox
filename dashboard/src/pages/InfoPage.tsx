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

const inlineCode: React.CSSProperties = {
  fontFamily: "'Courier New', monospace",
  fontSize: 13,
  backgroundColor: 'var(--light)',
  padding: '1px 6px',
  borderRadius: 4,
  color: 'var(--primary-60)',
}

// ── Tab bar ───────────────────────────────────────────────────────────────────

type View = 'business' | 'engineering'

function TabBar({ active, onChange }: { active: View; onChange: (v: View) => void }): React.JSX.Element {
  const tabs: Array<{ id: View; label: string }> = [
    { id: 'business',    label: 'Business View'    },
    { id: 'engineering', label: 'Engineering View' },
  ]
  return (
    <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.1)', marginTop: 32 }}>
      {tabs.map(({ id, label }) => (
        <button key={id} onClick={() => onChange(id)} style={{
          background: 'none', border: 'none',
          borderBottom: `2px solid ${active === id ? 'var(--gold-light)' : 'transparent'}`,
          cursor: 'pointer', padding: '10px 20px', marginBottom: -1,
          fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 500,
          letterSpacing: '1.5px', textTransform: 'uppercase',
          color: active === id ? 'var(--gold-light)' : 'rgba(255,255,255,0.4)',
          transition: 'color 0.15s',
        }}>
          {label}
        </button>
      ))}
    </div>
  )
}

// =============================================================================
// BUSINESS VIEW
// =============================================================================

function CampaignFlowDiagram(): React.JSX.Element {
  const steps = [
    { n: '01', title: 'Define Segment',   sub: 'Age, geo, category affinity, purchase history'  },
    { n: '02', title: 'Build Campaign',   sub: 'Ad copy, price change, or promo stimulus'        },
    { n: '03', title: 'Run Simulation',   sub: 'LLM evaluates persona response in real time'     },
    { n: '04', title: 'Read Results',     sub: 'Sentiment, conversion score, verbatim response'  },
    { n: '05', title: 'Launch Confident', sub: 'Validated creative reaches the real channel'     },
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
              borderRadius: 10, padding: '20px 16px', textAlign: 'center',
            }}>
              <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 28, fontWeight: 300, color: i === 4 ? 'var(--gold-light)' : 'var(--primary-30)', lineHeight: 1, marginBottom: 8 }}>
                {s.n}
              </div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 600, color: i === 4 ? '#fff' : 'var(--dark)', marginBottom: 6 }}>
                {s.title}
              </div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: i === 4 ? 'rgba(255,255,255,0.6)' : 'var(--mid)', lineHeight: 1.5 }}>
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

function ComparisonTable(): React.JSX.Element {
  const rows = [
    { approach: 'Live A/B test',     time: '2 – 4 weeks',  cost: 'High (real media spend)', risk: 'Live conversion loss during test', signal: 'Statistically reliable' },
    { approach: 'Focus group',       time: '1 – 2 weeks',  cost: 'Medium-high',             risk: 'Moderator bias, small N',          signal: 'Qualitative only'       },
    { approach: 'Survey panel',      time: '3 – 7 days',   cost: 'Medium',                  risk: 'Self-report bias',                 signal: 'Intent, not behaviour'  },
    { approach: 'Synthetic simulation', time: 'Seconds',   cost: 'Minimal (compute)',       risk: 'None',                             signal: 'Directional (scored)'   },
  ]
  const cols = ['Approach', 'Time to signal', 'Cost', 'Risk', 'Signal quality']
  return (
    <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--primary-10)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr 1.4fr 1.2fr', backgroundColor: 'var(--primary)', padding: '10px 16px', gap: 12 }}>
        {cols.map((h) => (
          <span key={h} style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '2px', color: 'rgba(255,255,255,0.55)' }}>{h}</span>
        ))}
      </div>
      {rows.map((r, i) => (
        <div key={r.approach} style={{
          display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr 1.4fr 1.2fr',
          padding: '12px 16px', gap: 12,
          backgroundColor: i === 3 ? 'rgba(201,168,76,0.06)' : i % 2 === 0 ? 'var(--white)' : 'var(--light)',
          borderLeft: i === 3 ? '3px solid var(--gold)' : '3px solid transparent',
          alignItems: 'start',
        }}>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: i === 3 ? 700 : 400, color: i === 3 ? 'var(--dark)' : '#475569' }}>{r.approach}</span>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: i === 3 ? '#22943a' : '#475569', fontWeight: i === 3 ? 600 : 400 }}>{r.time}</span>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: i === 3 ? '#22943a' : '#475569', fontWeight: i === 3 ? 600 : 400 }}>{r.cost}</span>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: i === 3 ? '#22943a' : '#475569', fontWeight: i === 3 ? 600 : 400 }}>{r.risk}</span>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569' }}>{r.signal}</span>
        </div>
      ))}
    </div>
  )
}

function StimulusGuide(): React.JSX.Element {
  const types = [
    {
      type: 'Ad Copy',
      color: 'var(--primary)',
      bg: 'rgba(0,51,102,0.05)',
      border: 'var(--primary-30)',
      fields: ['Headline', 'Body copy', 'Call to action'],
      tests: 'Message framing, emotional register, CTA phrasing, value proposition clarity.',
      example: '"Discover Your Next Favourite — Exclusive for You" + Shop Now',
    },
    {
      type: 'Price Change',
      color: 'var(--gold)',
      bg: 'rgba(201,168,76,0.06)',
      border: 'rgba(201,168,76,0.4)',
      fields: ['Product name', 'Original price', 'New price'],
      tests: 'Price sensitivity by segment, discount threshold, perceived value erosion.',
      example: 'Wireless Headphones Pro: €129.99 → €89.99',
    },
    {
      type: 'Promotion',
      color: '#27B97C',
      bg: 'rgba(39,185,124,0.06)',
      border: 'rgba(39,185,124,0.3)',
      fields: ['Promo code', 'Discount value', 'Discount type (% or fixed)', 'Expiry window'],
      tests: 'Urgency response, discount type preference (% vs fixed), code-based vs automatic.',
      example: 'SUMMER20 — 20% off, expires in 7 days',
    },
  ]
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
      {types.map((t) => (
        <div key={t.type} style={{ backgroundColor: t.bg, border: `1.5px solid ${t.border}`, borderRadius: 10, padding: '20px' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '2px', color: t.color, marginBottom: 12 }}>{t.type}</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>Fields</div>
          <ul style={{ margin: '0 0 12px', padding: '0 0 0 16px' }}>
            {t.fields.map((f) => (
              <li key={f} style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569', marginBottom: 2 }}>{f}</li>
            ))}
          </ul>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 4, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>Tests</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569', lineHeight: 1.6, marginBottom: 10 }}>{t.tests}</div>
          <div style={{ fontFamily: "'Courier New'", fontSize: 11, color: t.color, backgroundColor: 'var(--white)', borderRadius: 6, padding: '6px 10px', lineHeight: 1.5 }}>{t.example}</div>
        </div>
      ))}
    </div>
  )
}

function StakeholderMap(): React.JSX.Element {
  const stakeholders = [
    {
      role: 'CMO / VP Marketing',
      accent: 'var(--primary)',
      gets: 'Budget confidence before commitment. Replaces gut-feel campaign approvals with scored evidence. Can compare 10 creative directions in a single afternoon.',
      uses: 'Strategic variant review, segment prioritisation, pre-board briefing data.',
    },
    {
      role: 'Campaign Manager',
      accent: 'var(--gold)',
      gets: 'A ranked shortlist of the strongest variants, ready to brief into creative production or activate directly. Removes weeks of internal debate about which version to run.',
      uses: 'Daily simulation runs, A/B candidate filtering, copy iteration.',
    },
    {
      role: 'Media Buyer',
      accent: '#27B97C',
      gets: 'Segment-stimulus fit validation before activating paid inventory. Reduces wasted impressions by ensuring the creative matches the audience\'s modelled preferences.',
      uses: 'Audience targeting review, placement-copy alignment checks.',
    },
    {
      role: 'Data Scientist',
      accent: '#7C4DBD',
      gets: 'A testbed for segment hypothesis validation. Define a segment, run simulations, compare conversion score distributions across stimuli to understand which behavioral signals drive response.',
      uses: 'Segment definition refinement, feature importance analysis, model calibration.',
    },
  ]
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      {stakeholders.map((s) => (
        <div key={s.role} style={{ ...card, borderLeft: `3px solid ${s.accent}`, padding: '20px 24px' }}>
          <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 16, fontWeight: 400, color: 'var(--dark)', marginBottom: 4 }}>{s.role}</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569', lineHeight: 1.65, marginBottom: 10 }}>{s.gets}</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: 4 }}>How they use it</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569', fontStyle: 'italic' }}>{s.uses}</div>
        </div>
      ))}
    </div>
  )
}

function ScoreInterpretation(): React.JSX.Element {
  const bands = [
    { range: '0.65 – 1.00', label: 'Strong fit',    color: '#22943a', bg: 'rgba(34,148,58,0.08)',   text: 'The stimulus resonates strongly with the segment\'s modelled preferences. High priority for paid activation.' },
    { range: '0.40 – 0.64', label: 'Moderate fit',  color: '#b07d10', bg: 'rgba(176,125,16,0.08)',  text: 'Some alignment but not compelling. Refine the offer, adjust the CTA, or test a different price point before committing.' },
    { range: '0.00 – 0.39', label: 'Poor fit',      color: '#b03535', bg: 'rgba(176,53,53,0.08)',   text: 'The stimulus does not match the segment\'s current needs or preferences. Do not activate without significant rework.' },
  ]
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {bands.map((b) => (
        <div key={b.range} style={{ display: 'grid', gridTemplateColumns: '120px 120px 1fr', alignItems: 'center', gap: 16, backgroundColor: b.bg, border: `1px solid ${b.color}22`, borderRadius: 8, padding: '14px 18px' }}>
          <div style={{ fontFamily: "'Courier New'", fontSize: 14, fontWeight: 700, color: b.color }}>{b.range}</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: b.color, textTransform: 'uppercase', letterSpacing: '1.5px' }}>{b.label}</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.6 }}>{b.text}</div>
        </div>
      ))}
      <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginTop: 4, lineHeight: 1.6 }}>
        The conversion score is a probability estimate (0–1) calibrated against the segment's modelled purchase behaviour. It is directional — use it to rank and filter variants, not as a precise revenue forecast. The verbatim response and sentiment classification provide the qualitative context behind the number.
      </p>
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
          customer segments will respond to a campaign stimulus before that campaign reaches a live
          channel. It creates AI-powered digital twins of customer segments derived from real
          behavioural data: purchase history, browsing patterns, geographic profile, and category
          affinity. Each twin is a probabilistic model of a real audience cohort, not a persona card
          on a slide deck.
        </p>
        <p style={bodyText}>
          A marketer defines a target segment, selects or writes a campaign stimulus (ad copy, a
          price change, a promotional code), and runs a simulation. The platform returns a verbatim
          response from the synthetic persona, a sentiment classification, and a calibrated
          conversion score. The entire cycle runs in seconds.
        </p>
        <p style={{ ...bodyText, marginBottom: 0 }}>
          The platform sits between campaign strategy and media activation. It is not a creative
          production tool and not a media buying platform. It is the validation step that currently
          does not exist in most marketing workflows — the moment between "we have an idea" and "we
          spend money testing it on real audiences."
        </p>
      </div>

      {/* The problem */}
      <div style={card}>
        <Eyebrow>The problem</Eyebrow>
        <h2 style={sectionTitle}>Why current methods are insufficient</h2>
        <p style={bodyText}>
          Marketing teams face a compounding set of constraints that make campaign validation
          progressively harder. Third-party cookie deprecation has degraded the audience signal
          quality that behavioural targeting relied on. Rising CPMs across programmatic channels
          mean the cost of a poorly performing campaign is higher than it was three years ago.
          Privacy regulations have restricted the data available for lookalike modelling.
        </p>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          At the same time, the standard validation methods — A/B testing, focus groups, survey
          panels — have not changed. They remain slow, expensive, or subject to the biases that
          come from artificial testing environments. The table below shows where simulation fits
          relative to existing approaches.
        </p>
        <ComparisonTable />
        <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginTop: 16, lineHeight: 1.6 }}>
          Synthetic simulation is not a replacement for live A/B testing. It is a pre-filter that
          reduces the candidate set before live testing begins — eliminating obvious losers before
          they consume media budget, and surfacing the two or three variants worth testing in
          production.
        </p>
      </div>

      {/* How it works */}
      <div style={card}>
        <Eyebrow>How it works</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 24 }}>The five-step simulation cycle</h2>
        <CampaignFlowDiagram />
        <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginTop: 20, lineHeight: 1.65 }}>
          Each step is executed in the platform. No external tools, no engineering handoff, no
          waiting for a data team to build a cohort. The loop from hypothesis to validated result
          typically takes under five minutes.
        </p>
      </div>

      {/* Stimulus types */}
      <div style={card}>
        <Eyebrow>Stimulus types</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 6 }}>What you can test</h2>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          The platform supports three stimulus types, each designed to test a different dimension
          of campaign performance. A single simulation run takes one stimulus and evaluates it
          against one segment. Campaigns can group multiple variants for ranked comparison.
        </p>
        <StimulusGuide />
      </div>

      {/* Reading results */}
      <div style={card}>
        <Eyebrow>Reading results</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 6 }}>How to interpret a simulation output</h2>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          Each simulation returns three outputs: a conversion score (0–1), a sentiment
          classification (positive / neutral / negative), and a verbatim persona response. The
          score is the primary ranking signal. The verbatim response explains the reasoning behind
          the score — it tells you why a creative resonates or fails, not just whether it does.
        </p>
        <ScoreInterpretation />
      </div>

      {/* Stakeholder map */}
      <div style={card}>
        <Eyebrow>Who uses it</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 6 }}>Value by stakeholder</h2>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          The platform serves different roles in a marketing organisation. The value proposition
          differs depending on what decisions each role owns.
        </p>
        <StakeholderMap />
      </div>

      {/* Use cases */}
      <div style={card}>
        <Eyebrow>Use cases</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 20 }}>Where teams apply it</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {[
            {
              title: 'Pre-launch creative validation',
              body: 'Before a campaign goes live, run each creative variant against the target segment. Identify which headline, offer, or CTA generates the highest simulated conversion score. Carry only the top two or three variants into paid activation — eliminating the rest before any budget is committed.',
            },
            {
              title: 'Pricing and promotion testing',
              body: 'Price sensitivity varies sharply by segment. A 20% discount resonates with Gen Z deal-seekers but may erode perceived value for premium-oriented millennials. Test the discount threshold and discount type (percentage vs fixed amount) against each cohort. The verbatim response shows whether the offer reads as generous or as a signal of poor quality.',
            },
            {
              title: 'Seasonal campaign planning',
              body: 'Summer launches, back-to-school, flash sales — simulate early. Build a ranked library of validated stimuli per segment before the campaign calendar opens, replacing reactive last-minute creative decisions with a pre-tested inventory of campaign-ready variants.',
            },
            {
              title: 'New segment exploration',
              body: 'Entering a new geography or demographic? Define the segment from available data signals, build hypotheses about what messaging will convert, and simulate before allocating budget to a channel you have not previously tested against that cohort. Fail cheaply in simulation rather than expensively in market.',
            },
            {
              title: 'Creative brief validation',
              body: 'Before briefing an agency, simulate the creative direction to validate the strategic hypothesis. If the simulated persona responds poorly to the emotional register or value framing in the brief, the brief needs revision — not the finished creative work, which costs significantly more to rework.',
            },
            {
              title: 'Cross-segment stimulus matching',
              body: 'Run the same stimulus across multiple segments to identify which cohorts it resonates with most strongly. A single ad copy variant may perform very differently for Gen Z in Madrid versus parents in Valencia. Use the score distribution across segments to inform targeting decisions.',
            },
          ].map(({ title, body }) => (
            <div key={title} style={{ backgroundColor: 'var(--light)', borderRadius: 10, padding: '20px 22px', borderLeft: '3px solid var(--gold)' }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)', marginBottom: 8 }}>{title}</div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.65 }}>{body}</div>
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
          exogenous events — news cycles, competitor moves, supply shocks — nor for the precise
          creative rendering in a native ad environment, where format, placement context, and
          surrounding content all affect response. A high conversion score in simulation means
          the creative is well-matched to the segment's modelled preferences. It does not mean
          the live campaign will hit that exact conversion rate.
        </p>
        <p style={bodyText}>
          The model reflects the segment's behaviour up to the last training date. Rapid shifts
          in consumer sentiment or market conditions that post-date the training data will not be
          captured. The <strong>is_stale</strong> flag on each segment indicates when a model has
          not been updated recently and its predictions should be treated with lower confidence.
        </p>
        <p style={{ ...bodyText, marginBottom: 0 }}>
          The correct use of simulation is to eliminate obviously poor candidates before spend
          and to rank variants for prioritised live testing. It compresses the A/B testing
          funnel — it does not eliminate the need for live validation of the final winner.
        </p>
      </div>

    </div>
  )
}

// =============================================================================
// ENGINEERING VIEW
// =============================================================================

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
      note: 'Non-blocking dispatch',
    },
    {
      label: 'Data Layer',
      color: 'var(--gold)',
      bg: 'rgba(201,168,76,0.06)',
      border: 'rgba(201,168,76,0.3)',
      items: ['PostgreSQL (primary)', 'Redis (cache + queue)', 'Qdrant (vectors)', 'Kafka (events)'],
      note: 'Persistence + streaming',
    },
    {
      label: 'AI Layer',
      color: '#E8470A',
      bg: 'rgba(232,71,10,0.05)',
      border: 'rgba(232,71,10,0.2)',
      items: ['Anthropic Claude API', 'claude-sonnet-4-6', 'Structured JSON output'],
      note: 'Persona inference',
    },
  ]
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {layers.map((l, i) => (
        <React.Fragment key={l.label}>
          <div style={{
            backgroundColor: l.bg, border: `1.5px solid ${l.border}`, borderRadius: 10,
            padding: '16px 20px', display: 'grid', gridTemplateColumns: '120px 1fr auto',
            alignItems: 'center', gap: 20,
          }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '2px', color: l.color, fontWeight: 700 }}>{l.label}</div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {l.items.map((item) => (
                <span key={item} style={{ fontFamily: "'Courier New', monospace", fontSize: 12, backgroundColor: 'var(--white)', border: `1px solid ${l.border}`, borderRadius: 5, padding: '3px 9px', color: 'var(--dark)' }}>
                  {item}
                </span>
              ))}
            </div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', whiteSpace: 'nowrap' }}>{l.note}</div>
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

function SimulationLifecycleDiagram(): React.JSX.Element {
  const steps = [
    { actor: 'Browser',     action: 'POST /simulate/run',                      detail: 'segment_id + stimulus payload',               color: '#27B97C' },
    { actor: 'FastAPI',     action: 'INSERT simulation_runs (status=pending)', detail: 'Returns run_id immediately to client',         color: 'var(--primary)' },
    { actor: 'FastAPI',     action: 'Enqueue ARQ task',                        detail: 'task_id = run_id pushed to Redis queue',       color: 'var(--primary)' },
    { actor: 'ARQ Worker',  action: 'Dequeue + fetch segment',                 detail: 'Reads segment definition from PostgreSQL',     color: '#7C4DBD' },
    { actor: 'ARQ Worker',  action: 'Build persona prompt',                    detail: 'Segment profile + stimulus injected into prompt', color: '#7C4DBD' },
    { actor: 'Claude API',  action: 'Inference call',                          detail: 'Returns sentiment + score + verbatim JSON',    color: '#E8470A' },
    { actor: 'ARQ Worker',  action: 'UPDATE simulation_runs',                  detail: 'status=completed, scores + response persisted', color: '#7C4DBD' },
    { actor: 'Browser',     action: 'WS push / poll GET /simulate/runs/{id}', detail: 'Client receives final result',                 color: '#27B97C' },
  ]
  return (
    <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--primary-10)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr 1fr', backgroundColor: 'var(--primary)', padding: '10px 16px', gap: 16 }}>
        {['Actor', 'Action', 'Detail'].map((h) => (
          <span key={h} style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '2px', color: 'rgba(255,255,255,0.5)' }}>{h}</span>
        ))}
      </div>
      {steps.map((s, i) => (
        <div key={i} style={{
          display: 'grid', gridTemplateColumns: '110px 1fr 1fr',
          padding: '10px 16px', gap: 16,
          backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--light)',
          alignItems: 'start', borderLeft: `3px solid ${s.color}`,
        }}>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: s.color }}>{s.actor}</span>
          <span style={{ fontFamily: "'Courier New'", fontSize: 11, color: 'var(--dark)' }}>{s.action}</span>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569' }}>{s.detail}</span>
        </div>
      ))}
    </div>
  )
}

function ApiEndpointMap(): React.JSX.Element {
  const groups = [
    {
      group: 'Auth', color: '#7C4DBD',
      endpoints: [
        { method: 'POST', path: '/auth/dev-token',  note: 'Issue JWT for dev use (dev mode only)' },
        { method: 'POST', path: '/auth/keys',        note: 'Create API key (admin / marketer)' },
        { method: 'GET',  path: '/auth/keys',        note: 'List API keys for current org' },
        { method: 'DELETE', path: '/auth/keys/{id}', note: 'Revoke an API key' },
      ],
    },
    {
      group: 'Organisation', color: 'var(--primary)',
      endpoints: [
        { method: 'GET',    path: '/org',              note: 'Current org details' },
        { method: 'GET',    path: '/org/members',       note: 'List members' },
        { method: 'POST',   path: '/org/members',       note: 'Invite member (admin only)' },
        { method: 'DELETE', path: '/org/members/{id}',  note: 'Remove member (admin only)' },
      ],
    },
    {
      group: 'Segments', color: 'var(--gold)',
      endpoints: [
        { method: 'GET',    path: '/segments',       note: 'Paginated segment list' },
        { method: 'POST',   path: '/segments',       note: 'Create segment' },
        { method: 'GET',    path: '/segments/{id}',  note: 'Segment detail' },
        { method: 'DELETE', path: '/segments/{id}',  note: 'Delete segment' },
      ],
    },
    {
      group: 'Campaigns', color: '#27B97C',
      endpoints: [
        { method: 'GET',  path: '/campaigns',                   note: 'Paginated campaign list' },
        { method: 'POST', path: '/campaigns',                   note: 'Create campaign' },
        { method: 'POST', path: '/campaigns/{id}/variants',     note: 'Add variant to campaign' },
      ],
    },
    {
      group: 'Simulations', color: '#E8470A',
      endpoints: [
        { method: 'POST', path: '/simulate/run',        note: 'Dispatch async simulation run' },
        { method: 'GET',  path: '/simulate/runs',       note: 'Paginated run history (filterable)' },
        { method: 'GET',  path: '/simulate/runs/{id}',  note: 'Single run detail + result' },
        { method: 'WS',   path: '/ws/simulate/{id}',   note: 'Live progress stream for a run' },
      ],
    },
    {
      group: 'Admin', color: 'var(--mid)',
      endpoints: [
        { method: 'GET',    path: '/admin/stats', note: 'Row counts per table (current org)' },
        { method: 'POST',   path: '/admin/seed',  note: 'Insert synthetic demo data' },
        { method: 'DELETE', path: '/admin/clear', note: 'Wipe all org data (non-production only)' },
      ],
    },
  ]

  const methodColor = (m: string) => {
    if (m === 'GET')    return { bg: 'rgba(39,185,124,0.12)',   color: '#0d5c3a' }
    if (m === 'POST')   return { bg: 'rgba(0,51,102,0.1)',      color: 'var(--primary)' }
    if (m === 'DELETE') return { bg: 'rgba(176,53,53,0.1)',     color: '#b03535' }
    if (m === 'WS')     return { bg: 'rgba(124,77,189,0.12)',   color: '#3d1f70' }
    return { bg: 'var(--light)', color: 'var(--mid)' }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {groups.map((g) => (
        <div key={g.group}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '2.5px', color: g.color, marginBottom: 8 }}>{g.group}</div>
          <div style={{ borderRadius: 8, overflow: 'hidden', border: '1px solid var(--primary-10)' }}>
            {g.endpoints.map((e, i) => {
              const mc = methodColor(e.method)
              return (
                <div key={e.path} style={{
                  display: 'grid', gridTemplateColumns: '60px 260px 1fr',
                  padding: '9px 14px', gap: 12, alignItems: 'center',
                  backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--light)',
                }}>
                  <span style={{ fontFamily: "'Courier New'", fontSize: 10, fontWeight: 700, backgroundColor: mc.bg, color: mc.color, borderRadius: 4, padding: '2px 6px', textAlign: 'center' }}>{e.method}</span>
                  <span style={{ fontFamily: "'Courier New'", fontSize: 12, color: 'var(--dark)' }}>{e.path}</span>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569' }}>{e.note}</span>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

function RbacMatrix(): React.JSX.Element {
  const permissions = [
    'SIMULATIONS_READ', 'SIMULATIONS_RUN',
    'SEGMENTS_READ', 'SEGMENTS_WRITE',
    'CAMPAIGNS_READ', 'CAMPAIGNS_WRITE',
    'ORG_MEMBERS_READ', 'ORG_MEMBERS_MANAGE',
    'ORG_KEYS_READ', 'ORG_KEYS_MANAGE',
    'ORG_AUDIT_READ', 'ORG_DATA_DELETE',
  ]
  const roles = ['viewer', 'analyst', 'marketer', 'admin']
  const granted: Record<string, string[]> = {
    viewer:   ['SIMULATIONS_READ', 'SEGMENTS_READ', 'CAMPAIGNS_READ'],
    analyst:  ['SIMULATIONS_READ', 'SEGMENTS_READ', 'CAMPAIGNS_READ', 'ORG_AUDIT_READ'],
    marketer: ['SIMULATIONS_READ', 'SIMULATIONS_RUN', 'SEGMENTS_READ', 'SEGMENTS_WRITE', 'CAMPAIGNS_READ', 'CAMPAIGNS_WRITE', 'ORG_KEYS_READ', 'ORG_AUDIT_READ'],
    admin:    permissions,
  }
  const check = (role: string, perm: string) => granted[role]?.includes(perm) ?? false

  return (
    <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--primary-10)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 80px 80px 90px 70px', backgroundColor: 'var(--primary)', padding: '10px 16px', gap: 8 }}>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '2px', color: 'rgba(255,255,255,0.5)' }}>Permission</span>
        {roles.map((r) => (
          <span key={r} style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '1.5px', color: 'rgba(255,255,255,0.5)', textAlign: 'center' }}>{r}</span>
        ))}
      </div>
      {permissions.map((p, i) => (
        <div key={p} style={{
          display: 'grid', gridTemplateColumns: '1fr 80px 80px 90px 70px',
          padding: '8px 16px', gap: 8,
          backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--light)',
          alignItems: 'center',
        }}>
          <span style={{ fontFamily: "'Courier New'", fontSize: 11, color: 'var(--dark)' }}>{p}</span>
          {roles.map((r) => (
            <div key={r} style={{ textAlign: 'center' }}>
              {check(r, p)
                ? <span style={{ color: '#22943a', fontWeight: 700, fontSize: 14 }}>✓</span>
                : <span style={{ color: 'var(--primary-30)', fontSize: 12 }}>—</span>
              }
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

function DbSchemaOverview(): React.JSX.Element {
  const tables = [
    { name: 'organizations', pk: 'id', fks: [], key: 'name, slug, plan', note: 'Top-level tenant record. All other tables reference org_id.' },
    { name: 'users',         pk: 'id', fks: ['org_id → organizations'], key: 'email, role, is_active', note: 'Platform users. Role determines RBAC permissions.' },
    { name: 'api_keys',      pk: 'id', fks: ['org_id → organizations'], key: 'key_hash (SHA-256), role, expires_at', note: 'Machine credentials. key_hash stored — raw key shown once on creation.' },
    { name: 'segments',      pk: 'id', fks: ['org_id → organizations'], key: 'name, definition (JSONB), is_stale', note: 'Segment definition. JSONB stores age range, geo, affinities, purchase thresholds.' },
    { name: 'campaigns',     pk: 'id', fks: ['org_id → organizations', 'segment_id → segments'], key: 'name, status', note: 'Groups variants for ranked comparison against a single segment.' },
    { name: 'campaign_variants', pk: 'id', fks: ['campaign_id → campaigns'], key: 'stimulus (JSONB), rank, score', note: 'One row per creative variant. Rank and score populated after simulation.' },
    { name: 'simulation_runs',   pk: 'id', fks: ['org_id → organizations', 'segment_id → segments'], key: 'stimulus (JSONB), sentiment, conversion_score, llm_metadata (JSONB)', note: 'Single simulation execution record. llm_metadata captures token counts and latency.' },
    { name: 'audit_events',      pk: 'id', fks: ['org_id → organizations'], key: 'action, actor_id, resource_type, status_code', note: 'Append-only audit log. Written by middleware on every mutating request.' },
  ]
  return (
    <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--primary-10)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '160px 90px 1fr 1fr', backgroundColor: 'var(--primary)', padding: '10px 16px', gap: 12 }}>
        {['Table', 'PK', 'Key columns', 'Purpose'].map((h) => (
          <span key={h} style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '2px', color: 'rgba(255,255,255,0.5)' }}>{h}</span>
        ))}
      </div>
      {tables.map((t, i) => (
        <div key={t.name} style={{
          display: 'grid', gridTemplateColumns: '160px 90px 1fr 1fr',
          padding: '12px 16px', gap: 12,
          backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--light)',
          alignItems: 'start',
        }}>
          <div>
            <div style={{ fontFamily: "'Courier New'", fontSize: 12, color: 'var(--primary-60)', fontWeight: 700 }}>{t.name}</div>
            {t.fks.map((fk) => (
              <div key={fk} style={{ fontFamily: "'Courier New'", fontSize: 10, color: 'var(--mid)', marginTop: 2 }}>{fk}</div>
            ))}
          </div>
          <span style={{ fontFamily: "'Courier New'", fontSize: 11, color: 'var(--gold)' }}>{t.pk}</span>
          <span style={{ fontFamily: "'Courier New'", fontSize: 11, color: '#475569', lineHeight: 1.6 }}>{t.key}</span>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569', lineHeight: 1.6 }}>{t.note}</span>
        </div>
      ))}
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
          display: 'grid', gridTemplateColumns: '160px 180px 1fr',
          padding: '12px 16px', gap: 16,
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
    { tech: 'React 18',     role: 'UI framework',       why: 'Concurrent rendering supports the real-time WebSocket update pattern. The hooks model eliminates class component lifecycle complexity. Functional components only throughout.' },
    { tech: 'TypeScript',   role: 'Type safety',        why: 'Strict mode enforced. All API response shapes are statically typed against the backend Pydantic models. Runtime type mismatches between frontend interfaces and actual API responses are caught at compile time, not in production.' },
    { tech: 'Vite 5',       role: 'Build + dev server', why: 'Native ESM in development gives 50–200ms hot-reload. The proxy configuration forwards /api/* to FastAPI and /ws/* to the WebSocket handler, making same-origin requests in the browser without CORS configuration during development.' },
    { tech: 'Zustand',      role: 'Client state',       why: 'No Provider wrapping, no action creators, no reducers. Two stores: authStore (JWT token + user) and campaignStore (multi-step form). All other state is local useState. Proportionate to actual state complexity.' },
    { tech: 'Inline styles', role: 'Styling',           why: 'All styles reference CSS custom properties from tokens.css. TypeScript checks property names and values. No class specificity cascade, no Tailwind approximations of precise brand values (e.g. rgba(201,168,76,0.12) for active nav backgrounds).' },
  ]

  const backendStack: StackRow[] = [
    { tech: 'FastAPI',        role: 'Web framework',    why: 'Native async/await. Automatic OpenAPI schema from Pydantic models — the /docs and /redoc endpoints require zero manual maintenance. Dependency injection handles auth, DB sessions, and permission checks without decorator stacks.' },
    { tech: 'Pydantic v2',    role: 'Validation',       why: 'Rust core gives 5–17× throughput vs v1. All request bodies, ORM response serialisations, and simulation payloads are Pydantic models. Validation errors return structured 422 JSON without custom error handling.' },
    { tech: 'SQLAlchemy 2',   role: 'ORM',              why: 'Native async via asyncpg. The mapped_column 2.0 API provides typed ORM fields. No raw SQL outside db.py. Multi-tenant isolation is enforced at the ORM layer — every query filters by org_id derived from the auth claims.' },
    { tech: 'ARQ',            role: 'Task queue',       why: 'Redis-backed async task queue built for asyncio. Simulation runs are dispatched immediately, returning a run_id. The API is non-blocking. Workers poll Redis, execute the Claude inference call, and persist results to PostgreSQL.' },
    { tech: 'JWT + API keys', role: 'Auth',             why: 'Two credential types: short-lived JWTs for human users, SHA-256-hashed API keys for machine callers. AUTH_REQUIRED=false bypasses both for local development without code changes. Role claims determine RBAC permissions.' },
    { tech: 'Prometheus',     role: 'Metrics',          why: 'Every HTTP request is recorded with method, path, and status code in a latency histogram. The /metrics endpoint is scraped by Prometheus. Grafana dashboards visualise p50/p95/p99 latency and error rates per route.' },
  ]

  const dataStack: StackRow[] = [
    { tech: 'PostgreSQL 16', role: 'Primary datastore', why: 'JSONB columns for stimulus and llm_metadata avoid schema migrations for each new stimulus or metadata field while remaining queryable. Row-level multi-tenancy via org_id on every table. Healthcheck via pg_isready in Docker Compose.' },
    { tech: 'Redis 7',       role: 'Cache + job queue', why: 'Dual purpose: ARQ uses Redis as the job queue broker (task dispatch + result storage), and the API uses it for short-lived response caching. One infrastructure component serving two concerns reduces operational surface area.' },
    { tech: 'Qdrant',        role: 'Vector store',      why: 'Persona embeddings stored for nearest-neighbour segment lookup. Selected over pgvector for production-grade ANN index performance and native payload filtering without full table scans at scale.' },
    { tech: 'Kafka',         role: 'Event streaming',   why: 'Navigation and purchase events are high-throughput append-only streams. Kafka decouples event producers (web, mobile) from segment model consumers with at-least-once delivery guarantees. Schema Registry enforces Avro contracts.' },
  ]

  const aiStack: StackRow[] = [
    { tech: 'claude-sonnet-4-6', role: 'Persona inference', why: 'Sonnet 4.6 balances quality, latency, and cost for structured scoring tasks. Opus 4.8 increases cost 5× with marginal gain on JSON output tasks. Haiku 4.5 lacks the reasoning depth needed for nuanced verbatim persona responses.' },
    { tech: 'Structured output',  role: 'Response format',  why: 'The system prompt instructs Claude to return a JSON object with sentiment, likelihood_to_convert, conversion_score, and verbatim_response. Structured output eliminates post-processing regex and enforces a stable contract between inference and the ORM.' },
    { tech: 'Prompt architecture', role: 'Context injection', why: 'The segment definition (age range, geo, category affinities, purchase history) is injected into the system prompt. The stimulus is in the user turn. This separates stable persona context (cached) from variable stimulus content (not cached).' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 40 }}>

      {/* Architecture */}
      <div style={card}>
        <Eyebrow>Architecture</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 6 }}>Five-layer system</h2>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          The platform is a five-layer stack. Each layer has a single, well-defined responsibility
          and communicates with adjacent layers only through defined interfaces. The presentation
          layer is a browser-only SPA. The API layer is stateless. Simulation work is offloaded to
          an isolated worker process. Persistence is distributed across three stores by data shape.
          Inference is delegated entirely to the Anthropic API — no model weights are hosted.
        </p>
        <ArchDiagram />
      </div>

      {/* Simulation lifecycle */}
      <div style={card}>
        <Eyebrow>Simulation lifecycle</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 6 }}>Eight-hop request path</h2>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          A simulation run is the critical path in the system. The API returns a run ID within
          milliseconds. The heavy work (segment fetch, prompt construction, Claude inference, result
          persistence) happens asynchronously in the worker process. The browser tracks progress via
          a WebSocket connection held open for the run duration.
        </p>
        <SimulationLifecycleDiagram />
      </div>

      {/* API endpoint map */}
      <div style={card}>
        <Eyebrow>API reference</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 6 }}>Endpoint map</h2>
        <p style={{ ...bodyText, marginBottom: 8 }}>
          The full OpenAPI specification is available at{' '}
          <code style={inlineCode}>http://localhost:8001/docs</code> (Swagger) and{' '}
          <code style={inlineCode}>http://localhost:8001/redoc</code> (ReDoc).
          The table below summarises the surface area by resource group.
        </p>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          All endpoints except <code style={inlineCode}>/health</code> and{' '}
          <code style={inlineCode}>/metrics</code> require authentication when{' '}
          <code style={inlineCode}>AUTH_REQUIRED=true</code>. Each route carries a{' '}
          <code style={inlineCode}>require(Permission.X)</code> dependency that enforces RBAC
          before any database operation is attempted.
        </p>
        <ApiEndpointMap />
      </div>

      {/* Database schema */}
      <div style={card}>
        <Eyebrow>Database schema</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 6 }}>Table reference</h2>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          All tables carry an <code style={inlineCode}>org_id</code> UUID column that scopes every
          row to a single tenant. Foreign keys enforce referential integrity at the database level.
          JSONB columns (<code style={inlineCode}>stimulus</code>,{' '}
          <code style={inlineCode}>definition</code>,{' '}
          <code style={inlineCode}>llm_metadata</code>) hold schemaless payloads that vary by type,
          avoiding a polymorphic table design while remaining fully queryable via PostgreSQL's JSONB
          operators.
        </p>
        <DbSchemaOverview />
      </div>

      {/* RBAC */}
      <div style={card}>
        <Eyebrow>Access control</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 6 }}>RBAC permission matrix</h2>
        <p style={{ ...bodyText, marginBottom: 8 }}>
          Four roles form an additive hierarchy — each role is a strict superset of the permissions
          granted to the role below it. Role is stored in the JWT claims and API key record;
          <code style={inlineCode}>has_permission(role, Permission.X)</code> is evaluated in the
          FastAPI dependency before any handler code runs.
        </p>
        <p style={{ ...bodyText, marginBottom: 24 }}>
          <code style={inlineCode}>admin</code> receives all permissions by definition
          (<code style={inlineCode}>frozenset(Permission)</code>). New permissions are
          automatically granted to admin without updating the permission map.
        </p>
        <RbacMatrix />
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

      {/* Architectural decisions */}
      <div style={card}>
        <Eyebrow>Design decisions</Eyebrow>
        <h2 style={{ ...sectionTitle, marginBottom: 20 }}>Key architectural choices</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {[
            {
              decision: 'Async-first throughout',
              detail: 'Every FastAPI route uses async def. SQLAlchemy sessions use async_sessionmaker with asyncpg. The ARQ worker is an asyncio event loop. A single uvicorn worker handles many concurrent in-flight simulation streams without blocking — critical when WebSocket connections are held open while Claude inference runs.',
            },
            {
              decision: 'JSONB for variable-schema payloads',
              detail: 'Stimulus payloads differ by type: ad_copy has headline/body_copy/cta; price_change has original_price/new_price; promo has promo_code/discount_type/expiry_days. A polymorphic table design (three tables + a type discriminator) would require joins and schema migrations for every new stimulus type. JSONB stores all types in one column, with the type discriminator field inside the JSON object. All three types are queryable via PostgreSQL\'s ->> operator.',
            },
            {
              decision: 'Stateless API, external state',
              detail: 'The FastAPI process holds no in-memory state between requests. JWT claims are validated statelessly. The ARQ job queue and cached responses live in Redis. This means the API scales horizontally to N instances without sticky sessions, shared memory, or a distributed cache invalidation protocol.',
            },
            {
              decision: 'LLM isolated from the request path',
              detail: 'Claude is called only from the ARQ worker, never from a FastAPI route handler. This means the API\'s p99 latency for CRUD endpoints is bounded by PostgreSQL query time (~5–20ms), not by inference latency (~800–4500ms). The API remains responsive during high simulation load.',
            },
            {
              decision: 'SQL migrations over ORM migrations',
              detail: 'The database schema is managed via numbered .sql files (001_initial_schema.sql, etc.) rather than Alembic. Docker Compose mounts the migrations directory to docker-entrypoint-initdb.d for automatic application on fresh volume init. All migrations use CREATE TABLE IF NOT EXISTS and CREATE INDEX IF NOT EXISTS for safe re-execution. The demo launcher applies them explicitly via docker exec psql on every startup.',
            },
            {
              decision: 'No server-side rendering',
              detail: 'The dashboard is a pure SPA served by the Vite dev server (development) or a static file host (production). There is no Next.js, no SSR, no hydration. The marketing simulation use case does not require SEO indexing or first-contentful-paint optimisation for unauthenticated users. A SPA is architecturally simpler and avoids the server/client boundary complexity that SSR introduces.',
            },
          ].map(({ decision, detail }) => (
            <div key={decision} style={{ borderLeft: '3px solid var(--primary-30)', paddingLeft: 20 }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: 'var(--dark)', marginBottom: 6 }}>{decision}</div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.75 }}>{detail}</div>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}

// =============================================================================
// Main page
// =============================================================================

export default function InfoPage(): React.JSX.Element {
  const [view, setView] = useState<View>('business')

  return (
    <div>
      <div style={heroStyle}>
        <div style={contentWrap}>
          <Eyebrow light>Platform Information</Eyebrow>
          <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 36, fontWeight: 300, color: '#fff', lineHeight: 1.2, margin: '8px 0 4px' }}>
            Synthetic Persona{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Sandbox</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: 0 }}>
            Business rationale and engineering reference.
          </p>
          <TabBar active={view} onChange={setView} />
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--light)', minHeight: '70vh' }}>
        <div style={bodyWrap}>
          {view === 'business'    && <BusinessView    />}
          {view === 'engineering' && <EngineeringView />}
        </div>
      </div>
    </div>
  )
}
