import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { getCursorCookie } from './vite/cursor-auth'

export default defineConfig({
  base: '/_ui/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/health': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
      '/proxy/claudegate': {
        target: 'http://localhost:9999',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/proxy\/claudegate/, ''),
      },
      '/proxy/mcp': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/proxy\/mcp/, '/mcp'),
      },
      '/proxy/cursor': {
        target: 'https://cursor.com',
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/proxy\/cursor/, ''),
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            const cookie = getCursorCookie()
            if (cookie) {
              proxyReq.setHeader('Cookie', cookie)
              proxyReq.setHeader('Accept', 'application/json')
              proxyReq.setHeader(
                'User-Agent',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36'
              )
            }
          })
        },
      },
    },
  },
})
