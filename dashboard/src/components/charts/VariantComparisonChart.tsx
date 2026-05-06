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

export interface ComparisonItem {
  name: string
  score: number
}

interface Props {
  data: ComparisonItem[]
}

const COLORS = ['#003366', '#27B97C', '#7C4DBD', '#F07020', '#E05080']

function scoreColor(score: number): string {
  if (score >= 0.65) return '#22943a'
  if (score >= 0.40) return '#b07d10'
  return '#b03535'
}

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

export default function VariantComparisonChart({ data }: Props): React.JSX.Element {
  if (data.length === 0) {
    return (
      <div style={{
        height: 220,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--fb)',
        fontSize: 13,
        color: 'var(--mid)',
      }}>
        Select runs from the history table to compare.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 48, left: 4, bottom: 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--primary-10)" horizontal={false} />
        <XAxis
          type="number"
          domain={[0, 1]}
          tickFormatter={formatScore}
          tick={{ fontFamily: 'var(--fb)', fontSize: 10, fill: 'var(--mid)' }}
          axisLine={{ stroke: 'var(--primary-10)' }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={120}
          tick={{ fontFamily: 'var(--fb)', fontSize: 11, fill: 'var(--dark)' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(value: number) => [formatScore(value), 'Conversion Score']}
        />
        <Bar dataKey="score" name="Score" radius={[0, 4, 4, 0]}>
          {data.map((item, i) => (
            <Cell key={i} fill={scoreColor(item.score)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
