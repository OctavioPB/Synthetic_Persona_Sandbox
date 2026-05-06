import type { Meta, StoryObj } from '@storybook/react'
import Eyebrow from '../components/Eyebrow'

const meta: Meta<typeof Eyebrow> = {
  title: 'Brand/Eyebrow',
  component: Eyebrow,
  parameters: { layout: 'padded' },
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof Eyebrow>

export const Default: Story = {
  args: { children: 'Section Label', light: false },
}

export const LightVariant: Story = {
  args: { children: 'Hero Label', light: true },
  parameters: { backgrounds: { default: 'navy' } },
}
