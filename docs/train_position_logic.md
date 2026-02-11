# 列車位置計算・遅延情報ロジック

## 概要

このドキュメントは、NowTrainアプリケーションの列車位置計算と遅延情報取得のロジックをまとめたものです。

---

## データソース

### 1. GTFS-RT (Google Transit Feed Specification - Realtime)

- **エンドポイント**: ODPT API経由で取得
- **提供データ**:
  - `TripUpdate`: 列車ごとの各駅到着・発車予定時刻
  - `stop_id`: 駅ID（数値形式、例: `"1101"`）
  - `delay`: 遅延秒数（多くの場合空または0）

### 2. ODPT Train API

- **エンドポイント**: `https://api.odpt.org/api/v4/odpt:Train`
- **提供データ**:
  - `odpt:delay`: 遅延秒数（信頼性が高い）
  - `odpt:fromStation`: 現在駅（例: `"odpt.Station:JR-East.ChuoRapid.Tokyo"`）
  - `odpt:toStation`: 次駅
  - `odpt:trainNumber`: 列車番号

### 3. GTFS Static (stops.txt)

- **ファイル**: `odpt/JR-East-Train-GTFS/stops.txt`
- **提供データ**:
  - `stop_id` → 座標（緯度・経度）のマッピング
  - GTFS-RTの数値形式stop_idに対応

---

## 駅ID形式

システム内で複数の駅ID形式が使用されている：

| 形式 | 例 | 使用箇所 |
|------|-----|---------|
| ODPT形式 | `odpt.Station:JR-East.ChuoRapid.Tokyo` | ODPT Train API |
| DB形式 | `JR-East.ChuoRapid.Tokyo` | データベース、coordinates.json |
| GTFS形式 | `1101` (数値) | GTFS-RT TripUpdate |

### 変換ロジック

```
ODPT形式 → DB形式:
  "odpt.Station:JR-East.ChuoRapid.Tokyo" → "JR-East.ChuoRapid.Tokyo"
  (プレフィックス "odpt.Station:" を除去)
```

---

## 位置計算フロー

### 全体フロー

```
1. GTFS-RT TripUpdate取得
   ↓
2. ODPT Train API取得（遅延情報）
   ↓
3. マッチング（trip_id → train_number）
   ↓
4. 進捗計算 (compute_progress_for_train)
   ↓
5. 座標計算 (calculate_coordinates)
   ↓
6. フロントエンドへ返却
```

### 進捗計算 (train_position_v4.py)

#### ステータス判定

| ステータス | 条件 | progress値 |
|-----------|------|-----------|
| `stopped` | 現在時刻が駅の到着〜発車の間 | 0.0 |
| `running` | 現在時刻が区間（発車〜到着）内 | 0.0〜1.0 |
| `unknown` | どの区間にも該当しない | None |
| `invalid` | 有効な区間データがない | None |

#### 物理演算ベースの進捗計算

E235系の性能に基づく台形速度制御を適用：

```python
T_ACC = 30.0  # 加速時間 (0→90km/h)
T_DEC = 25.0  # 減速時間 (90km/h→0)
```

- 加速区間: 2次関数で進捗増加
- 等速区間: 線形で進捗増加
- 減速区間: 2次関数で進捗減少

### 座標計算 (calculate_coordinates)

#### 1. 停車中 (stopped)

```python
station_id = prev_station_id or next_station_id
coord = get_station_coord(station_id)
return (lat, lon, bearing=0.0)
```

#### 2. 走行中 (running)

1. **線路スナップ方式**（優先）
   - coordinates.jsonから線路形状を取得
   - 前駅・次駅の最近傍点を探索
   - 進捗率に基づいて線路上の点を補間
   - 方位角(bearing)も計算

2. **直線補間方式**（フォールバック）
   - 前駅・次駅の座標を直線で結ぶ
   - 進捗率で補間

#### 3. 不明 (unknown)

```python
station_id = prev_station_id or next_station_id
coord = get_station_coord(station_id)
return (lat, lon)  # bearingなし
```

---

## 遅延情報

### 取得優先順位

1. **ODPT Train API** (`odpt_delay`) - 優先
2. **GTFS-RT TripUpdate** (`delay`) - フォールバック

### マッチングロジック

```python
# trip_id から train_number を抽出
# "1:4201300G" → "1300G"
# "42000906G" → "906G"

def extract_train_number_from_trip_id(trip_id):
    # OTPプレフィックス除去
    # 末尾3-4桁 + 英字サフィックスを抽出
    # 先頭ゼロを削除
```

### フロントエンド表示(未実装)

| 遅延時間 | 分類 | 色 |
|---------|------|-----|
| 0〜2分未満 | on-time | 緑 (#00B140) |
| 2〜5分未満 | moderate-delay | 黄 (#FFD700) |
| 5分以上 | severe-delay | 赤 (#FF4500) |

---

## 駅座標の取得

### 優先順位

1. **データベース** (`station_positions`)
   - キー: DB形式ID（例: `"JR-East.ChuoRapid.Tokyo"`）

2. **GTFS stops.txt** （フォールバック）
   - キー: 数値stop_id（例: `"1101"`）
   - data_cache.pyの`load_gtfs_stops()`で読み込み

### 変換処理

```python
def get_station_coord(station_id: str):
    # 1. DBから直接検索
    coord = station_positions.get(station_id)
    if coord:
        return coord

    # 2. 数値stop_idを抽出してGTFSから検索
    if "." in station_id:
        raw_stop_id = station_id.split(".")[-1]
        if raw_stop_id.isdigit():
            return gtfs_stop_coords.get(raw_stop_id)

    return None
```

---

## 既知の問題と対策

### 問題1: マーカーが表示されない

**原因**: GTFS-RTの`stop_id`が数値形式だが、座標検索がDB形式IDを期待

**解決策**: GTFS stops.txtを読み込み、数値stop_idでの座標検索にフォールバック

### 問題2: 「運行中」表示なのにマーカーが表示されない

**原因**:
- GTFS-RTで`stop_id`がnullの場合
- 駅座標が取得できない場合

**潜在的解決策**:
- ODPT Train APIの`from_station`/`to_station`を使用（未実装）

### 問題3: 遅延情報が表示されない

**原因**: GTFS-RTの`delay`フィールドが多くの場合空

**解決策**: ODPT Train APIから遅延情報を取得し、GTFS-RTデータに統合

---

## ファイル構成

| ファイル | 役割 |
|---------|------|
| `gtfs_rt_tripupdate.py` | GTFS-RT TripUpdate取得・正規化 |
| `train_position_v4.py` | 進捗計算・座標計算 |
| `odpt_train_api.py` | ODPT Train API取得 |
| `data_cache.py` | 静的データ管理、座標取得 |
| `main.py` | APIエンドポイント、データ統合 |

---

## データ構造

### TrainSchedule

```python
@dataclass
class TrainSchedule:
    trip_id: str
    train_number: Optional[str]
    start_date: Optional[str]
    direction: Optional[str]
    feed_timestamp: Optional[int]
    schedules_by_seq: Dict[int, RealtimeStationSchedule]
    ordered_sequences: List[int]
    odpt_delay: int = 0  # ODPT遅延秒数
```

### SegmentProgress

```python
@dataclass
class SegmentProgress:
    trip_id: str
    train_number: Optional[str]
    direction: Optional[str]
    prev_station_id: Optional[str]
    next_station_id: Optional[str]
    prev_seq: Optional[int]
    next_seq: Optional[int]
    now_ts: int
    t0_departure: Optional[int]
    t1_arrival: Optional[int]
    progress: Optional[float]  # 0.0〜1.0
    status: str  # "running" / "stopped" / "unknown" / "invalid"
    feed_timestamp: Optional[int]
    segment_count: int
    delay: int  # 遅延秒数
```

---

## API レスポンス例

```json
{
  "trains": [
    {
      "trip_id": "4201300G",
      "train_number": "1300G",
      "direction": "InnerLoop",
      "status": "running",
      "progress": 0.45,
      "location": {
        "latitude": 35.6812,
        "longitude": 139.7671
      },
      "bearing": 180.5,
      "prev_station": "JR-East.Yamanote.Tokyo",
      "next_station": "JR-East.Yamanote.Yurakucho",
      "delay": 120,
      "delay_status": "moderate-delay"
    }
  ],
  "timestamp": 1707638400
}
```
