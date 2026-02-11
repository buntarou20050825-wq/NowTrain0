// frontend/src/__tests__/App.test.jsx
// スモークテスト — App コンポーネントがクラッシュせずレンダリングされることを確認
import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../App'

describe('App', () => {
    it('クラッシュせずにレンダリングされる', () => {
        const { container } = render(<App />)
        expect(container).toBeTruthy()
    })

    it('ルート要素が存在する', () => {
        const { container } = render(<App />)
        // BrowserRouter 内に何らかの要素がレンダリングされていること
        expect(container.innerHTML.length).toBeGreaterThan(0)
    })
})
