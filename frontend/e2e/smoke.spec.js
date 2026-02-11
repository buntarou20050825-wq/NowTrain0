// frontend/e2e/smoke.spec.js
// E2E スモークテスト — ページの基本的な読み込みを検証
// バックエンドはモックモード (VIRTUAL_TIME) で起動されている前提
import { test, expect } from '@playwright/test'

test.describe('NowTrain E2E Smoke', () => {
    test('ページが正常にロードされる', async ({ page }) => {
        const response = await page.goto('/')
        // HTTP 200 であること
        expect(response?.status()).toBe(200)
    })

    test('タイトルが設定されている', async ({ page }) => {
        await page.goto('/')
        // <title> タグが空でないこと
        const title = await page.title()
        expect(title.length).toBeGreaterThan(0)
    })

    test('root 要素が存在する', async ({ page }) => {
        await page.goto('/')
        // React がマウントされる #root が存在すること
        const root = page.locator('#root')
        await expect(root).toBeAttached()
    })

    test('API ヘルスチェックが応答する', async ({ request }) => {
        // バックエンドの /api/health を直接呼び出し
        const res = await request.get('http://localhost:8000/api/health')
        expect(res.ok()).toBeTruthy()
        const body = await res.json()
        expect(body.status).toBe('ok')
    })
})
