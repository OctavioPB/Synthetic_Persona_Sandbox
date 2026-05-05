import React from 'react'

const footerStyle: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  padding: '20px 48px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  fontFamily: 'var(--fb)',
  fontSize: 9,
  letterSpacing: '3px',
  textTransform: 'uppercase',
  color: 'rgba(255,255,255,0.4)',
}

export default function Footer(): React.JSX.Element {
  const date = new Date()
    .toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
    .toUpperCase()

  return (
    <footer style={footerStyle}>
      <span>OPB · Octavio Pérez Bravo · Synthetic Persona Sandbox</span>
      <span>{date}</span>
    </footer>
  )
}
