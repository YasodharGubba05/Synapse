import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = process.env.VITE_API_BASE || 'http://127.0.0.1:8001'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
})
