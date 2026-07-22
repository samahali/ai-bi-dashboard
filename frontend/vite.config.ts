import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),   // Tailwind v4 — replaces PostCSS plugin
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // recharts' own chunk (~565kB) is a single cohesive vendor library,
    // cached independently from the app bundle and only fetched on pages
    // that render a chart — raising the warning threshold past its size
    // avoids a permanent false-positive build warning for a chunk that's
    // already isolated as intended.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // recharts (and its d3 internals) is the single largest dependency
        // and is only needed on pages that render a chart — split it into
        // its own chunk so it's fetched in parallel / cached separately
        // from the main app bundle instead of inflating every page load.
        manualChunks: {
          recharts: ['recharts'],
        },
      },
    },
  },
})
