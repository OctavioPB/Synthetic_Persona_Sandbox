import type { Preview } from '@storybook/react'
import '../src/styles/tokens.css'

const preview: Preview = {
  parameters: {
    backgrounds: {
      options: {
        light: { name: 'light', value: '#F4F6F9' },
        dark: { name: 'dark',  value: '#0f1117' },
        navy: { name: 'navy',  value: '#003366' }
      }
    },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date:  /Date$/i,
      },
    },
  },

  initialGlobals: {
    backgrounds: {
      value: 'light'
    }
  }
}

export default preview
