# backend/geometry.py
from typing import Dict, List, Optional, Tuple


def build_all_railways_cache(coordinates: Dict) -> Dict[str, List[List[float]]]:
    """
    全路線の座標をキャッシュに格納（Base路線含む）
    type=subの参照解決に使用する。

    Returns:
        { "Base.TabataShinagawa": [[lon, lat], ...], "JR-East.Utsunomiya": [...], ... }
    """
    cache: Dict[str, List[List[float]]] = {}
    for railway in coordinates.get("railways", []):
        railway_id = railway.get("id", "")
        sublines = railway.get("sublines", [])

        # 全sublineの座標を結合
        all_coords: List[List[float]] = []
        for sub in sublines:
            coords = sub.get("coords", [])
            all_coords.extend(coords)

        if all_coords:
            cache[railway_id] = all_coords

    return cache


def resolve_subline_coords(subline: Dict, all_railways_cache: Dict[str, List[List[float]]]) -> List[List[float]]:
    """
    sublineの座標を解決する。
    - type=main: subline自身のcoordsを返す
    - type=sub: 参照先の路線の座標を返す（始点・終点で切り出し）

    Args:
        subline: coordinates.jsonのsublineオブジェクト
        all_railways_cache: 全路線の座標キャッシュ

    Returns:
        解決された座標リスト
    """
    subtype = subline.get("type", "main")
    coords = subline.get("coords", [])

    # mainタイプまたは十分な座標がある場合はそのまま返す
    if subtype == "main" or len(coords) > 10:
        return coords

    # subタイプ: 参照先の路線を取得
    start_ref = subline.get("start", {})
    end_ref = subline.get("end", {})
    ref_railway = start_ref.get("railway") or end_ref.get("railway")

    if not ref_railway or ref_railway not in all_railways_cache:
        # 参照先が見つからない場合は元の座標を返す
        return coords

    # 参照先の座標を取得
    ref_coords = all_railways_cache[ref_railway]

    if len(coords) < 2 or len(ref_coords) < 2:
        return coords

    # sublineの始点・終点に最も近い参照座標のインデックスを見つける
    start_point = coords[0]
    end_point = coords[-1]

    def find_nearest_idx(point, coord_list):
        min_dist = float("inf")
        min_idx = 0
        for i, c in enumerate(coord_list):
            dist = (c[0] - point[0]) ** 2 + (c[1] - point[1]) ** 2
            if dist < min_dist:
                min_dist = dist
                min_idx = i
        return min_idx

    start_idx = find_nearest_idx(start_point, ref_coords)
    end_idx = find_nearest_idx(end_point, ref_coords)

    # 範囲を切り出し
    if start_idx <= end_idx:
        return ref_coords[start_idx : end_idx + 1]
    else:
        # 逆方向の場合は反転
        return list(reversed(ref_coords[end_idx : start_idx + 1]))


def merge_sublines_v2(
    sublines: List[Dict], is_loop: bool = False, all_railways_cache: Optional[Dict[str, List[List[float]]]] = None
) -> List[List[float]]:
    """
    sublinesを正しい順序でマージし、連続した座標配列を返す。
    type=subのsublineは参照先の路線の座標を使用する。

    Args:
        sublines: coordinates.jsonのsublines配列
        is_loop: 環状路線かどうか
        all_railways_cache: 全路線の座標キャッシュ（参照解決用）

    Returns:
        マージされた座標のリスト [[lon, lat], ...]
    """
    if not sublines:
        return []

    if all_railways_cache is None:
        all_railways_cache = {}

    def coord_key(coord):
        """座標を丸めてハッシュ可能なキーに変換"""
        return (round(coord[0], 8), round(coord[1], 8))

    # 1. 各sublineの座標を解決（type=subなら参照先を使用）
    start_coords: Dict[tuple, List[int]] = {}  # coord_key -> [subline_index, ...]
    end_coords: Dict[tuple, List[int]] = {}  # coord_key -> [subline_index, ...]

    valid_sublines: List[Tuple[int, List[List[float]]]] = []
    for i, sub in enumerate(sublines):
        # 参照解決: type=subなら参照先の座標を使用
        coords = resolve_subline_coords(sub, all_railways_cache)
        if len(coords) >= 2:
            valid_sublines.append((i, coords))

            start_key = coord_key(coords[0])
            end_key = coord_key(coords[-1])

            start_coords.setdefault(start_key, []).append(i)
            end_coords.setdefault(end_key, []).append(i)

    if not valid_sublines:
        return []

    # 2. 接続グラフを構築（終点→始点）
    graph: Dict[int, List[int]] = {i: [] for i, _ in valid_sublines}
    in_degree: Dict[int, int] = {i: 0 for i, _ in valid_sublines}

    for i, coords in valid_sublines:
        end_key = coord_key(coords[-1])
        if end_key in start_coords:
            for j in start_coords[end_key]:
                if i != j:
                    graph[i].append(j)
                    in_degree[j] += 1

    # 3. 開始点を決定
    start_idx = None
    if is_loop:
        # 環状路線: 最初のsublineから開始
        start_idx = valid_sublines[0][0]
    else:
        # 非環状路線: 入次数0のsublineから開始
        for i, _ in valid_sublines:
            if in_degree[i] == 0:
                start_idx = i
                break
        if start_idx is None:
            start_idx = valid_sublines[0][0]

    # 4. DFSで順序を決定
    ordered_indices: List[int] = []
    visited: set = set()

    def dfs(idx: int):
        if idx in visited:
            return
        visited.add(idx)
        ordered_indices.append(idx)
        for next_idx in graph[idx]:
            if next_idx not in visited:
                dfs(next_idx)

    dfs(start_idx)

    # 未訪問のsublineも追加（孤立したセグメント対応）
    for i, _ in valid_sublines:
        if i not in visited:
            dfs(i)

    # 5. 座標をマージ（重複除去）
    merged_coords: List[List[float]] = []
    idx_to_coords = {i: coords for i, coords in valid_sublines}

    for i, idx in enumerate(ordered_indices):
        coords = idx_to_coords.get(idx, [])
        if not coords:
            continue

        if i == 0:
            merged_coords.extend(coords)
        else:
            # 重複座標の除去
            if merged_coords and coord_key(coords[0]) == coord_key(merged_coords[-1]):
                merged_coords.extend(coords[1:])
            else:
                merged_coords.extend(coords)

    return merged_coords


def merge_sublines_fallback(sublines: List[Dict]) -> List[List[float]]:
    """
    フォールバック: 距離ベースの貪欲アルゴリズムでsublineを接続する。
    グラフベースのマージが失敗した場合に使用。

    Args:
        sublines: coordinates.jsonのsublines配列

    Returns:
        マージされた座標のリスト [[lon, lat], ...]
    """
    if not sublines:
        return []

    def coord_key(coord):
        return (round(coord[0], 8), round(coord[1], 8))

    def dist_sq(c1, c2):
        return (c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2

    valid = [(i, sub.get("coords", [])) for i, sub in enumerate(sublines) if sub.get("coords")]
    if not valid:
        return []

    used = [False] * len(valid)
    result: List[List[float]] = []

    # 最初のsublineから開始
    used[0] = True
    coords = valid[0][1]
    result.extend(coords)
    current_end = coords[-1]

    for _ in range(len(valid) - 1):
        best_idx = -1
        best_dist = float("inf")
        best_reversed = False

        for i, (_, coords) in enumerate(valid):
            if used[i] or not coords:
                continue

            d_start = dist_sq(coords[0], current_end)
            if d_start < best_dist:
                best_dist = d_start
                best_idx = i
                best_reversed = False

            d_end = dist_sq(coords[-1], current_end)
            if d_end < best_dist:
                best_dist = d_end
                best_idx = i
                best_reversed = True

        if best_idx < 0:
            break

        used[best_idx] = True
        coords = valid[best_idx][1]
        if best_reversed:
            coords = list(reversed(coords))

        if result and coord_key(coords[0]) == coord_key(result[-1]):
            result.extend(coords[1:])
        else:
            result.extend(coords)

        current_end = result[-1]

    return result
