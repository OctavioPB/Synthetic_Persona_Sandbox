import React, { useState } from 'react'
import { StimulusPayload, StimulusType } from '../store/campaignStore'

interface Props {
  onConfirm: (variantName: string, stimulus: StimulusPayload) => void
  onCancel: () => void
}

const TYPES: Array<{ id: StimulusType; label: string; desc: string }> = [
  { id: 'ad_copy',      label: 'Ad Copy',     desc: 'Headline, body copy & CTA' },
  { id: 'price_change', label: 'Price Change', desc: 'Simulate a product price drop' },
  { id: 'promo',        label: 'Promo Code',   desc: 'Discount code offer' },
]

const label: React.CSSProperties = {
  fontFamily: 'var(--fb)',
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: '2px',
  color: 'var(--mid)',
  marginBottom: 6,
  display: 'block',
}

const input: React.CSSProperties = {
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

const row2: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: 12,
}

function Field({
  label: lbl,
  type = 'text',
  value,
  onChange,
  placeholder,
}: {
  label: string
  type?: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}): React.JSX.Element {
  return (
    <div style={{ marginBottom: 14 }}>
      <span style={label}>{lbl}</span>
      <input
        type={type}
        style={input}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

export default function StimulusBuilder({ onConfirm, onCancel }: Props): React.JSX.Element {
  const [variantName, setVariantName] = useState('')
  const [stimType, setStimType] = useState<StimulusType>('ad_copy')

  const [headline, setHeadline]         = useState('')
  const [bodyCopy, setBodyCopy]         = useState('')
  const [cta, setCta]                   = useState('')

  const [productName, setProductName]   = useState('')
  const [origPrice, setOrigPrice]       = useState('')
  const [newPrice, setNewPrice]         = useState('')

  const [promoCode, setPromoCode]       = useState('')
  const [discValue, setDiscValue]       = useState('')
  const [discType, setDiscType]         = useState<'percent' | 'fixed'>('percent')
  const [expiryDays, setExpiryDays]     = useState('')

  const isValid = (): boolean => {
    if (!variantName.trim()) return false
    if (stimType === 'ad_copy')
      return !!(headline.trim() && bodyCopy.trim() && cta.trim())
    if (stimType === 'price_change')
      return !!(productName.trim() && origPrice && newPrice)
    return !!(promoCode.trim() && discValue)
  }

  const handleConfirm = () => {
    let stimulus: StimulusPayload
    if (stimType === 'ad_copy') {
      stimulus = {
        type: 'ad_copy',
        headline: headline.trim(),
        body_copy: bodyCopy.trim(),
        cta: cta.trim(),
      }
    } else if (stimType === 'price_change') {
      stimulus = {
        type: 'price_change',
        product_name: productName.trim(),
        original_price: parseFloat(origPrice),
        new_price: parseFloat(newPrice),
      }
    } else {
      stimulus = {
        type: 'promo',
        promo_code: promoCode.trim(),
        discount_value: parseFloat(discValue),
        discount_type: discType,
        ...(expiryDays ? { expiry_days: parseInt(expiryDays, 10) } : {}),
      }
    }
    onConfirm(variantName.trim(), stimulus)
  }

  return (
    <div style={{
      backgroundColor: '#fff',
      border: '1px solid rgba(0,51,102,0.12)',
      borderRadius: 12,
      padding: '24px 28px',
    }}>
      <p style={{
        fontFamily: "'Fraunces', Georgia, serif",
        fontSize: 16,
        fontWeight: 400,
        color: 'var(--dark)',
        margin: '0 0 20px',
      }}>
        New <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>Variant</em>
      </p>

      {/* Variant name */}
      <Field label="Variant Name" value={variantName} onChange={setVariantName} placeholder="e.g. Summer Hero Banner" />

      {/* Stimulus type picker */}
      <span style={label}>Stimulus Type</span>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 20 }}>
        {TYPES.map(({ id, label: lbl, desc }) => {
          const active = stimType === id
          return (
            <button
              key={id}
              onClick={() => setStimType(id)}
              style={{
                background: active ? 'rgba(201,168,76,0.08)' : '#fafafa',
                border: `1.5px solid ${active ? 'var(--gold)' : 'rgba(0,51,102,0.12)'}`,
                borderRadius: 8,
                padding: '12px 10px',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'border-color 0.15s, background 0.15s',
              }}
            >
              <div style={{
                fontFamily: 'var(--fb)',
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: '1px',
                textTransform: 'uppercase',
                color: active ? 'var(--gold)' : 'var(--mid)',
                marginBottom: 4,
              }}>
                {lbl}
              </div>
              <div style={{
                fontFamily: 'var(--fb)',
                fontSize: 10,
                color: 'rgba(0,51,102,0.45)',
                lineHeight: 1.4,
              }}>
                {desc}
              </div>
            </button>
          )
        })}
      </div>

      {/* Dynamic fields */}
      {stimType === 'ad_copy' && (
        <>
          <Field label="Headline" value={headline} onChange={setHeadline} placeholder="Summer Sale — Up to 50% Off" />
          <div style={{ marginBottom: 14 }}>
            <span style={label}>Body Copy</span>
            <textarea
              rows={3}
              style={{ ...input, resize: 'vertical' } as React.CSSProperties}
              value={bodyCopy}
              placeholder="Discover curated deals on your favourite categories."
              onChange={(e) => setBodyCopy(e.target.value)}
            />
          </div>
          <Field label="Call to Action" value={cta} onChange={setCta} placeholder="Shop Now" />
        </>
      )}

      {stimType === 'price_change' && (
        <>
          <Field label="Product Name" value={productName} onChange={setProductName} placeholder="Wireless Headphones" />
          <div style={row2}>
            <Field label="Original Price (€)" type="number" value={origPrice} onChange={setOrigPrice} placeholder="120" />
            <Field label="New Price (€)"      type="number" value={newPrice}  onChange={setNewPrice}  placeholder="89.99" />
          </div>
        </>
      )}

      {stimType === 'promo' && (
        <>
          <Field label="Promo Code" value={promoCode} onChange={setPromoCode} placeholder="SAVE20" />
          <div style={row2}>
            <Field label="Discount Value" type="number" value={discValue} onChange={setDiscValue} placeholder="20" />
            <div style={{ marginBottom: 14 }}>
              <span style={label}>Discount Type</span>
              <select
                style={input}
                value={discType}
                onChange={(e) => setDiscType(e.target.value as 'percent' | 'fixed')}
              >
                <option value="percent">Percent (%)</option>
                <option value="fixed">Fixed (€)</option>
              </select>
            </div>
          </div>
          <Field label="Expiry (days, optional)" type="number" value={expiryDays} onChange={setExpiryDays} placeholder="7" />
        </>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
        <button
          onClick={onCancel}
          style={{
            fontFamily: 'var(--fb)',
            fontSize: 11,
            letterSpacing: '1px',
            textTransform: 'uppercase',
            background: 'none',
            border: '1px solid rgba(0,51,102,0.2)',
            borderRadius: 6,
            padding: '8px 16px',
            cursor: 'pointer',
            color: 'var(--mid)',
          }}
        >
          Cancel
        </button>
        <button
          onClick={handleConfirm}
          disabled={!isValid()}
          style={{
            fontFamily: 'var(--fb)',
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '1.5px',
            textTransform: 'uppercase',
            backgroundColor: isValid() ? 'var(--gold)' : 'rgba(201,168,76,0.3)',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            padding: '8px 20px',
            cursor: isValid() ? 'pointer' : 'not-allowed',
            transition: 'background-color 0.15s',
          }}
        >
          Add Variant
        </button>
      </div>
    </div>
  )
}
