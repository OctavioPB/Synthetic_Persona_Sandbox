import React, { useEffect, useRef, useState } from 'react'
import Eyebrow from '../components/Eyebrow'
import PersonaThinkingIndicator from '../components/PersonaThinkingIndicator'
import StimulusBuilder from '../components/StimulusBuilder'
import { RunResult, useCampaignStore, VariantSpec } from '../store/campaignStore'
import { api, SegmentSummary } from '../services/api'
import { TERMINAL_STATUSES, useSimulationProgress, SimulationProgress } from '../hooks/useSimulationProgress'

interface Props {
  onLaunchComplete: () => void
  onCancel: () => void
}

// ── Shared styles ─────────────────────────────────────────────────────────────

const heroStyle: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
  `,
  backgroundSize: '48px 48px',
  padding: '48px 48px 40px',
}

const section: React.CSSProperties = {
  maxWidth: 860,
  margin: '0 auto',
  padding: '48px 48px',
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  fontFamily: 'var(--fb)',
  fontSize: 13,
  color: 'var(--dark)',
  border: '1px solid rgba(0,51,102,0.15)',
  borderRadius: 6,
  padding: '9px 12px',
  outline: 'none',
  backgroundColor: '#fff',
  boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '2px',
  color: 'var(--mid)',
  marginBottom: 6,
  display: 'block',
}

const primaryBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '1.5px',
  textTransform: 'uppercase',
  backgroundColor: 'var(--gold)',
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '10px 22px',
  cursor: 'pointer',
}

const ghostBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 11,
  letterSpacing: '1px',
  textTransform: 'uppercase',
  background: 'none',
  border: '1px solid rgba(0,51,102,0.2)',
  borderRadius: 6,
  padding: '10px 18px',
  cursor: 'pointer',
  color: 'var(--mid)',
}

// ── Step indicator ─────────────────────────────────────────────────────────────

const STEP_LABELS = ['Campaign', 'Variants', 'Launch']

function StepIndicator({ current }: { current: 1 | 2 | 3 }): React.JSX.Element {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 32 }}>
      {STEP_LABELS.map((lbl, i) => {
        const num = i + 1
        const done = num < current
        const active = num === current
        return (
          <React.Fragment key={lbl}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <div style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                backgroundColor: done || active ? 'var(--gold)' : 'transparent',
                border: `2px solid ${done || active ? 'var(--gold)' : 'rgba(0,51,102,0.2)'}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s',
              }}>
                {done ? (
                  <svg width="12" height="9" viewBox="0 0 12 9" fill="none">
                    <path d="M1 4.5L4.5 8L11 1" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <span style={{
                    fontFamily: 'var(--fb)',
                    fontSize: 10,
                    fontWeight: 700,
                    color: active ? '#fff' : 'rgba(0,51,102,0.3)',
                  }}>{num}</span>
                )}
              </div>
              <span style={{
                fontFamily: 'var(--fb)',
                fontSize: 10,
                letterSpacing: '1.5px',
                textTransform: 'uppercase',
                color: active ? 'var(--gold)' : done ? 'var(--mid)' : 'rgba(0,51,102,0.3)',
              }}>
                {lbl}
              </span>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <div style={{
                flex: 1,
                height: 1,
                backgroundColor: i < current - 1 ? 'var(--gold)' : 'rgba(0,51,102,0.1)',
                marginBottom: 22,
                minWidth: 40,
                transition: 'background-color 0.2s',
              }} />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

// ── Variant progress card (one per variant, manages own WebSocket) ─────────────

interface VariantProgressCardProps {
  variantName: string
  runId: string | null
  onComplete: (progress: SimulationProgress) => void
}

function VariantProgressCard({ variantName, runId, onComplete }: VariantProgressCardProps): React.JSX.Element {
  const progress = useSimulationProgress(runId)
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete
  const firedRef = useRef(false)

  useEffect(() => {
    if (TERMINAL_STATUSES.has(progress.status) && !firedRef.current) {
      firedRef.current = true
      onCompleteRef.current(progress)
    }
  }, [progress.status])

  if (!runId || progress.status === 'pending' || progress.status === 'running') {
    return <PersonaThinkingIndicator variantName={variantName} />
  }

  const score = progress.conversionScore
  const scoreColor = score === null ? 'var(--mid)'
    : score >= 0.65 ? '#22943a'
    : score >= 0.4  ? '#b07d10'
    : '#b03535'

  if (progress.status === 'completed') {
    return (
      <div style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        border: '1px solid rgba(0,51,102,0.08)',
        padding: '20px 20px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        minHeight: 140,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <p style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 13, fontWeight: 500, color: 'var(--primary)', margin: 0 }}>
            {variantName}
          </p>
          <div style={{
            fontFamily: 'var(--fb)',
            fontSize: 18,
            fontWeight: 700,
            color: scoreColor,
            lineHeight: 1,
          }}>
            {score !== null ? `${Math.round(score * 100)}%` : '—'}
          </div>
        </div>

        {progress.sentiment && (
          <SentimentPill sentiment={progress.sentiment} />
        )}

        {progress.verbatimResponse && (
          <p style={{
            fontFamily: 'var(--fb)',
            fontSize: 11,
            color: 'rgba(0,51,102,0.6)',
            margin: 0,
            lineHeight: 1.5,
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          } as React.CSSProperties}>
            "{progress.verbatimResponse}"
          </p>
        )}

        {progress.latencyMs && (
          <p style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', margin: 0, marginTop: 'auto' }}>
            {(progress.latencyMs / 1000).toFixed(1)}s
          </p>
        )}
      </div>
    )
  }

  return (
    <div style={{
      backgroundColor: '#fff3f3',
      borderRadius: 12,
      border: '1px solid rgba(176,53,53,0.2)',
      padding: '20px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      minHeight: 140,
    }}>
      <p style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 13, color: '#b03535', margin: 0 }}>
        {variantName}
      </p>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'rgba(176,53,53,0.7)', margin: 0 }}>
        {progress.errorDetail ?? 'Simulation failed'}
      </p>
    </div>
  )
}

// ── Sentiment pill ────────────────────────────────────────────────────────────

function SentimentPill({ sentiment }: { sentiment: string }): React.JSX.Element {
  const map: Record<string, { bg: string; color: string }> = {
    positive: { bg: 'rgba(34,148,58,0.1)',  color: '#22943a' },
    neutral:  { bg: 'rgba(0,51,102,0.08)',  color: 'var(--mid)' },
    negative: { bg: 'rgba(176,53,53,0.1)',  color: '#b03535' },
  }
  const { bg, color } = map[sentiment] ?? map['neutral']
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      backgroundColor: bg,
      borderRadius: 20,
      padding: '3px 9px',
      width: 'fit-content',
    }}>
      <div style={{ width: 5, height: 5, borderRadius: '50%', backgroundColor: color }} />
      <span style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'capitalize', color, fontWeight: 600 }}>
        {sentiment}
      </span>
    </div>
  )
}

// ── Launch phase ──────────────────────────────────────────────────────────────

interface LaunchPhaseProps {
  campaignName: string
  segmentId: string
  segmentName: string
  variants: VariantSpec[]
  onAllComplete: (results: RunResult[]) => void
}

function LaunchPhase({ campaignName, segmentId, variants, onAllComplete }: LaunchPhaseProps): React.JSX.Element {
  const [runIds, setRunIds]   = useState<Record<number, string>>({})
  const [launchErr, setLaunchErr] = useState<string | null>(null)
  const completed = useRef<Record<number, SimulationProgress>>({})
  const firedRef  = useRef(false)

  useEffect(() => {
    let mounted = true

    const launch = async () => {
      try {
        const campaign = await api.campaigns.create({
          name: campaignName,
          description: '',
          segment_id: segmentId,
        })

        const ids: Record<number, string> = {}
        for (let i = 0; i < variants.length; i++) {
          const v = variants[i]
          await api.campaigns.createVariant(campaign.id, {
            name: v.name,
            stimulus: v.stimulus as Record<string, unknown>,
          })
          const run = await api.simulations.run({
            segment_id: segmentId,
            stimulus: v.stimulus as Record<string, unknown>,
          })
          ids[i] = run.id
        }

        if (mounted) setRunIds(ids)
      } catch (err) {
        if (mounted) setLaunchErr(err instanceof Error ? err.message : 'Launch failed')
      }
    }

    launch()
    return () => { mounted = false }
  }, [])  // intentionally run once on mount

  const handleVariantComplete = (index: number, progress: SimulationProgress) => {
    completed.current[index] = progress
    const doneCount = Object.keys(completed.current).length

    if (doneCount >= variants.length && !firedRef.current) {
      firedRef.current = true
      const results: RunResult[] = variants.map((v, i) => {
        const p = completed.current[i]
        return {
          variantIndex: i,
          variantName:  v.name,
          runId:        runIds[i] ?? '',
          status:       p?.status ?? 'failed',
          conversionScore:  p?.conversionScore  ?? null,
          verbatimResponse: p?.verbatimResponse ?? null,
          sentiment:        p?.sentiment        ?? null,
          latencyMs:        p?.latencyMs        ?? null,
        }
      })
      onAllComplete(results)
    }
  }

  if (launchErr) {
    return (
      <div style={{ textAlign: 'center', padding: '32px 0' }}>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#b03535' }}>
          Launch error: {launchErr}
        </p>
      </div>
    )
  }

  const enqueued = Object.keys(runIds).length
  const total = variants.length

  return (
    <div>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 20 }}>
        {enqueued < total
          ? `Enqueueing simulations… (${enqueued}/${total})`
          : `Running ${total} simulation${total > 1 ? 's' : ''} in parallel`}
      </p>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
        gap: 16,
      }}>
        {variants.map((v, i) => (
          <VariantProgressCard
            key={i}
            variantName={v.name}
            runId={runIds[i] ?? null}
            onComplete={(p) => handleVariantComplete(i, p)}
          />
        ))}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CampaignLauncherPage({ onLaunchComplete, onCancel }: Props): React.JSX.Element {
  const { form, setFormField, addVariant, removeVariant, setCampaignResults } = useCampaignStore()

  const [step, setStep]               = useState<1 | 2 | 3>(1)
  const [segments, setSegments]       = useState<SegmentSummary[]>([])
  const [segmentsErr, setSegmentsErr] = useState(false)
  const [showBuilder, setShowBuilder] = useState(false)

  useEffect(() => {
    api.segments.list()
      .then(setSegments)
      .catch(() => setSegmentsErr(true))
  }, [])

  const step1Valid = form.name.trim().length >= 2 && form.segmentId !== ''
  const step2Valid = form.variants.length >= 1

  const handleAllComplete = (results: RunResult[]) => {
    setCampaignResults(results)
    onLaunchComplete()
  }

  const handleSegmentChange = (id: string) => {
    const seg = segments.find((s) => s.id === id)
    setFormField('segmentId', id)
    setFormField('segmentName', seg?.name ?? '')
  }

  return (
    <div>
      {/* Hero */}
      <div style={heroStyle}>
        <div style={{ maxWidth: 860, margin: '0 auto' }}>
          <Eyebrow light>Campaign Launcher</Eyebrow>
          <h1 style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 36,
            fontWeight: 300,
            color: '#fff',
            lineHeight: 1.2,
            margin: '8px 0 4px',
          }}>
            Test your{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>campaign</em>
            {' '}before it ships
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: 0 }}>
            Simulate audience reactions to multiple variants — in seconds.
          </p>
        </div>
      </div>

      {/* Body */}
      <div style={{ backgroundColor: 'var(--light)', minHeight: '70vh' }}>
        <div style={section}>
          <StepIndicator current={step} />

          {/* ── Step 1: Campaign info ──────────────────────────────────────────── */}
          {step === 1 && (
            <div>
              <Eyebrow>Step 1</Eyebrow>
              <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '0 0 24px' }}>
                Campaign information
              </h2>

              <div style={{ backgroundColor: '#fff', borderRadius: 12, border: '1px solid rgba(0,51,102,0.08)', padding: '28px' }}>
                <div style={{ marginBottom: 16 }}>
                  <span style={labelStyle}>Campaign Name *</span>
                  <input
                    style={inputStyle}
                    value={form.name}
                    placeholder="e.g. Summer 2026 — Madrid Launch"
                    onChange={(e) => setFormField('name', e.target.value)}
                  />
                </div>

                <div style={{ marginBottom: 16 }}>
                  <span style={labelStyle}>Description (optional)</span>
                  <textarea
                    rows={2}
                    style={{ ...inputStyle, resize: 'vertical' } as React.CSSProperties}
                    value={form.description}
                    placeholder="Brief context for this campaign…"
                    onChange={(e) => setFormField('description', e.target.value)}
                  />
                </div>

                <div>
                  <span style={labelStyle}>Target Segment *</span>
                  {segmentsErr ? (
                    <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#b03535' }}>
                      Could not load segments — is the API running?
                    </p>
                  ) : (
                    <select
                      style={inputStyle}
                      value={form.segmentId}
                      onChange={(e) => handleSegmentChange(e.target.value)}
                    >
                      <option value="">Select a segment…</option>
                      {segments.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}{s.is_stale ? ' ⚠ stale' : ''}</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 24 }}>
                <button style={ghostBtn} onClick={onCancel}>Cancel</button>
                <button
                  style={{ ...primaryBtn, opacity: step1Valid ? 1 : 0.4, cursor: step1Valid ? 'pointer' : 'not-allowed' }}
                  disabled={!step1Valid}
                  onClick={() => setStep(2)}
                >
                  Next: Add Variants →
                </button>
              </div>
            </div>
          )}

          {/* ── Step 2: Variants ──────────────────────────────────────────────── */}
          {step === 2 && (
            <div>
              <Eyebrow>Step 2</Eyebrow>
              <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '0 0 24px' }}>
                Add variants to test
              </h2>

              {/* Existing variants list */}
              {form.variants.length > 0 && (
                <div style={{ marginBottom: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {form.variants.map((v, i) => (
                    <div
                      key={i}
                      style={{
                        backgroundColor: '#fff',
                        borderRadius: 8,
                        border: '1px solid rgba(0,51,102,0.08)',
                        padding: '12px 16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{
                          fontFamily: 'var(--fb)',
                          fontSize: 10,
                          textTransform: 'uppercase',
                          letterSpacing: '1.5px',
                          backgroundColor: 'rgba(201,168,76,0.12)',
                          color: 'var(--gold)',
                          borderRadius: 4,
                          padding: '2px 7px',
                          fontWeight: 700,
                        }}>
                          {v.stimulus.type.replace('_', ' ')}
                        </span>
                        <span style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 500 }}>
                          {v.name}
                        </span>
                      </div>
                      <button
                        onClick={() => removeVariant(i)}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: 'var(--mid)',
                          fontSize: 16,
                          padding: '0 4px',
                        }}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Stimulus builder */}
              {showBuilder ? (
                <StimulusBuilder
                  onConfirm={(name, stimulus) => {
                    addVariant({ name, stimulus })
                    setShowBuilder(false)
                  }}
                  onCancel={() => setShowBuilder(false)}
                />
              ) : (
                <button
                  onClick={() => setShowBuilder(true)}
                  style={{
                    ...ghostBtn,
                    width: '100%',
                    textAlign: 'center',
                    padding: '14px',
                    borderStyle: 'dashed',
                    color: 'var(--gold)',
                    borderColor: 'rgba(201,168,76,0.4)',
                  } as React.CSSProperties}
                >
                  + Add Variant
                </button>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 24 }}>
                <button style={ghostBtn} onClick={() => setStep(1)}>← Back</button>
                <button
                  style={{ ...primaryBtn, opacity: step2Valid ? 1 : 0.4, cursor: step2Valid ? 'pointer' : 'not-allowed' }}
                  disabled={!step2Valid}
                  onClick={() => setStep(3)}
                >
                  Launch {form.variants.length} Variant{form.variants.length > 1 ? 's' : ''} →
                </button>
              </div>
            </div>
          )}

          {/* ── Step 3: Launch ────────────────────────────────────────────────── */}
          {step === 3 && (
            <div>
              <Eyebrow>Step 3 — Running</Eyebrow>
              <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 22, fontWeight: 300, color: 'var(--dark)', margin: '0 0 24px' }}>
                Personas are <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>thinking</em>
              </h2>

              <LaunchPhase
                campaignName={form.name}
                segmentId={form.segmentId}
                segmentName={form.segmentName}
                variants={form.variants}
                onAllComplete={handleAllComplete}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
