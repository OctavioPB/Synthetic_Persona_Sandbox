import React, { useEffect, useMemo, useState } from 'react'
import Eyebrow from '../components/Eyebrow'
import ConversionTrendChart, { TrendDataPoint } from '../components/charts/ConversionTrendChart'
import StimulusTypeChart, { StimulusBarData } from '../components/charts/StimulusTypeChart'
import VariantComparisonChart, { ComparisonItem } from '../components/charts/VariantComparisonChart'
import { api, SimulationRunResponse } from '../services/api'

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreColor(s: number | null): string {
  if (s === null) return 'var(--mid)'
  if (s >= 0.65)  return '#22943a'
  if (s >= 0.40)  return '#b07d10'
  return '#b03535'
}

function fmtScore(s: number | null): string {
  return s !== null ? `${Math.round(s * 100)}%` : '—'
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' })
}

function fmtLatency(ms: number | null): string {
  return ms !== null ? `${(ms / 1000).toFixed(1)}s` : '—'
}

function exportCSV(runs: SimulationRunResponse[]): void {
  const headers = ['ID', 'Date', 'Stimulus Type', 'Conversion Score', 'Sentiment', 'Latency (ms)', 'Status']
  const rows = runs.map((r) => [
    r.id,
    r.created_at,
    r.stimulus_type,
    r.conversion_score?.toFixed(3) ?? '',
    r.sentiment ?? '',
    r.latency_ms?.toString() ?? '',
    r.status,
  ])
  const csv = [headers, ...rows].map((row) => row.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `simulations_${new Date().toISOString().split('T')[0]}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

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

const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius: 'var(--radius-md)',
  padding: '28px',
  boxShadow: 'var(--shadow-card)',
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

const filterInput: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 12,
  color: 'var(--dark)',
  border: '1px solid var(--primary-10)',
  borderRadius: 6,
  padding: '7px 10px',
  outline: 'none',
  backgroundColor: 'var(--white)',
}

// ── KPI stat card ─────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, accent = 'var(--gold)' }: {
  label: string
  value: string
  sub?: string
  accent?: string
}): React.JSX.Element {
  return (
    <div style={{ ...card, display: 'flex', alignItems: 'stretch', gap: 16 }}>
      <div style={{ width: 3, backgroundColor: accent, borderRadius: 2, flexShrink: 0 }} />
      <div>
        <div style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 30, fontWeight: 300, color: 'var(--dark)', lineHeight: 1 }}>
          {value}
        </div>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '3px', color: 'var(--mid)', marginTop: 5 }}>
          {label}
        </div>
        {sub && (
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginTop: 4, fontStyle: 'italic' }}>
            {sub}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Sentiment pill ────────────────────────────────────────────────────────────

function SentimentPill({ sentiment }: { sentiment: string | null }): React.JSX.Element {
  const map: Record<string, { bg: string; color: string }> = {
    positive: { bg: 'rgba(34,148,58,0.1)',  color: '#22943a' },
    neutral:  { bg: 'rgba(0,51,102,0.08)',  color: 'var(--mid)' },
    negative: { bg: 'rgba(176,53,53,0.1)',  color: '#b03535' },
  }
  if (!sentiment) return <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>—</span>
  const { bg, color } = map[sentiment] ?? map['neutral']
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4, backgroundColor: bg, borderRadius: 20, padding: '2px 8px' }}>
      <div style={{ width: 5, height: 5, borderRadius: '50%', backgroundColor: color, flexShrink: 0 }} />
      <span style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'capitalize', color, fontWeight: 600 }}>{sentiment}</span>
    </div>
  )
}

// ── Tab switcher ──────────────────────────────────────────────────────────────

type Tab = 'overview' | 'history' | 'compare'

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }): React.JSX.Element {
  const tabs: Array<{ id: Tab; label: string }> = [
    { id: 'overview', label: 'Overview'  },
    { id: 'history',  label: 'History'   },
    { id: 'compare',  label: 'Compare'   },
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

// ── Overview tab ──────────────────────────────────────────────────────────────

function OverviewTab({ runs }: { runs: SimulationRunResponse[] }): React.JSX.Element {
  const completed = useMemo(() => runs.filter((r) => r.status === 'completed' && r.conversion_score !== null), [runs])

  const trendData: TrendDataPoint[] = useMemo(() => {
    const byDay: Record<string, number[]> = {}
    completed.forEach((r) => {
      const day = r.created_at.split('T')[0]
      if (!byDay[day]) byDay[day] = []
      byDay[day].push(r.conversion_score!)
    })
    return Object.entries(byDay)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, scores]) => ({
        date,
        avg_score: scores.reduce((a, v) => a + v, 0) / scores.length,
        count: scores.length,
      }))
  }, [completed])

  const stimulusData: StimulusBarData[] = useMemo(() => {
    return (['ad_copy', 'price_change', 'promo'] as const).map((t) => {
      const typeRuns = completed.filter((r) => r.stimulus_type === t)
      const avg = typeRuns.length > 0
        ? typeRuns.reduce((a, r) => a + (r.conversion_score ?? 0), 0) / typeRuns.length
        : 0
      return { type: t.replace('_', ' '), avg_score: avg, count: typeRuns.length }
    })
  }, [completed])

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
      {/* Conversion trend */}
      <div style={card}>
        <Eyebrow>Conversion Trend</Eyebrow>
        <h3 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 16, fontWeight: 400, color: 'var(--dark)', margin: '0 0 20px' }}>
          Daily avg score
        </h3>
        <ConversionTrendChart data={trendData} />
      </div>

      {/* Stimulus type performance */}
      <div style={card}>
        <Eyebrow>By Stimulus Type</Eyebrow>
        <h3 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 16, fontWeight: 400, color: 'var(--dark)', margin: '0 0 20px' }}>
          Avg conversion score
        </h3>
        <StimulusTypeChart data={stimulusData} />
      </div>
    </div>
  )
}

// ── History tab ───────────────────────────────────────────────────────────────

type SortKey = 'date' | 'score' | 'latency'
type SortDir = 'asc' | 'desc'

function HistoryTab({ runs }: { runs: SimulationRunResponse[] }): React.JSX.Element {
  const [filterType,    setFilterType]    = useState('')
  const [filterStatus,  setFilterStatus]  = useState('')
  const [filterMinScore, setFilterMinScore] = useState('')
  const [filterMaxScore, setFilterMaxScore] = useState('')
  const [sortKey,  setSortKey]  = useState<SortKey>('date')
  const [sortDir,  setSortDir]  = useState<SortDir>('desc')

  const filtered = useMemo(() => {
    let result = [...runs]
    if (filterType)   result = result.filter((r) => r.stimulus_type === filterType)
    if (filterStatus) result = result.filter((r) => r.status === filterStatus)
    const min = parseFloat(filterMinScore) / 100
    const max = parseFloat(filterMaxScore) / 100
    if (!isNaN(min)) result = result.filter((r) => (r.conversion_score ?? 0) >= min)
    if (!isNaN(max)) result = result.filter((r) => (r.conversion_score ?? 1) <= max)

    result.sort((a, b) => {
      let va: number
      let vb: number
      if (sortKey === 'score') {
        va = a.conversion_score ?? -1
        vb = b.conversion_score ?? -1
      } else if (sortKey === 'latency') {
        va = a.latency_ms ?? 0
        vb = b.latency_ms ?? 0
      } else {
        va = new Date(a.created_at).getTime()
        vb = new Date(b.created_at).getTime()
      }
      return sortDir === 'desc' ? vb - va : va - vb
    })
    return result
  }, [runs, filterType, filterStatus, filterMinScore, filterMaxScore, sortKey, sortDir])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    else { setSortKey(key); setSortDir('desc') }
  }

  const sortIndicator = (key: SortKey) =>
    sortKey === key ? (sortDir === 'desc' ? ' ▾' : ' ▴') : ''

  const thStyle: React.CSSProperties = {
    fontFamily: 'var(--fb)',
    fontSize: 10,
    textTransform: 'uppercase',
    letterSpacing: '2px',
    color: '#fff',
    padding: '12px 16px',
    textAlign: 'left',
    fontWeight: 600,
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  }

  return (
    <div>
      {/* Filter bar */}
      <div style={{ ...card, display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: 16 }}>
        <div>
          <span style={labelStyle}>Stimulus Type</span>
          <select style={filterInput} value={filterType} onChange={(e) => setFilterType(e.target.value)}>
            <option value="">All</option>
            <option value="ad_copy">Ad Copy</option>
            <option value="price_change">Price Change</option>
            <option value="promo">Promo</option>
          </select>
        </div>
        <div>
          <span style={labelStyle}>Status</span>
          <select style={filterInput} value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="">All</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>
        <div>
          <span style={labelStyle}>Min Score (%)</span>
          <input type="number" min="0" max="100" style={{ ...filterInput, width: 80 }}
            value={filterMinScore} placeholder="0"
            onChange={(e) => setFilterMinScore(e.target.value)} />
        </div>
        <div>
          <span style={labelStyle}>Max Score (%)</span>
          <input type="number" min="0" max="100" style={{ ...filterInput, width: 80 }}
            value={filterMaxScore} placeholder="100"
            onChange={(e) => setFilterMaxScore(e.target.value)} />
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <span style={{ ...labelStyle, marginBottom: 0, alignSelf: 'center' }}>
            {filtered.length} run{filtered.length !== 1 ? 's' : ''}
          </span>
          <button
            onClick={() => exportCSV(filtered)}
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
              padding: '8px 16px',
              cursor: 'pointer',
            }}
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden', boxShadow: 'var(--shadow-card)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead style={{ backgroundColor: 'var(--primary)' }}>
            <tr>
              {[
                { key: null,       label: 'Run ID'       },
                { key: 'date',     label: 'Date'         },
                { key: null,       label: 'Stimulus Type'},
                { key: 'score',    label: 'Score'        },
                { key: null,       label: 'Sentiment'    },
                { key: 'latency',  label: 'Latency'      },
                { key: null,       label: 'Status'       },
              ].map(({ key, label }) => (
                <th
                  key={label}
                  style={thStyle}
                  onClick={key ? () => toggleSort(key as SortKey) : undefined}
                >
                  {label}{key ? sortIndicator(key as SortKey) : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: '32px', textAlign: 'center', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', backgroundColor: 'var(--white)' }}>
                  No runs match the current filters.
                </td>
              </tr>
            ) : (
              filtered.map((r, i) => (
                <tr key={r.id} style={{ backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
                  <td style={{ padding: '10px 16px', fontFamily: 'Courier New', fontSize: 11, color: 'var(--mid)' }}>
                    {r.id.split('-')[0]}…
                  </td>
                  <td style={{ padding: '10px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', whiteSpace: 'nowrap' }}>
                    {fmtDate(r.created_at)}
                  </td>
                  <td style={{ padding: '10px 16px' }}>
                    <span style={{
                      fontFamily: 'var(--fb)',
                      fontSize: 10,
                      textTransform: 'uppercase',
                      letterSpacing: '1px',
                      backgroundColor: 'rgba(201,168,76,0.1)',
                      color: 'var(--gold)',
                      borderRadius: 4,
                      padding: '2px 7px',
                      fontWeight: 700,
                    }}>
                      {r.stimulus_type.replace('_', ' ')}
                    </span>
                  </td>
                  <td style={{ padding: '10px 16px', fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: scoreColor(r.conversion_score) }}>
                    {fmtScore(r.conversion_score)}
                  </td>
                  <td style={{ padding: '10px 16px' }}>
                    <SentimentPill sentiment={r.sentiment} />
                  </td>
                  <td style={{ padding: '10px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
                    {fmtLatency(r.latency_ms)}
                  </td>
                  <td style={{ padding: '10px 16px' }}>
                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 5,
                      backgroundColor: r.status === 'completed'
                        ? 'rgba(34,148,58,0.1)'
                        : r.status === 'failed'
                          ? 'rgba(176,53,53,0.1)'
                          : 'rgba(240,112,32,0.1)',
                      borderRadius: 20,
                      padding: '2px 9px',
                    }}>
                      <div style={{
                        width: 5, height: 5, borderRadius: '50%', flexShrink: 0,
                        backgroundColor: r.status === 'completed' ? '#22943a'
                          : r.status === 'failed' ? '#b03535' : '#f07020',
                      }} />
                      <span style={{
                        fontFamily: 'var(--fb)',
                        fontSize: 10,
                        textTransform: 'capitalize',
                        fontWeight: 600,
                        color: r.status === 'completed' ? '#22943a'
                          : r.status === 'failed' ? '#b03535' : '#f07020',
                      }}>
                        {r.status}
                      </span>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Compare tab ───────────────────────────────────────────────────────────────

function CompareTab({ runs }: { runs: SimulationRunResponse[] }): React.JSX.Element {
  const completed = runs.filter((r) => r.status === 'completed' && r.conversion_score !== null)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const chartData: ComparisonItem[] = completed
    .filter((r) => selected.has(r.id))
    .map((r) => ({
      name: `${r.stimulus_type.replace('_', ' ')} · ${fmtDate(r.created_at)}`,
      score: r.conversion_score!,
    }))

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20 }}>
      {/* Selection list */}
      <div style={{ ...card, maxHeight: 480, overflowY: 'auto' }}>
        <Eyebrow>Select Runs</Eyebrow>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 16 }}>
          Choose completed runs to compare side-by-side.
        </p>
        {completed.length === 0 ? (
          <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>No completed runs yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {completed.map((r) => {
              const isSelected = selected.has(r.id)
              return (
                <label
                  key={r.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '9px 12px',
                    borderRadius: 8,
                    border: `1.5px solid ${isSelected ? 'var(--gold)' : 'var(--primary-10)'}`,
                    backgroundColor: isSelected ? 'rgba(201,168,76,0.06)' : 'transparent',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggle(r.id)}
                    style={{ accentColor: 'var(--gold)', width: 14, height: 14, flexShrink: 0 }}
                  />
                  <div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--dark)', fontWeight: 500 }}>
                      {r.stimulus_type.replace('_', ' ')}
                    </div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>
                      {fmtDate(r.created_at)} · {fmtScore(r.conversion_score)}
                    </div>
                  </div>
                </label>
              )
            })}
          </div>
        )}
      </div>

      {/* Chart */}
      <div style={card}>
        <Eyebrow>Variant Comparison</Eyebrow>
        <h3 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 16, fontWeight: 400, color: 'var(--dark)', margin: '0 0 20px' }}>
          Conversion score by run
        </h3>
        <VariantComparisonChart data={chartData} />
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AnalyticsPage(): React.JSX.Element {
  const [runs, setRuns]     = useState<SimulationRunResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState<string | null>(null)
  const [tab, setTab]       = useState<Tab>('overview')

  useEffect(() => {
    api.simulations.list({ size: 200 })
      .then(setRuns)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  const completed  = runs.filter((r) => r.status === 'completed' && r.conversion_score !== null)
  const totalRuns  = runs.length
  const avgScore   = completed.length > 0
    ? completed.reduce((a, r) => a + (r.conversion_score ?? 0), 0) / completed.length
    : null

  const topType = useMemo(() => {
    if (completed.length === 0) return null
    const byType: Record<string, number[]> = {}
    completed.forEach((r) => {
      if (!byType[r.stimulus_type]) byType[r.stimulus_type] = []
      byType[r.stimulus_type].push(r.conversion_score!)
    })
    const best = Object.entries(byType)
      .map(([t, scores]) => ({ t, avg: scores.reduce((a, v) => a + v, 0) / scores.length }))
      .sort((a, b) => b.avg - a.avg)[0]
    return best ? best.t.replace('_', ' ') : null
  }, [completed])

  const last7d = useMemo(() => {
    const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000
    return runs.filter((r) => new Date(r.created_at).getTime() >= cutoff).length
  }, [runs])

  return (
    <div>
      {/* Hero with tabs */}
      <div style={heroStyle}>
        <div style={contentWrap}>
          <Eyebrow light>Campaign Analytics</Eyebrow>
          <h1 style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 36,
            fontWeight: 300,
            color: '#fff',
            lineHeight: 1.2,
            margin: '8px 0 4px',
          }}>
            Simulation <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>performance</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.5)', margin: 0 }}>
            Historical conversion data across all campaign runs.
          </p>
          <TabBar active={tab} onChange={setTab} />
        </div>
      </div>

      {/* Body */}
      <div style={{ backgroundColor: 'var(--light)', minHeight: '70vh' }}>
        <div style={{ ...contentWrap, padding: '40px 48px' }}>

          {/* KPI row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
            <KpiCard label="Total Runs"       value={String(totalRuns)}                      accent="var(--primary-60)" />
            <KpiCard label="Avg Conv. Score"  value={avgScore !== null ? fmtScore(avgScore) : '—'} accent="var(--gold)" />
            <KpiCard label="Best Stimulus"    value={topType ?? '—'}                          accent="#27B97C" />
            <KpiCard label="Runs — Last 7 Days" value={String(last7d)}                       accent="#7C4DBD" />
          </div>

          {/* Tab content */}
          {loading && (
            <div style={{ textAlign: 'center', padding: '48px 0', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
              Loading simulation history…
            </div>
          )}
          {error && (
            <div style={{ textAlign: 'center', padding: '32px 0', fontFamily: 'var(--fb)', fontSize: 13, color: '#b03535' }}>
              {error} — is the API running?
            </div>
          )}
          {!loading && !error && tab === 'overview' && <OverviewTab runs={runs} />}
          {!loading && !error && tab === 'history'  && <HistoryTab  runs={runs} />}
          {!loading && !error && tab === 'compare'  && <CompareTab  runs={runs} />}
        </div>
      </div>
    </div>
  )
}
