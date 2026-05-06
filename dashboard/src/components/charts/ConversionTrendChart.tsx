import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

export interface TrendDataPoint {
  date: string
  avg_score: number
  count: number
}

interface Props {
  data: TrendDataPoint[]
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
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

export default function ConversionTrendChart({ data }: Props): React.JSX.Element {
  if (data.length === 0) {
    return (
      <div style={{
        height: 240,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--fb)',
        fontSize: 13,
        color: 'var(--mid)',
      }}>
        No completed runs yet — launch a campaign to see trend data.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--primary-10)" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
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
          formatter={(value: number) => [formatScore(value), 'Avg Score']}
          labelFormatter={formatDate}
        />
        <Legend
          wrapperStyle={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}
        />
        <Line
          type="monotone"
          dataKey="avg_score"
          name="Avg Conversion Score"
          stroke="#003366"
          strokeWidth={2}
          dot={{ r: 3, fill: '#003366' }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
