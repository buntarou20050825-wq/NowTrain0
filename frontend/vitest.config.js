/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    test: {
        // jsdom でブラウザ環境をシミュレート
        environment: 'jsdom',
        // テストファイルのパターン
        include: ['src/**/*.{test,spec}.{js,jsx,ts,tsx}'],
        // グローバルに使える API (describe, it, expect 等)
        globals: true,
        // CSS のインポートをモック
        css: false,
        // セットアップファイル
        setupFiles: ['./src/__tests__/setup.js'],
    },
})
