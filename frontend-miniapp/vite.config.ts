import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { vanillaExtractPlugin } from '@vanilla-extract/vite-plugin'
import { fileURLToPath, URL } from 'node:url'
import path from 'path'

const apiUrl = process.env.VITE_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), vanillaExtractPlugin()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@navigator': path.resolve(__dirname, './src/content/navigator'),
    },
  },
  server: {
    port: 5174,
    proxy: {
      '/api': { target: apiUrl, changeOrigin: true },
    },
    allowedHosts: ['dev1.mfc-api.wish-edu.ru'],
  },
})
