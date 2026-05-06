import React, { useState } from 'react'
import Eyebrow from '../components/Eyebrow'

interface SegmentBuilderPageProps {
  onCancel: () => void
  onSaved:  () => void
}

const CATEGORIES = ['Electronics', 'Fashion', 'Home & Garden', 'Sports', 'Books', 'Food & Beverage']

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
  borderBottom: '1px solid var(--primary-10)',
}

const label: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: '2px',
  textTransform: 'uppercase',
  color: 'var(--primary)',
  marginBottom: 6,
  display: 'block',
}

const input: React.CSSProperties = {
  width: '100%',
  fontFamily: 'var(--fb)',
  fontSize: 14,
  color: 'var(--dark)',
  border: '1px solid var(--primary-30)',
  borderRadius: 6,
  padding: '10px 14px',
  outline: 'none',
  backgroundColor: '#fff',
}

const row2: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: 20,
}

const catChip = (selected: boolean): React.CSSProperties => ({
  fontFamily: 'var(--fb)',
  fontSize: 11,
  fontWeight: selected ? 700 : 400,
  letterSpacing: '1px',
  textTransform: 'uppercase',
  border: `1.5px solid ${selected ? 'var(--gold)' : 'var(--primary-30)'}`,
  borderRadius: 6,
  padding: '7px 14px',
  cursor: 'pointer',
  backgroundColor: selected ? 'rgba(200,152,42,0.08)' : '#fff',
  color: selected ? 'var(--gold)' : 'var(--mid)',
  transition: 'all 0.15s',
})

const saveBtn: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '1.5px',
  textTransform: 'uppercase',
  backgroundColor: 'var(--primary)',
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '12px 28px',
  cursor: 'pointer',
}

const cancelBtn: React.CSSProperties = {
  ...saveBtn,
  backgroundColor: 'transparent',
  color: 'var(--mid)',
  border: '1px solid var(--primary-30)',
}

interface FormState {
  name:                 string
  description:          string
  min_age:              string
  max_age:              string
  country:              string
  city:                 string
  category_affinities:  string[]
  purchase_history_days: string
  min_purchase_count:   string
}

const INITIAL: FormState = {
  name: '', description: '', min_age: '18', max_age: '65',
  country: '', city: '', category_affinities: [],
  purchase_history_days: '90', min_purchase_count: '',
}

export default function SegmentBuilderPage({ onCancel, onSaved }: SegmentBuilderPageProps): React.JSX.Element {
  const [form, setForm]     = useState<FormState>(INITIAL)
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState<string | null>(null)

  function set(key: keyof FormState, value: string): void {
    setForm((f) => ({ ...f, [key]: value }))
  }

  function toggleCategory(cat: string): void {
    setForm((f) => ({
      ...f,
      category_affinities: f.category_affinities.includes(cat)
        ? f.category_affinities.filter((c) => c !== cat)
        : [...f.category_affinities, cat],
    }))
  }

  async function handleSave(): Promise<void> {
    if (!form.name.trim()) { setError('Segment name is required.'); return }
    setSaving(true)
    setError(null)
    try {
      const body = {
        name:        form.name.trim(),
        description: form.description.trim() || null,
        definition: {
          age_range: form.min_age && form.max_age
            ? { min_age: parseInt(form.min_age), max_age: parseInt(form.max_age) }
            : null,
          geo: form.city || form.country
            ? { city: form.city || null, country: form.country || null }
            : null,
          category_affinities:   form.category_affinities,
          purchase_history_days: parseInt(form.purchase_history_days) || 90,
          min_purchase_count:    form.min_purchase_count ? parseInt(form.min_purchase_count) : null,
        },
      }
      const resp = await fetch('/api/segments', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })
      if (!resp.ok) throw new Error(`API error ${resp.status}`)
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      {/* Hero */}
      <div style={heroStyle}>
        <div style={{ maxWidth: 860, margin: '0 auto' }}>
          <h1 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 36, fontWeight: 300, color: '#fff', lineHeight: 1.2 }}>
            Define a <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>segment</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.55)', marginTop: 8 }}>
            Set demographic filters and category affinities to scope the audience for simulation.
          </p>
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--light)' }}>
        {/* Basic info */}
        <div style={section}>
          <Eyebrow>Basic Info</Eyebrow>
          <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, color: '#0a1628', margin: '0 0 24px' }}>
            Name and description
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={label}>Segment name *</label>
              <input style={input} value={form.name} onChange={(e) => set('name', e.target.value)}
                placeholder="e.g. Gen Z — Madrid 18-24" />
            </div>
            <div>
              <label style={label}>Description</label>
              <textarea style={{ ...input, resize: 'vertical', minHeight: 72 }}
                value={form.description} onChange={(e) => set('description', e.target.value)}
                placeholder="Brief description of this segment's characteristics…" />
            </div>
          </div>
        </div>

        {/* Demographics */}
        <div style={section}>
          <Eyebrow>Demographics</Eyebrow>
          <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, color: '#0a1628', margin: '0 0 24px' }}>
            Age range and geography
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={row2}>
              <div>
                <label style={label}>Min age</label>
                <input style={input} type="number" value={form.min_age} onChange={(e) => set('min_age', e.target.value)} min={0} max={120} />
              </div>
              <div>
                <label style={label}>Max age</label>
                <input style={input} type="number" value={form.max_age} onChange={(e) => set('max_age', e.target.value)} min={0} max={120} />
              </div>
            </div>
            <div style={row2}>
              <div>
                <label style={label}>City</label>
                <input style={input} value={form.city} onChange={(e) => set('city', e.target.value)} placeholder="e.g. Madrid" />
              </div>
              <div>
                <label style={label}>Country</label>
                <input style={input} value={form.country} onChange={(e) => set('country', e.target.value)} placeholder="e.g. Spain" />
              </div>
            </div>
          </div>
        </div>

        {/* Category affinities */}
        <div style={section}>
          <Eyebrow>Behavioral Filters</Eyebrow>
          <h2 style={{ fontFamily: "'Fraunces', Georgia, serif", fontSize: 20, fontWeight: 300, color: '#0a1628', margin: '0 0 8px' }}>
            Category affinities
          </h2>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 20 }}>
            Only behavioral events matching these categories will be included in the feature matrix.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 28 }}>
            {CATEGORIES.map((cat) => (
              <button key={cat} style={catChip(form.category_affinities.includes(cat))}
                onClick={() => toggleCategory(cat)}>{cat}</button>
            ))}
          </div>
          <div style={row2}>
            <div>
              <label style={label}>Lookback window (days)</label>
              <input style={input} type="number" value={form.purchase_history_days}
                onChange={(e) => set('purchase_history_days', e.target.value)} min={1} max={365} />
            </div>
            <div>
              <label style={label}>Min. purchase count</label>
              <input style={input} type="number" value={form.min_purchase_count}
                onChange={(e) => set('min_purchase_count', e.target.value)} min={0} placeholder="No minimum" />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div style={{ ...section, borderBottom: 'none' }}>
          {error && (
            <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#7a1020', backgroundColor: '#fdeaea', padding: '10px 16px', borderRadius: 6, marginBottom: 20 }}>
              {error}
            </div>
          )}
          <div style={{ display: 'flex', gap: 12 }}>
            <button style={saveBtn} onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save Segment'}
            </button>
            <button style={cancelBtn} onClick={onCancel}>Cancel</button>
          </div>
        </div>
      </div>
    </div>
  )
}
