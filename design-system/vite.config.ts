import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Builds and serves the showcase page only. Portals consume src/ directly
// (see README.md); this package is never published or bundled as a library.
// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5179 },
  preview: { port: 5179 },
})
