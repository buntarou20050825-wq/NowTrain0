import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // ↓ 元々あったAPIの接続設定（これを消すとバックエンドと通信できなくなります）
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
    // ↓ 今回追加するngrok許可設定
    allowedHosts: true,
  },
})