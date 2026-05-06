import type { Meta, StoryObj } from '@storybook/react'
import PersonaThinkingIndicator from '../components/PersonaThinkingIndicator'

const meta: Meta<typeof PersonaThinkingIndicator> = {
  title: 'Simulation/PersonaThinkingIndicator',
  component: PersonaThinkingIndicator,
  parameters: { layout: 'centered' },
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof PersonaThinkingIndicator>

export const Default: Story = {
  args: { variantName: 'Summer Hero Banner' },
}

export const LongName: Story = {
  args: { variantName: 'Price Drop — Wireless Headphones 25% Off' },
}
