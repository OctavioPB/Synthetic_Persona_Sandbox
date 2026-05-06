import type { Meta, StoryObj } from '@storybook/react'
import ConversionTrendChart from '../components/charts/ConversionTrendChart'

const meta: Meta<typeof ConversionTrendChart> = {
  title: 'Charts/ConversionTrendChart',
  component: ConversionTrendChart,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof ConversionTrendChart>

export const WithData: Story = {
  args: {
    data: [
      { date: '2026-04-28', avg_score: 0.42, count: 3 },
      { date: '2026-04-29', avg_score: 0.55, count: 5 },
      { date: '2026-04-30', avg_score: 0.61, count: 4 },
      { date: '2026-05-01', avg_score: 0.48, count: 6 },
      { date: '2026-05-02', avg_score: 0.70, count: 8 },
      { date: '2026-05-03', avg_score: 0.65, count: 7 },
      { date: '2026-05-04', avg_score: 0.73, count: 9 },
    ],
  },
}

export const Empty: Story = {
  args: { data: [] },
}
