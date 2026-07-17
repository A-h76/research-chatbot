import path from "path"
import { defineConfig } from 'vite'
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
})
