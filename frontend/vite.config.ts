import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
//
// Proxy target resolution:
//   - Local development (no Docker):  http://localhost:8000  (VITE_API_TARGET default)
//   - Inside Docker Compose:          http://backend:8000    (set via docker-compose.yml)
//
// VITE_API_TARGET is read at Node.js startup time (build/server start) via process.env,
// not at browser runtime, so it correctly picks up the Docker service name.
const apiTarget = process.env.VITE_API_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      // Proxy all /api requests to the backend.
      // Inside Docker: apiTarget = http://backend:8000 (resolved via Docker bridge network)
      // Local dev:     apiTarget = http://localhost:8000
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
