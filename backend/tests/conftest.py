# backend/tests/conftest.py
"""
pytest 共通設定。
backend/ ディレクトリを sys.path に追加し、
各テストファイル内での sys.path.insert ハックを不要にする。
"""
import sys
from pathlib import Path

# backend/ をインポートパスに追加
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
