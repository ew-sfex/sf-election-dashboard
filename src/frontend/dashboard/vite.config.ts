import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/sf-election-dashboard/' : '/',
  plugins: [react()],
  server: {
    proxy: {
      '/api/sf-live.xml': {
        target: 'https://sfelections.org',
        changeOrigin: true,
        rewrite: () => '/results/20261103/data/summary.xml',
        headers: {
          'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
          Accept: 'application/xml,text/xml,*/*;q=0.8',
        },
      },
    },
  },
}))
