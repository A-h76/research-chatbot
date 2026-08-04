import path from "path"
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const BACKEND = 'http://localhost:5000'
const REPO_DOCS = path.resolve(__dirname, "../docs")

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@repo-docs": REPO_DOCS,
    },
  },
  build: {
    manifest: true,
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, "index.html"),
        ecosystem: path.resolve(__dirname, "ecosystem.html"),
      },
    },
  },
  server: {
    fs: {
      // Allow importing living contracts / ADRs as ?raw for Docs (Mintlify layout).
      allow: [path.resolve(__dirname, "..")],
    },
    proxy: {
      '/api': BACKEND,
      '/auth': BACKEND,
      '/login': BACKEND,
      '/logout': BACKEND,
      '/static': BACKEND,
      '/robots.txt': BACKEND,
      '/product': BACKEND,
      '/how-it-works': BACKEND,
      '/research': BACKEND,
      '/early-access': BACKEND,
      '/pricing': BACKEND,
    },
  },
  test: {
    environment: "node",
    globals: false,
  },
})
