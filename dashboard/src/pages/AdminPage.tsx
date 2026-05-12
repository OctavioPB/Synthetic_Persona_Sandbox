import React, { useCallback, useEffect, useState } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, AdminStats, ClearResult, SeedResult } from '../services/api'

// ── Styles ────────────────────────────────────────────────────────────────────

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
  padding: '40px 48px',
}

const card: React.CSSProperties = {
  backgroundColor: '#fff',
  borderRadius: 12,
  border: '1px solid rgba(0,51,102,0.08)',
  padding: '28px',
  marginBottom: 24,
}

const label: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 11,
  textTransform: 'uppercase' as const,
  letterSpacing: '2px',
  color: 'var(--mid)',
  marginBottom: 6,
  display: 'block',
}

const inputStyle: React.CSSProperties = {
  width: 80,
  fontFamily: 'var(--fb)',
  fontSize: 13,
  color: 'var(--dark)',
  border: '1px solid rgba(0,51,102,0.15)',
  borderRadius: 6,
  padding: '8px 10px',
  outline: 'none',
  backgroundColor: '#fff',
  textAlign: 'center' as const,
}

const primaryBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '1.5px',
  textTransform: 'uppercase' as const,
  backgroundColor: 'var(--gold)',
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '10px 24px',
  cursor: 'pointer',
}

const dangerBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: '1.5px',
  textTransform: 'uppercase' as const,
  backgroundColor: '#b03535',
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '10px 24px',
  cursor: 'pointer',
}

const ghostBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 11,
  letterSpacing: '1px',
  textTransform: 'uppercase' as const,
  background: 'none',
  border: '1px solid rgba(0,51,102,0.2)',
  borderRadius: 6,
  padding: '10px 18px',
  cursor: 'pointer',
  color: 'var(--mid)',
}

// ── Stat pill ─────────────────────────────────────────────────────────────────

function StatPill({ label: lbl, value, accent }: { label: string; value: number; accent: string }): React.JSX.Element {
  return (
    <div style={{
      flex: 1,
      backgroundColor: '#fafafa',
      border: '1px solid rgba(0,51,102,0.07)',
      borderRadius: 10,
      padding: '16px 20px',
      textAlign: 'center',
    }}>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 28, fontWeight: 700, color: accent, lineHeight: 1 }}>
        {value}
      </div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', marginTop: 6 }}>
        {lbl}
      </div>
    </div>
  )
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ msg, ok }: { msg: string; ok: boolean }): React.JSX.Element {
  return (
    <div style={{
      fontFamily: 'var(--fb)',
      fontSize: 12,
      color: ok ? '#22943a' : '#b03535',
      backgroundColor: ok ? 'rgba(34,148,58,0.07)' : 'rgba(176,53,53,0.07)',
      border: `1px solid ${ok ? 'rgba(34,148,58,0.2)' : 'rgba(176,53,53,0.2)'}`,
      borderRadius: 8,
      padding: '10px 16px',
      marginTop: 16,
    }}>
      {msg}
    </div>
  )
}

// ── Confirm modal ─────────────────────────────────────────────────────────────

function ConfirmModal({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }): React.JSX.Element {
  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(0,0,0,0.45)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 200,
    }}>
      <div style={{
        backgroundColor: '#fff',
        borderRadius: 14,
        padding: '32px 36px',
        maxWidth: 400,
        width: '90%',
        boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
      }}>
        <h3 style={{
          fontFamily: "'Fraunces', Georgia, serif",
          fontSize: 20,
          fontWeight: 400,
          color: 'var(--dark)',
          margin: '0 0 10px',
        }}>
          Clear all data?
        </h3>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', margin: '0 0 24px', lineHeight: 1.5 }}>
          This will permanently delete all segments, campaigns, variants and simulation runs for this organisation. This action cannot be undone.
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button style={ghostBtn} onClick={onCancel}>Cancel</button>
          <button style={dangerBtn} onClick={onConfirm}>Yes, clear everything</button>
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AdminPage(): React.JSX.Element {
  const [stats,       setStats]       = useState<AdminStats | null>(null)
  const [statsErr,    setStatsErr]    = useState(false)

  const [nSegments,   setNSegments]   = useState(6)
  const [nCampaigns,  setNCampaigns]  = useState(2)
  const [nRuns,       setNRuns]       = useState(8)

  const [seeding,     setSeeding]     = useState(false)
  const [seedResult,  setSeedResult]  = useState<SeedResult | null>(null)
  const [seedErr,     setSeedErr]     = useState<string | null>(null)

  const [clearing,    setClearing]    = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [clearResult, setClearResult] = useState<ClearResult | null>(null)
  const [clearErr,    setClearErr]    = useState<string | null>(null)

  const loadStats = useCallback(() => {
    setStatsErr(false)
    api.admin.stats()
      .then(setStats)
      .catch(() => setStatsErr(true))
  }, [])

  useEffect(() => { loadStats() }, [loadStats])

  const handleSeed = async () => {
    setSeeding(true)
    setSeedResult(null)
    setSeedErr(null)
    try {
      const result = await api.admin.seed({ n_segments: nSegments, n_campaigns: nCampaigns, n_runs: nRuns })
      setSeedResult(result)
      loadStats()
    } catch (e: unknown) {
      setSeedErr(e instanceof Error ? e.message : 'Seed failed')
    } finally {
      setSeeding(false)
    }
  }

  const handleClear = async () => {
    setShowConfirm(false)
    setClearing(true)
    setClearResult(null)
    setClearErr(null)
    try {
      const result = await api.admin.clear()
      setClearResult(result)
      loadStats()
    } catch (e: unknown) {
      setClearErr(e instanceof Error ? e.message : 'Clear failed')
    } finally {
      setClearing(false)
    }
  }

  return (
    <>
      {showConfirm && (
        <ConfirmModal
          onConfirm={handleClear}
          onCancel={() => setShowConfirm(false)}
        />
      )}

      {/* Hero */}
      <div style={heroStyle}>
        <div style={{ maxWidth: 860, margin: '0 auto' }}>
          <Eyebrow light>Admin</Eyebrow>
          <h1 style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 36,
            fontWeight: 300,
            color: '#fff',
            lineHeight: 1.2,
            margin: '8px 0 4px',
          }}>
            Database{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>controls</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: 0 }}>
            Seed randomised demo data or wipe the database. Development only.
          </p>
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--light)', minHeight: '70vh' }}>
        <div style={section}>

          {/* ── Current stats ── */}
          <div style={{ ...card, marginBottom: 32 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div>
                <Eyebrow>Current state</Eyebrow>
                <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, color: 'var(--dark)', margin: 0 }}>
                  Database rows
                </h2>
              </div>
              <button style={ghostBtn} onClick={loadStats}>↺ Refresh</button>
            </div>

            {statsErr ? (
              <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#b03535' }}>
                Could not load stats — is the API running?
              </p>
            ) : stats ? (
              <div style={{ display: 'flex', gap: 12 }}>
                <StatPill label="Segments"         value={stats.segments}          accent="var(--primary)" />
                <StatPill label="Campaigns"        value={stats.campaigns}         accent="var(--gold)" />
                <StatPill label="Variants"         value={stats.campaign_variants} accent="#27B97C" />
                <StatPill label="Simulation Runs"  value={stats.simulation_runs}   accent="#7C4DBD" />
              </div>
            ) : (
              <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>Loading…</p>
            )}
          </div>

          {/* ── Seed section ── */}
          <div style={card}>
            <Eyebrow>Populate</Eyebrow>
            <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, color: 'var(--dark)', margin: '0 0 6px' }}>
              Seed synthetic data
            </h2>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', margin: '0 0 24px', lineHeight: 1.5 }}>
              Generates randomised segments, campaigns, variants and completed simulation runs using realistic Spanish market profiles.
            </p>

            <div style={{ display: 'flex', gap: 32, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 24 }}>
              <div>
                <span style={label}>Segments <span style={{ color: 'rgba(0,51,102,0.35)' }}>(max 6)</span></span>
                <input
                  type="number"
                  min={1}
                  max={6}
                  style={inputStyle}
                  value={nSegments}
                  onChange={(e) => setNSegments(Math.max(1, Math.min(6, Number(e.target.value))))}
                />
              </div>
              <div>
                <span style={label}>Campaigns <span style={{ color: 'rgba(0,51,102,0.35)' }}>(per segment, max 4)</span></span>
                <input
                  type="number"
                  min={1}
                  max={4}
                  style={inputStyle}
                  value={nCampaigns}
                  onChange={(e) => setNCampaigns(Math.max(1, Math.min(4, Number(e.target.value))))}
                />
              </div>
              <div>
                <span style={label}>Sim runs <span style={{ color: 'rgba(0,51,102,0.35)' }}>(per segment, max 20)</span></span>
                <input
                  type="number"
                  min={1}
                  max={20}
                  style={inputStyle}
                  value={nRuns}
                  onChange={(e) => setNRuns(Math.max(1, Math.min(20, Number(e.target.value))))}
                />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <button
                style={{ ...primaryBtn, opacity: seeding ? 0.6 : 1, cursor: seeding ? 'not-allowed' : 'pointer' }}
                disabled={seeding}
                onClick={handleSeed}
              >
                {seeding ? 'Seeding…' : '⬆ Seed database'}
              </button>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'rgba(0,51,102,0.35)' }}>
                Will create ~{nSegments * (nCampaigns + nRuns)} rows
              </span>
            </div>

            {seedResult && <Toast msg={seedResult.message} ok={true} />}
            {seedErr    && <Toast msg={seedErr}            ok={false} />}
          </div>

          {/* ── Clear section ── */}
          <div style={{ ...card, border: '1px solid rgba(176,53,53,0.18)', backgroundColor: 'rgba(176,53,53,0.02)' }}>
            <Eyebrow>Danger zone</Eyebrow>
            <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, color: '#b03535', margin: '0 0 6px' }}>
              Clear database
            </h2>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', margin: '0 0 20px', lineHeight: 1.5 }}>
              Deletes all segments, campaigns, variants and simulation runs for this organisation. The organisation account itself is not affected.
            </p>

            <button
              style={{ ...dangerBtn, opacity: clearing ? 0.6 : 1, cursor: clearing ? 'not-allowed' : 'pointer' }}
              disabled={clearing}
              onClick={() => setShowConfirm(true)}
            >
              {clearing ? 'Clearing…' : '✕ Clear all data'}
            </button>

            {clearResult && <Toast msg={clearResult.message} ok={true} />}
            {clearErr    && <Toast msg={clearErr}            ok={false} />}
          </div>

        </div>
      </div>
    </>
  )
}
