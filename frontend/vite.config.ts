import path from "path"
// vitest/config re-exports Vite's own defineConfig, extended with a typed
// `test` key — same config object, just so `test` below isn't a type error.
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const BACKEND = 'http://localhost:5000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      '/api': BACKEND,
      '/auth': BACKEND,
      '/login': BACKEND,
      '/logout': BACKEND,
      '/static': BACKEND,
      '/robots.txt': BACKEND,
    },
  },
  test: {
    // Testing plain fetch-wrapping functions (features/*/api.ts), not
    // React components — the default node environment is enough, no
    // jsdom/testing-library needed for what's actually being tested.
    environment: "node",
    globals: false,
  },
})
