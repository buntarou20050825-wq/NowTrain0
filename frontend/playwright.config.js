/* eslint-env node */
// @ts-check

import process from "node:process";
import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E テスト設定
 *
 * CI では Vite preview server (port 4173) + FastAPI mock backend (port 8000) を
 * ワークフロー側で起動済みの前提。
 * ローカルでは webServer 設定でバックエンド・フロントエンドを自動起動。
 */
export default defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 1 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: process.env.CI ? 'list' : 'html',

    use: {
        baseURL: 'http://localhost:4173',
        // スクリーンショット & トレースは失敗時のみ
        screenshot: 'only-on-failure',
        trace: 'on-first-retry',
        // タイムアウト
        actionTimeout: 10_000,
    },

    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],

    // テスト結果の出力先
    outputDir: './test-results',
})
