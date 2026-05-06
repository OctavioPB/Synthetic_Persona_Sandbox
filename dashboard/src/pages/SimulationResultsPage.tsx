import React, { useState } from 'react'
import Eyebrow from '../components/Eyebrow'
import { RunResult, useCampaignStore } from '../store/campaignStore'

interface Props {
  onLaunchAnother: () => void
  onViewSegments: () => void
}

// ── Score helpers ─────────────────────────────────────────────────────────────

function scoreColor(score: number | null): string {
  if (score === null) return 'var(--mid)'
  if (score >= 0.65)  return '#22943a'
  if (score >= 0.4)   return '#b07d10'
  return '#b03535'
}

function scoreLabel(score: number | null): string {
  if (score === null) return '—'
  return `${Math.round(score * 100)}%`
}

// ── Sentiment pill ────────────────────────────────────────────────────────────

function SentimentPill({ sentiment }: { sentiment: string | null }): React.JSX.Element {
  const map: Record<string, { bg: string; color: string }> = {
    positive: { bg: 'rgba(34,148,58,0.1)',  color: '#22943a' },
    neutral:  { bg: 'rgba(0,51,102,0.08)',  color: 'var(--mid)' },
    negative: { bg: 'rgba(176,53,53,0.1)',  color: '#b03535' },
  }
  if (!sentiment) return <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>—</span>
  const { bg, color } = map[sentiment] ?? map['neutral']
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      backgroundColor: bg,
      borderRadius: 20,
      padding: '3px 10px',
    }}>
      <div style={{ width: 5, height: 5, borderRadius: '50%', backgroundColor: color, flexShrink: 0 }} />
      <span style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'capitalize', color, fontWeight: 600 }}>
        {sentiment}
      </span>
    </div>
  )
}

// ── Score bar ─────────────────────────────────────────────────────────────────

function ScoreBar({ score }: { score: number | null }): React.JSX.Element {
  const pct = score !== null ? Math.round(score * 100) : 0
  const color = scoreColor(score)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 120 }}>
      <div style={{
        flex: 1,
        height: 5,
        backgroundColor: 'rgba(0,51,102,0.08)',
        borderRadius: 3,
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          backgroundColor: color,
          borderRadius: 3,
          transition: 'width 0.6s ease',
        }} />
      </div>
      <span style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color, minWidth: 36, textAlign: 'right' }}>
        {scoreLabel(score)}
      </span>
    </div>
  )
}

// ── Result row ────────────────────────────────────────────────────────────────

function ResultRow({ result, rank, isFirst }: { result: RunResult; rank: number; isFirst: boolean }): React.JSX.Element {
  const [expanded, setExpanded] = useState(false)

  const rankBg = isFirst
    ? 'linear-gradient(135deg, rgba(201,168,76,0.12), rgba(201,168,76,0.04))'
    : '#fff'

  const rankBorder = isFirst
    ? '1px solid rgba(201,168,76,0.3)'
    : '1px solid rgba(0,51,102,0.07)'

  return (
    <div style={{
      background: rankBg,
      border: rankBorder,
      borderRadius: 10,
      marginBottom: 10,
      overflow: 'hidden',
      transition: 'box-shadow 0.15s',
    }}>
      {/* Row header */}
      <button
        onClick={() => result.verbatimResponse && setExpanded((e) => !e)}
        style={{
          width: '100%',
          background: 'none',
          border: 'none',
          padding: '16px 20px',
          cursor: result.verbatimResponse ? 'pointer' : 'default',
          display: 'grid',
          gridTemplateColumns: '36px 1fr 160px 120px 70px 24px',
          alignItems: 'center',
          gap: 12,
          textAlign: 'left',
        }}
      >
        {/* Rank */}
        <div style={{
          fontFamily: "'Fraunces', Georgia, serif",
          fontSize: isFirst ? 22 : 16,
          fontWeight: 300,
          color: isFirst ? 'var(--gold)' : 'var(--mid)',
          lineHeight: 1,
        }}>
          {rank}
        </div>

        {/* Variant name */}
        <div>
          <p style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 14, fontWeight: 400, color: 'var(--dark)', margin: 0 }}>
            {result.variantName}
          </p>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', margin: '2px 0 0', textTransform: 'uppercase', letterSpacing: '1px' }}>
            {result.status === 'failed' || result.status === 'error' ? 'failed' : 'completed'}
          </p>
        </div>

        {/* Score bar */}
        <ScoreBar score={result.conversionScore} />

        {/* Sentiment */}
        <SentimentPill sentiment={result.sentiment} />

        {/* Latency */}
        <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', textAlign: 'right' }}>
          {result.latencyMs ? `${(result.latencyMs / 1000).toFixed(1)}s` : '—'}
        </div>

        {/* Expand chevron */}
        {result.verbatimResponse ? (
          <div style={{
            color: 'rgba(0,51,102,0.3)',
            fontSize: 14,
            transition: 'transform 0.2s',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
          }}>
            ▾
          </div>
        ) : <div />}
      </button>

      {/* Verbatim response */}
      {expanded && result.verbatimResponse && (
        <div style={{
          borderTop: '1px solid rgba(0,51,102,0.06)',
          padding: '16px 20px 20px',
          backgroundColor: 'rgba(0,51,102,0.02)',
        }}>
          <p style={{
            fontFamily: 'var(--fb)',
            fontSize: 10,
            textTransform: 'uppercase',
            letterSpacing: '2px',
            color: 'var(--mid)',
            margin: '0 0 8px',
          }}>
            Persona Response
          </p>
          <p style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 14,
            fontWeight: 300,
            color: 'var(--dark)',
            lineHeight: 1.65,
            margin: 0,
            fontStyle: 'italic',
          }}>
            "{result.verbatimResponse}"
          </p>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SimulationResultsPage({ onLaunchAnother, onViewSegments }: Props): React.JSX.Element {
  const { campaignResults, form } = useCampaignStore()

  const sorted: RunResult[] = [...campaignResults].sort((a, b) => {
    const sa = a.conversionScore ?? -1
    const sb = b.conversionScore ?? -1
    return sb - sa
  })

  const winner = sorted[0]
  const completedCount = campaignResults.filter((r) => r.status === 'completed').length
  const avgScore = completedCount > 0
    ? sorted
        .filter((r) => r.conversionScore !== null)
        .reduce((acc, r) => acc + (r.conversionScore ?? 0), 0) / completedCount
    : null

  return (
    <div>
      {/* Hero */}
      <div style={{
        backgroundColor: 'var(--primary)',
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
        `,
        backgroundSize: '48px 48px',
        padding: '48px 48px 40px',
      }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <Eyebrow light>Simulation Results</Eyebrow>
          <h1 style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 36,
            fontWeight: 300,
            color: '#fff',
            lineHeight: 1.2,
            margin: '8px 0 4px',
          }}>
            <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>{form.name}</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.5)', margin: 0 }}>
            {form.segmentName} · {campaignResults.length} variant{campaignResults.length > 1 ? 's' : ''} tested
          </p>
        </div>
      </div>

      {/* Body */}
      <div style={{ backgroundColor: 'var(--light)', minHeight: '70vh' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '48px 48px' }}>

          {/* KPI row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 40 }}>
            {[
              {
                label: 'Top Score',
                value: scoreLabel(winner?.conversionScore ?? null),
                sub: winner?.variantName ?? '—',
                accent: scoreColor(winner?.conversionScore ?? null),
              },
              {
                label: 'Avg. Score',
                value: avgScore !== null ? `${Math.round(avgScore * 100)}%` : '—',
                sub: `${completedCount} completed`,
                accent: 'var(--gold)',
              },
              {
                label: 'Variants Run',
                value: String(completedCount),
                sub: `${campaignResults.length - completedCount} failed`,
                accent: 'var(--primary)',
              },
            ].map(({ label, value, sub, accent }) => (
              <div key={label} style={{
                backgroundColor: '#fff',
                borderRadius: 12,
                padding: '20px 24px',
                boxShadow: '0 1px 8px rgba(0,51,102,0.06)',
                display: 'flex',
                alignItems: 'stretch',
                gap: 16,
              }}>
                <div style={{ width: 3, backgroundColor: accent, borderRadius: 2, flexShrink: 0 }} />
                <div>
                  <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 32, fontWeight: 300, color: 'var(--dark)', lineHeight: 1 }}>
                    {value}
                  </div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '3px', color: 'var(--mid)', marginTop: 4 }}>
                    {label}
                  </div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginTop: 6, fontStyle: 'italic' }}>
                    {sub}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Leaderboard */}
          <Eyebrow>Performance Ranking</Eyebrow>
          <h2 style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 22,
            fontWeight: 300,
            color: 'var(--dark)',
            margin: '0 0 8px',
          }}>
            Variant leaderboard
          </h2>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 24 }}>
            Sorted by conversion score. Click a row to read the persona's verbatim response.
          </p>

          {/* Table header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '36px 1fr 160px 120px 70px 24px',
            gap: 12,
            padding: '0 20px 10px',
          }}>
            {['#', 'Variant', 'Conversion Score', 'Sentiment', 'Latency', ''].map((h) => (
              <span key={h} style={{
                fontFamily: 'var(--fb)',
                fontSize: 10,
                textTransform: 'uppercase',
                letterSpacing: '2px',
                color: 'var(--mid)',
              }}>
                {h}
              </span>
            ))}
          </div>

          {sorted.map((result, i) => (
            <ResultRow key={result.variantIndex} result={result} rank={i + 1} isFirst={i === 0} />
          ))}

          {/* Actions */}
          <div style={{ display: 'flex', gap: 12, marginTop: 36, justifyContent: 'flex-end' }}>
            <button
              onClick={onViewSegments}
              style={{
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
              }}
            >
              View Segments
            </button>
            <button
              onClick={onLaunchAnother}
              style={{
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
              }}
            >
              Launch Another Campaign
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
