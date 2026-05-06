import React, { useEffect, useState } from 'react'

const MESSAGES = [
  'Consulting persona memory…',
  'Analysing stimulus context…',
  'Synthesising response…',
  'Scoring conversion intent…',
]

interface Props {
  variantName: string
}

export default function PersonaThinkingIndicator({ variantName }: Props): React.JSX.Element {
  const [phase, setPhase] = useState(0)
  const [msgIdx, setMsgIdx] = useState(0)

  useEffect(() => {
    const dotTimer = setInterval(() => setPhase((p) => (p + 1) % 3), 500)
    const msgTimer = setInterval(() => setMsgIdx((i) => (i + 1) % MESSAGES.length), 2000)
    return () => {
      clearInterval(dotTimer)
      clearInterval(msgTimer)
    }
  }, [])

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 14,
      padding: '28px 24px',
      background: 'linear-gradient(135deg, rgba(0,51,102,0.04), rgba(201,168,76,0.06))',
      borderRadius: 12,
      border: '1px solid rgba(201,168,76,0.22)',
      minHeight: 140,
      justifyContent: 'center',
    }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{
            width: 9,
            height: 9,
            borderRadius: '50%',
            backgroundColor: i === phase ? 'var(--gold)' : 'rgba(201,168,76,0.22)',
            transition: 'background-color 0.35s ease',
          }} />
        ))}
      </div>

      <p style={{
        fontFamily: "'Fraunces', Georgia, serif",
        fontSize: 13,
        fontWeight: 500,
        color: 'var(--primary)',
        margin: 0,
        textAlign: 'center',
      }}>
        {variantName}
      </p>

      <p style={{
        fontFamily: 'var(--fb)',
        fontSize: 11,
        color: 'rgba(0,51,102,0.5)',
        margin: 0,
        letterSpacing: '0.2px',
        textAlign: 'center',
      }}>
        {MESSAGES[msgIdx]}
      </p>
    </div>
  )
}
