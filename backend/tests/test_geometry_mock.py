import sys
import unittest
from pathlib import Path

# backendディレクトリをパスに追加して geometry.py をインポートできるようにする
sys.path.append(str(Path(__file__).resolve().parent.parent))

from geometry import merge_sublines_v2, resolve_subline_coords


class TestGeometryMerge(unittest.TestCase):
    def test_simple_merge(self):
        """単純な連結テスト"""
        print("\n--- Test: Simple Merge ---")
        sublines = [
            {"type": "main", "coords": [[139.0, 35.0], [139.1, 35.1]]},
            {"type": "main", "coords": [[139.1, 35.1], [139.2, 35.2]]},
        ]

        result = merge_sublines_v2(sublines)

        # 期待値: 3点 (重複する [139.1, 35.1] が1つにまとまる)
        expected = [[139.0, 35.0], [139.1, 35.1], [139.2, 35.2]]
        print("Input: 2 segments")
        print(f"Output: {len(result)} points")

        self.assertEqual(len(result), 3)
        self.assertEqual(result, expected)

    def test_gap_merge(self):
        """離れたセグメントのテスト（グラフ的に接続できない場合）"""
        print("\n--- Test: Gap Merge (Discontinuous) ---")
        sublines = [
            {"type": "main", "coords": [[139.0, 35.0], [139.1, 35.1]]},
            # ここで途切れている
            {"type": "main", "coords": [[140.0, 36.0], [140.1, 36.1]]},
        ]

        result = merge_sublines_v2(sublines)

        # 連続していないので、単に順番に結合されるはず（4点）
        print(f"Output: {len(result)} points")
        self.assertEqual(len(result), 4)

    def test_reference_resolution(self):
        """サブライン参照の解決テスト"""
        print("\n--- Test: Subline Reference ---")

        # 参照先の全路線キャッシュ
        all_railways_cache = {"Base.Line": [[139.0, 35.0], [139.1, 35.1], [139.2, 35.2], [139.3, 35.3]]}

        sublines = [
            # Base.Line の一部を参照 (35.1 -> 35.2)
            {
                "type": "sub",
                "coords": [[139.1, 35.1], [139.2, 35.2]],  # 注: start/end決定のためにのみ使用される
                "start": {"railway": "Base.Line"},
                "end": {"railway": "Base.Line"},
            }
        ]

        # geometry.py の resolve_subline_coords が正しく参照先から座標を引いてくるか
        resolved = resolve_subline_coords(sublines[0], all_railways_cache)

        # 期待値: Base.Line の中からマッチする部分 [139.1, 35.1]〜[139.2, 35.2] が返る
        # (mockデータでは座標が完全一致するように作っているが、実際は近傍探索が働く)
        print(f"Resolved points: {resolved}")
        self.assertEqual(len(resolved), 2)
        self.assertAlmostEqual(resolved[0][0], 139.1)


if __name__ == "__main__":
    unittest.main()
