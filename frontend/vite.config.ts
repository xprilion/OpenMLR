import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api/terminal': {
        target: process.env.VITE_API_URL || 'http://localhost:3000',
        ws: true,
      },
      '/api/events': {
        target: process.env.VITE_API_URL || 'http://localhost:3000',
        ws: true,
      },
      '/api': process.env.VITE_API_URL || 'http://localhost:3000',
      '/health': process.env.VITE_API_URL || 'http://localhost:3000',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/__tests__/**', 'src/types.ts', 'src/main.tsx'],
    },
  },
})
