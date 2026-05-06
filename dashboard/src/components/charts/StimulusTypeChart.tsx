import React from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts'

export interface StimulusBarData {
  type: string
  avg_score: number
  count: number
}

interface Props {
  data: StimulusBarData[]
}

// BRAND.md data visualization color series
const COLORS = ['#003366', '#27B97C', '#7C4DBD']

function formatScore(v: number): string {
  return `${Math.round(v * 100)}%`
}

const tooltipStyle: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  border: '1px solid var(--primary-10)',
  borderRadius: 8,
  fontFamily: 'var(--fb)',
  fontSize: 12,
  color: 'var(--dark)',
  boxShadow: 'var(--shadow-soft)',
}

export default function StimulusTypeChart({ data }: Props): React.JSX.Element {
  if (data.every((d) => d.count === 0)) {
    return (
      <div style={{
        height: 200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--fb)',
        fontSize: 13,
        color: 'var(--mid)',
      }}>
        No data yet.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--primary-10)" vertical={false} />
        <XAxis
          dataKey="type"
          tick={{ fontFamily: 'var(--fb)', fontSize: 10, fill: 'var(--mid)' }}
          axisLine={{ stroke: 'var(--primary-10)' }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={formatScore}
          domain={[0, 1]}
          tick={{ fontFamily: 'var(--fb)', fontSize: 10, fill: 'var(--mid)' }}
          axisLine={false}
          tickLine={false}
          width={42}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(value: number, _name: string, props: { payload?: StimulusBarData }) => [
            `${formatScore(value)} (${props.payload?.count ?? 0} runs)`,
            'Avg Score',
          ]}
        />
        <Bar dataKey="avg_score" name="Avg Score" radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
