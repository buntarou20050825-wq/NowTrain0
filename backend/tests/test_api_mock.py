from fastapi.testclient import TestClient

from main import app  # main.pyでFastAPI appが定義されてる前提

client = TestClient(app)


def test_time_status_endpoint():
    r = client.get("/api/debug/time-status")
    # エンドポイントが存在しない場合 404 になる可能性があるため、
    # 既存のテスト意図に合わせて 200 チェックを行う
    # (コンテキスト: ユーザーは 200 を期待している)
    assert r.status_code == 200
