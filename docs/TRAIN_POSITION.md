# 電車位置計算の仕様

このドキュメントでは、NowTrainの電車位置計算システムの詳細を説明します。

---

## 概要

NowTrainは、ODPT API（公共交通オープンデータ）から取得したGTFS-RT TripUpdateデータを基に、各列車の現在位置をリアルタイムで計算します。

### 計算フロー

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   ODPT API      │────▶│ gtfs_rt_tripupdate │────▶│ train_position_v4 │
│ (GTFS-RT Proto) │     │   (Protobuf解析)    │     │   (位置計算)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │ 座標補間        │
                                               │ (線路追従)      │
                                               └─────────────────┘
```

---

## 1. GTFS-RT データ取得

### 1.1 データソース

```python
# constants.py
ODPT_BASE_URL = "https://api-challenge.odpt.org/api/v4"
TRIP_UPDATE_URL = f"{ODPT_BASE_URL}/gtfs/realtime/jreast_odpt_train_trip_update"
```

ODPT APIから JR東日本の TripUpdate データを Protocol Buffers 形式で取得します。

### 1.2 TripUpdate の構造

```
FeedMessage
├── header
│   └── timestamp (フィード生成時刻)
└── entity[] (列車ごとのエンティティ)
    └── trip_update
        ├── trip
        │   ├── trip_id (例: "1001G")
        │   ├── route_id (例: "JR-East.Yamanote")
        │   └── start_date
        └── stop_time_update[] (駅ごとの時刻情報)
            ├── stop_sequence (停車順序)
            ├── stop_id (駅ID)
            ├── arrival
            │   ├── time (到着予定時刻: Unix秒)
            │   └── delay (遅延秒数)
            └── departure
                ├── time (発車予定時刻: Unix秒)
                └── delay (遅延秒数)
```

### 1.3 データモデル変換

取得したProtobufデータを、以下のデータクラスに変換します。

```python
@dataclass
class RealtimeStationSchedule:
    """1駅分のリアルタイム到着・発車時刻情報"""
    stop_sequence: int           # 停車順序 (1-based)
    station_id: Optional[str]    # 駅ID (例: "JR-East.Yamanote.Shinjuku")
    arrival_time: Optional[int]  # 到着時刻 (Unix秒)
    departure_time: Optional[int]# 発車時刻 (Unix秒)
    delay: int = 0               # 遅延秒数

@dataclass
class TrainSchedule:
    """1本の列車のリアルタイム時刻テーブル"""
    trip_id: str
    train_number: Optional[str]
    direction: Optional[str]      # "InnerLoop" / "OuterLoop" など
    feed_timestamp: Optional[int]
    schedules_by_seq: Dict[int, RealtimeStationSchedule]
    ordered_sequences: List[int]  # 停車順序のソート済みリスト
```

---

## 2. 列車位置計算 (train_position_v4.py)

### 2.1 計算アルゴリズム

列車の位置は以下の3状態に分類されます：

| 状態 | 説明 | progress値 |
|------|------|-----------|
| `stopped` | 駅に停車中 | 0.0 |
| `running` | 区間走行中 | 0.0〜1.0 |
| `unknown` | 運行時間外または計算不能 | None |

### 2.2 状態判定ロジック

```python
def compute_progress_for_train(schedule: TrainSchedule, now_ts: int):
    # 1. 停車判定
    for seq in ordered_sequences:
        station = schedules_by_seq[seq]
        if arrival_time <= now_ts <= departure_time:
            return SegmentProgress(status="stopped", progress=0.0)

    # 2. 走行区間判定
    for i in range(len(sequences) - 1):
        prev_station = schedules_by_seq[sequences[i]]
        next_station = schedules_by_seq[sequences[i + 1]]

        t0 = prev_station.departure_time  # 前駅発車
        t1 = next_station.arrival_time    # 次駅到着

        if t0 <= now_ts <= t1:
            elapsed = now_ts - t0
            duration = t1 - t0
            progress = calculate_physics_progress(elapsed, duration)
            return SegmentProgress(status="running", progress=progress)

    # 3. どの区間にも該当しない
    return SegmentProgress(status="unknown", progress=None)
```

### 2.3 駅停車時間（Dwell Time）の処理

GTFS-RTでは `arrival_time == departure_time` となることがあります。この場合、駅ランクに応じた停車時間を加算して実質的な発車時刻を計算します。

```python
# station_ranks.py

STATION_RANKS = {
    # Sランク: 巨大ターミナル (50秒)
    "JR-East.Yamanote.Shinjuku": 50,
    "JR-East.Yamanote.Tokyo": 50,
    "JR-East.Yamanote.Shibuya": 50,
    "JR-East.Yamanote.Ikebukuro": 50,

    # Aランク: 主要駅 (35秒)
    "JR-East.Yamanote.Shinagawa": 35,
    "JR-East.Yamanote.Ueno": 35,
    # ...

    # Bランク: 一般駅 (デフォルト20秒)
}

def get_station_dwell_time(station_id: str) -> int:
    return STATION_RANKS.get(station_id, 20)  # デフォルト20秒
```

---

## 3. 物理演算ベースの台形速度制御

### 3.1 E235系の性能パラメータ

山手線E235系の加減速特性をモデル化しています。

| パラメータ | 値 | 説明 |
|----------|-----|------|
| T_ACC | 30秒 | 加速時間 (0→90km/h) |
| T_DEC | 25秒 | 減速時間 (90km/h→0) |

### 3.2 速度プロファイル

```
速度
  ▲
  │      ┌──────────────────┐
  │     /                    \
  │    /                      \
  │   /                        \
  └──┴────────────────────────┴──▶ 時間
     加速(30s)    定速     減速(25s)
```

### 3.3 進捗率計算アルゴリズム

```python
def calculate_physics_progress(elapsed_time: float, total_duration: float) -> float:
    """
    台形速度制御に基づく進捗率(0.0-1.0)を計算
    """
    T_ACC = 30.0  # 加速時間
    T_DEC = 25.0  # 減速時間

    # 短区間の場合はスケール調整
    if total_duration < (T_ACC + T_DEC):
        factor = total_duration / (T_ACC + T_DEC)
        t_acc = T_ACC * factor
        t_dec = T_DEC * factor
    else:
        t_acc = T_ACC
        t_dec = T_DEC

    t_const = total_duration - t_acc - t_dec  # 定速区間の長さ

    # 速度ピーク値 (全行程で進捗率が1.0になるよう正規化)
    v_peak = 1.0 / (0.5 * t_acc + t_const + 0.5 * t_dec)

    if elapsed_time < t_acc:
        # 加速区間: 等加速度運動 (s = 0.5 * a * t^2)
        return 0.5 * (v_peak / t_acc) * (elapsed_time ** 2)

    elif elapsed_time < (t_acc + t_const):
        # 定速区間: 等速度運動
        dist_acc = 0.5 * v_peak * t_acc  # 加速区間で進んだ距離
        return dist_acc + v_peak * (elapsed_time - t_acc)

    else:
        # 減速区間: 等減速度運動 (残り時間から逆算)
        time_left = total_duration - elapsed_time
        return 1.0 - 0.5 * (v_peak / t_dec) * (time_left ** 2)
```

### 3.4 進捗率の変化

以下は、2分間（120秒）の区間での進捗率の変化例です。

| 経過時間 | 区間 | 進捗率 |
|---------|------|--------|
| 0秒 | 加速開始 | 0.0% |
| 15秒 | 加速中 | 4.7% |
| 30秒 | 加速完了 | 18.8% |
| 60秒 | 定速中 | 50.0% |
| 90秒 | 減速開始 | 81.3% |
| 105秒 | 減速中 | 95.3% |
| 120秒 | 減速完了 | 100.0% |

---

## 4. 線路追従座標計算

### 4.1 座標計算の概要

計算された進捗率を実際の地理座標に変換する際、直線補間ではなく線路形状に沿った補間を行います。

```
    前駅 ●─────────────────────● 次駅
         \                   /
          \    実際の線路   /
           ●──────────────●
```

### 4.2 座標計算フロー

```python
def calculate_coordinates(progress_data, cache, line_id):
    # 1. 停車中の場合: 駅座標をそのまま返す
    if status == "stopped":
        return get_station_coordinate(station_id)

    # 2. 走行中の場合: 線路スナップ
    if status == "running":
        # 2.1 線路点群を取得
        rail_coords = get_merged_coords(cache, line_id)

        # 2.2 前駅・次駅の最近傍点を探索
        prev_idx = find_nearest_point(rail_coords, prev_station)
        next_idx = find_nearest_point(rail_coords, next_station)

        # 2.3 パス切り出し
        path = rail_coords[prev_idx : next_idx + 1]

        # 2.4 パス長に基づく位置特定
        target_distance = total_path_length * progress
        position = interpolate_along_path(path, target_distance)

        return position
```

### 4.3 Haversine距離計算

地球上の2点間距離を計算する際は、Haversine公式を使用します。

```python
def get_distance_meters(lat1, lon1, lat2, lon2):
    """Haversine formula for great-circle distance"""
    R = 6371000  # 地球の半径 (メートル)

    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)

    a = sin(dphi/2)**2 + cos(phi1) * cos(phi2) * sin(dlambda/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c
```

### 4.4 方位角計算

列車アイコンの向きを決定するため、進行方向の方位角を計算します。

```python
def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    2点間の方位角（北=0度, 時計回り）
    """
    phi1, phi2 = radians(lat1), radians(lat2)
    dlambda = radians(lon2 - lon1)

    y = sin(dlambda) * cos(phi2)
    x = cos(phi1) * sin(phi2) - sin(phi1) * cos(phi2) * cos(dlambda)

    theta = atan2(y, x)
    bearing = (degrees(theta) + 360) % 360

    return bearing  # 0-360度
```

---

## 5. 出力データ構造

### 5.1 SegmentProgress

列車位置計算の出力は以下の構造です。

```python
@dataclass
class SegmentProgress:
    """列車の現在位置・進捗情報"""
    trip_id: str
    train_number: Optional[str]
    direction: Optional[str]

    # 現在区間
    prev_station_id: Optional[str]  # 前駅ID
    next_station_id: Optional[str]  # 次駅ID

    # 時刻情報
    now_ts: int                     # 現在時刻 (Unix秒)
    t0_departure: Optional[int]     # 前駅発車時刻
    t1_arrival: Optional[int]       # 次駅到着時刻

    # 進捗
    progress: Optional[float]       # 0.0〜1.0
    status: str                     # "running" / "stopped" / "unknown"

    # 付加情報
    delay: int = 0                  # 遅延秒数
    segment_count: int = 0          # 全区間数
```

### 5.2 API レスポンス例

```json
GET /api/trains/JR-East.Yamanote/positions/v4

{
  "line_id": "JR-East.Yamanote",
  "trains": [
    {
      "train_id": "1001G",
      "train_number": "1001G",
      "status": "running",
      "progress": 0.65,
      "latitude": 35.6812,
      "longitude": 139.7671,
      "bearing": 45.2,
      "prev_station": "JR-East.Yamanote.Tokyo",
      "next_station": "JR-East.Yamanote.Kanda",
      "delay": 120,
      "direction": "OuterLoop"
    }
  ],
  "timestamp": 1704067200,
  "feed_timestamp": 1704067195
}
```

---

## 6. クライアントサイド補間

### 6.1 60fps アニメーション

サーバーからのデータ更新間隔（約5秒）では滑らかな表示ができないため、クライアント側で補間を行います。

```javascript
// フロントエンドでの補間処理 (概念コード)
function interpolateTrainPosition(train, deltaTime) {
    if (train.status !== 'running') return train.position;

    // 前回位置から次の位置への補間
    const totalDuration = train.t1_arrival - train.t0_departure;
    const elapsed = (Date.now() / 1000) - train.t0_departure;
    const newProgress = calculatePhysicsProgress(elapsed, totalDuration);

    // 線形補間で座標を更新
    return {
        lat: prevLat + (nextLat - prevLat) * newProgress,
        lng: prevLng + (nextLng - prevLng) * newProgress
    };
}
```

### 6.2 更新サイクル

```
サーバー側 (5秒間隔)
────●────────────────●────────────────●────▶

クライアント側 (16ms間隔 ≈ 60fps)
────●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●──▶
```

---

## 7. 遅延情報の処理

### 7.1 遅延データの取得

GTFS-RT TripUpdate には各駅の遅延秒数が含まれています。

```protobuf
stop_time_update {
  arrival {
    time: 1704067200  // 予定時刻
    delay: 120        // 遅延秒数 (2分遅れ)
  }
}
```

### 7.2 遅延の表示

| 状態 | 取得する遅延値 |
|------|--------------|
| 停車中 | その駅の `delay` 値 |
| 走行中 | 次駅到着の `delay` 値 |

---

## 8. パフォーマンス最適化

### 8.1 キャッシュ戦略

```python
# 線路形状キャッシュ
_SHAPE_CACHE: Dict[str, List[tuple]] = {}

def get_merged_coords(cache, line_id):
    if line_id in _SHAPE_CACHE:
        return _SHAPE_CACHE[line_id]

    # 計算して保存
    coords = compute_merged_coords(cache, line_id)
    _SHAPE_CACHE[line_id] = coords
    return coords
```

### 8.2 計算量削減

- 線路座標のキャッシュにより、繰り返し計算を回避
- 最近傍探索は単純全探索（O(n)）だが、1路線あたり数百点程度なので問題なし

---

## 9. まとめ

### 計算フローの全体像

```
1. GTFS-RT TripUpdate取得 (5秒間隔)
           ↓
2. Protobuf解析 & TrainSchedule生成
           ↓
3. 状態判定 (stopped / running / unknown)
           ↓
4. 物理演算で進捗率計算 (台形速度制御)
           ↓
5. 線路追従座標補間
           ↓
6. API レスポンス生成
           ↓
7. クライアントサイド60fps補間
```

### 精度に影響する要素

| 要素 | 影響 | 対策 |
|------|------|------|
| GTFS-RTの更新遅延 | 数秒〜十数秒の誤差 | クライアント補間 |
| 駅停車時間の推定 | 停車判定のずれ | 駅ランク別の時間設定 |
| 線路形状データの精度 | 座標のずれ | Mini Tokyo 3D データ使用 |

---

## 関連ドキュメント

- [システムアーキテクチャ](ARCHITECTURE.md) - 全体設計とAPI仕様
- [README](../README.md) - プロジェクト概要とセットアップ
