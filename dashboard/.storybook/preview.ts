import type { Preview } from '@storybook/react'
import '../src/styles/tokens.css'

const preview: Preview = {
  parameters: {
    backgrounds: {
      default: 'light',
      values: [
        { name: 'light', value: '#F4F6F9' },
        { name: 'dark',  value: '#0f1117' },
        { name: 'navy',  value: '#003366' },
      ],
    },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date:  /Date$/i,
      },
    },
  },
}

export default preview
