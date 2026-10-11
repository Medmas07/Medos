import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, searchForWorkspaceRoot } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5175,
    // The linked design system serves its self-hosted font files from its own node_modules.
    fs: { allow: [searchForWorkspaceRoot(process.cwd()), '../../../design-system'] },
  },
  resolve: {
    dedupe: ['react', 'react-dom'],
  },
})
