# NowTrain 電車位置計算システム 技術レポート

## 概要

NowTrainは、GTFS-RTリアルタイムデータと物理演算を組み合わせて電車の現在位置を計算するシステムです。

---

## 1. データソース

### 1.1 ODPT API（公共交通オープンデータ）

```
取得URL: https://api-challenge.odpt.org/api/v4/gtfs/realtime/...
形式: Protocol Buffers (Protobuf)
更新頻度: 約20秒ごと
```

**取得データ:**
- **TripUpdate**: 各列車の駅到着・発車時刻
  - `arrival.time`: 予測到着時刻（**遅延が既に反映されている**）
  - `departure.time`: 予測発車時刻（**遅延が既に反映されている**）
  - `delay`: 定刻比の遅延秒数（表示用の参考情報）

### 1.2 静的データ（Mini Tokyo 3D形式）

| ファイル | 内容 |
|---------|------|
| `railways.json` | 路線定義（51路線、駅リスト、方向名） |
| `coordinates.json` | 線路の座標データ（緯度・経度の配列） |
| `stations.json` | 駅マスタ（座標、名称） |
| `train-timetables/*.json` | 時刻表データ（18路線分） |

---

## 2. 処理フロー

```
┌─────────────────────────────────────┐
│ ODPT API (GTFS-RT TripUpdate)       │
│ • 各列車の駅到着・発車時刻          │
│ • 遅延情報                          │
└────────────┬────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────┐
│ Step 1: TripUpdate取得・正規化                    │
│ (gtfs_rt_tripupdate.py)                          │
│                                                  │
│ • Protobuf解析                                   │
│ • 駅ID解決（3段階優先度）                        │
│ • TrainSchedule構造体に変換                      │
└────────────┬───────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────┐
│ Step 2: 現在区間・進捗率の計算                    │
│ (train_position_v4.py)                           │
│                                                  │
│ • 現在時刻と駅時刻を比較                         │
│ • 停車中 or 走行中を判定                         │
│ • 走行中なら物理演算で進捗率を計算               │
└────────────┬───────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────┐
│ Step 3: 座標計算（線路形状追従）                  │
│ (train_position_v4.py)                           │
│                                                  │
│ • 線路座標から駅間パスを抽出                     │
│ • 進捗率 × 駅間距離 = 現在位置                   │
│ • 方位角も計算                                   │
└────────────┬───────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ フロントエンド（地図表示）       │
│ • 列車マーカーを描画            │
│ • 60fps補間でスムーズに移動     │
└─────────────────────────────────┘
```

---

## 3. 位置計算アルゴリズム

### 3.1 状態判定

各列車について、現在時刻 `now` と駅時刻を比較:

```python
# 停車中判定
if arrival_time <= now <= departure_time:
    status = "stopped"
    progress = 0.0

# 走行中判定
elif prev_departure <= now <= next_arrival:
    status = "running"
    progress = calculate_physics_progress(elapsed, duration)
```

### 3.2 遅延情報の扱い

GTFS-RT仕様では、時刻データは以下の構造:

| フィールド | 内容 | 用途 |
|-----------|------|------|
| `arrival.time` | 予測到着時刻（遅延込み） | 位置計算に使用 |
| `departure.time` | 予測発車時刻（遅延込み） | 位置計算に使用 |
| `delay` | 定刻比の遅延秒数 | 表示用（+N分遅れ） |

**重要:** `arrival.time` には既に遅延が反映されているため、位置計算で `delay` を別途加算する必要はない。

```
例: 本来10:30着の電車が2分遅れている場合
- arrival.time = 10:32（予測時刻）
- delay = 120秒（参考情報）
→ 位置計算は10:32を基準に行われる（正しい）
```

### 3.3 物理演算（台形速度制御）

E235系山手線の実車性能に基づく加減速モデル:

```
速度
 ↑
 │    ┌────────────┐
 │   /              \
 │  /                \
 │ /                  \
 └─┴──────────────────┴─→ 時間
   加速    定速    減速
   30秒           25秒
```

**計算式:**

```python
T_ACC = 30.0  # 加速時間（秒）
T_DEC = 25.0  # 減速時間（秒）

# 加速フェーズ（0 ≤ t < T_ACC）
progress = 0.5 * (v_peak / T_ACC) * t²

# 定速フェーズ（T_ACC ≤ t < T_ACC + T_CONST）
progress = dist_acc + v_peak * (t - T_ACC)

# 減速フェーズ（残り時間 time_left）
progress = 1.0 - 0.5 * (v_peak / T_DEC) * time_left²
```

**効果:**
- 直線補間より自然な動き
- 駅発車時はゆっくり、中間で最速、駅到着時はゆっくり

### 3.4 線路形状への追従

単純な2点間補間ではなく、実際の線路形状に沿って座標を計算:

```python
# 1. 線路座標データを取得（coordinates.json）
coords = get_merged_coords(cache, "JR-East.Yamanote")
# → 838点の座標配列

# 2. 前駅・次駅に最も近い線路座標を探索
idx_prev = find_nearest_point(coords, prev_station)
idx_next = find_nearest_point(coords, next_station)

# 3. 駅間のパスを抽出
path = coords[idx_prev : idx_next + 1]

# 4. パス上で進捗率に対応する位置を計算
total_distance = sum(segment_distances)
target_distance = total_distance * progress

# 5. 区間内補間で最終座標を決定
(latitude, longitude, bearing) = interpolate_on_path(path, target_distance)
```

---

## 4. 駅ID解決の仕組み

GTFS-RTの `stop_id` を内部形式に変換する3段階ロジック:

| 優先度 | 方法 | 例 |
|--------|------|-----|
| 1 | `JR-East.` プレフィックス付きならそのまま使用 | `JR-East.Yamanote.Tokyo` |
| 2 | 静的時刻表の `seq_to_station` マップで変換 | `stop_seq=5` → `JR-East.Yamanote.Shinagawa` |
| 3 | `mt3d_prefix` を付与して変換 | `Tokyo` → `JR-East.ChuoRapid.Tokyo` |

---

## 5. 主要ファイル

| ファイル | 役割 |
|---------|------|
| `gtfs_rt_tripupdate.py` | GTFS-RT取得、駅ID解決、TrainSchedule構築 |
| `train_position_v4.py` | 進捗計算、物理演算、座標計算 |
| `gtfs_rt_vehicle.py` | trip_id解析、方向判定、路線推定 |
| `data_cache.py` | 静的データ読み込み、キャッシュ管理 |
| `config.py` | 51路線の定義 |

---

## 6. 主要データ構造

### TrainSchedule（1列車の時刻情報）

```python
@dataclass
class TrainSchedule:
    trip_id: str              # "4201301G"
    train_number: str         # "301G"
    direction: str            # "OuterLoop" / "InnerLoop"
    feed_timestamp: int       # APIレスポンス時刻
    schedules_by_seq: Dict[int, RealtimeStationSchedule]
    ordered_sequences: List[int]
```

### SegmentProgress（位置計算結果）

```python
@dataclass
class SegmentProgress:
    trip_id: str
    train_number: str
    direction: str
    status: str               # "running" / "stopped" / "unknown"
    progress: float           # 0.0 〜 1.0
    prev_station_id: str      # 前駅ID
    next_station_id: str      # 次駅ID
    delay: int                # 遅延秒数
    t0_departure: int         # 前駅発車時刻
    t1_arrival: int           # 次駅到着時刻
```

---

## 7. 対応路線

51路線に対応（`config.py` で定義）:

- 山手線、京浜東北線、中央線快速、総武線各駅停車
- 東海道線、横須賀線、湘南新宿ライン
- 宇都宮線、高崎線、常磐線
- 埼京線、武蔵野線、南武線、横浜線
- その他支線・貨物線を含む全51路線

---

## 8. パフォーマンス最適化

| 最適化 | 内容 |
|--------|------|
| 線路座標キャッシュ | `_SHAPE_CACHE` でsubline統合結果を保持 |
| 駅座標キャッシュ | `station_positions` をメモリに保持 |
| 駅ランクキャッシュ | DB読み込みは起動時1回のみ |
| 時刻表インデックス | 列車番号→時刻表の高速検索 |

---

## 9. エラーハンドリング

```python
# 線路スナップ失敗時
try:
    coords = get_merged_coords(cache, line_id)
    # 線路追従で座標計算
except:
    # フォールバック: 2点間の直線補間
    return linear_interpolation(prev_coord, next_coord, progress)
```

---

## 10. API レスポンス例

`GET /api/trains/yamanote/positions/v4`

```json
{
  "source": "tripupdate_v4",
  "status": "success",
  "timestamp": 1760072237,
  "total_trains": 52,
  "positions": [
    {
      "trip_id": "4201301G",
      "train_number": "301G",
      "direction": "OuterLoop",
      "status": "running",
      "progress": 0.4523,
      "delay": 120,
      "location": {
        "latitude": 35.628471,
        "longitude": 139.738521,
        "bearing": 45.2
      },
      "segment": {
        "prev_station_id": "JR-East.Yamanote.Shinagawa",
        "next_station_id": "JR-East.Yamanote.Tamachi"
      },
      "times": {
        "now_ts": 1760072237,
        "t0_departure": 1760072100,
        "t1_arrival": 1760072280
      }
    }
  ]
}
```

---

## まとめ

NowTrainの電車位置計算システムは:

1. **GTFS-RTリアルタイムデータ**から各列車の駅時刻を取得
2. **現在時刻との比較**で停車中/走行中を判定
3. **物理演算（台形速度制御）**で自然な進捗率を計算
4. **線路形状データ**に沿って正確な座標を算出
5. **60fps補間**でフロントエンドがスムーズにアニメーション

これにより、20秒間隔のAPIデータから滑らかな電車移動を実現しています。
