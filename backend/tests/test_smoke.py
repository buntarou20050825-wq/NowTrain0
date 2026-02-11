# backend/tests/test_smoke.py
"""
CI スモークテスト — テストが 0件で CI が失敗するのを防ぐ最小限のテスト。
外部依存なし、DB接続なし。
"""
import os

# CI 環境ではダミー環境変数を設定（.env が存在しないため）
os.environ.setdefault("ODPT_API_KEY", "ci_dummy_key")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_health_endpoint():
    """GET /api/health が 200 を返す"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_app_instance_exists():
    """FastAPI app インスタンスが正しく生成されている"""
    assert app is not None
    assert app.title is not None
