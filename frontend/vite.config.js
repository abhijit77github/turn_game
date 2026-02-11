import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '192.168.0.6',
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://abhijit-app.ddns.net:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'http://abhijit-app.ddns.net:8000',
        ws: true,
        changeOrigin: true
      }
    },
    allowedHosts: ['127.0.0.1', 'abhijit-app.ddns.net']
  }
})
