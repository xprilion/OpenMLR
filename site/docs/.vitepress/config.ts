import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'OpenMLR',
  description: 'ML Research Intern — Documentation',
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Setup', link: '/setup' },
      { text: 'GitHub', link: 'https://github.com/xprilion/OpenMLR' },
    ],
    sidebar: [
      {
        text: 'Getting Started',
        items: [
          { text: 'Overview', link: '/' },
          { text: 'Setup & Installation', link: '/setup' },
          { text: 'Configuration', link: '/configuration' },
        ],
      },
      {
        text: 'Usage',
        items: [
          { text: 'Modes (Plan / Research / Write)', link: '/modes' },
          { text: 'Agent Tools', link: '/tools' },
        ],
      },
      {
        text: 'Reference',
        items: [
          { text: 'Architecture', link: '/architecture' },
          { text: 'REST API', link: '/api' },
        ],
      },
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/xprilion/OpenMLR' },
    ],
    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024–present Anubhav Singh',
    },
  },
  overrides: [
    {
      // Light mode: warm blue-grey instead of pure white/black
      global: true,
      cssVariables: {
        ':root': {
          '--vp-c-bg': '#f8fafc',
          '--vp-c-bg-alt': '#f1f5f9',
          '--vp-c-bg-elv': '#ffffff',
          '--vp-c-bg-soft': '#f1f5f9',
          '--vp-c-text-1': '#1e293b',
          '--vp-c-text-2': '#475569',
          '--vp-c-text-3': '#64748b',
          '--vp-c-border': '#cbd5e1',
          '--vp-c-divider': '#e2e8f0',
          '--vp-c-gutter': '#e2e8f0',
        },
      },
    },
  ],
})
