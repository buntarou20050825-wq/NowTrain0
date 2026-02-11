# NowTrain システムアーキテクチャ

## 概要

NowTrainは、JR東日本の電車をリアルタイムで追跡し、経路検索・ナビゲーションを行うWebアプリケーションです。

---

## システム構成図

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Client (Browser)                                 │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    React Application (Vite)                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │ │
│  │  │ SearchScreen │→ │ResultsScreen │→ │  NavigationScreen      │   │ │
│  │  │              │  │              │  │  ┌─────────────────┐   │   │ │
│  │  │ - 駅入力     │  │ - 経路一覧   │  │  │    MapView      │   │   │ │
│  │  │ - 日時選択   │  │ - 詳細展開   │  │  │ (Mapbox GL JS)  │   │   │ │
│  │  │ - 検索実行   │  │ - ナビ開始   │  │  └─────────────────┘   │   │ │
│  │  └──────────────┘  └──────────────┘  │  ┌─────────────────┐   │   │ │
│  │                                       │  │  BottomSheet    │   │   │ │
│  │                                       │  │ (経路詳細)      │   │   │ │
│  │                                       │  └─────────────────┘   │   │ │
│  │                                       └────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                              HTTP / Fetch API
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                                 │
│                        localhost:8000                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                        API Layer (main.py)                        │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│   │
│  │  │/api/stations│ │/api/route   │ │/api/trains  │ │/api/shapes  ││   │
│  │  │  /search    │ │  /search    │ │ /{id}/v4    │ │             ││   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘│   │
│  └─────────┼───────────────┼───────────────┼───────────────┼────────┘   │
│            │               │               │               │            │
│            ▼               ▼               ▼               ▼            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │  DataCache   │ │  OTP Client  │ │train_position│ │  DataCache   │   │
│  │  (JSON/DB)   │ │  (GraphQL)   │ │    _v4.py    │ │ coordinates  │   │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────────────┘   │
│         │                │                │                             │
│         ▼                ▼                ▼                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                    │
│  │   SQLite     │ │     OTP      │ │  GTFS-RT     │                    │
│  │ nowtrain.db  │ │ Docker:8080  │ │  Parser      │                    │
│  └──────────────┘ └──────────────┘ └──────┬───────┘                    │
└─────────────────────────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │    ODPT API      │
                                    │  (GTFS-RT Feed)  │
                                    │ api.odpt.org     │
                                    └──────────────────┘
```

---

## フロントエンドアーキテクチャ

### 技術スタック

| 技術 | バージョン | 用途 |
|------|-----------|------|
| React | 19.x | UIフレームワーク |
| Vite | 7.x | ビルドツール・開発サーバー |
| Mapbox GL JS | 3.16+ | 地図表示・レンダリング |
| React Router | 6.x | ルーティング |

### コンポーネント構成

```
App.jsx
├── MainApp.jsx (3フェーズUIコントローラー)
│   ├── SearchScreen.jsx (Phase 1: 検索)
│   ├── ResultsScreen.jsx (Phase 2: 結果)
│   └── NavigationScreen.jsx (Phase 3: ナビ)
│       └── MapView.jsx (Mapbox統合)
├── MapView.jsx (スタンドアローン地図)
└── AdminPanel.jsx (管理画面)
```

### 状態管理

Props Drilling + React Hooks (Redux/Context不使用)

```javascript
// MainApp.jsx
const [phase, setPhase] = useState("search");      // 現在のフェーズ
const [searchResults, setSearchResults] = useState(null);
const [searchParams, setSearchParams] = useState(null);
const [selectedItinerary, setSelectedItinerary] = useState(null);
```

### 3フェーズUIフロー

```
Phase 1 (search)       Phase 2 (results)       Phase 3 (navigation)
┌──────────────┐      ┌──────────────┐       ┌──────────────────────┐
│ SearchScreen │ ──→  │ResultsScreen │  ──→  │  NavigationScreen    │
│              │      │              │       │  ┌────────────────┐  │
│ - 出発駅     │      │ - 経路一覧   │       │  │    MapView     │  │
│ - 到着駅     │      │ - タイムライン│       │  │  + My Train    │  │
│ - 日時       │      │ - ナビ開始   │       │  └────────────────┘  │
└──────────────┘      └──────────────┘       │  ┌────────────────┐  │
                                             │  │  BottomSheet   │  │
                                             │  │  (運行状況)    │  │
                                             │  └────────────────┘  │
                                             └──────────────────────┘
```

### MapView 主要機能

| 機能 | 実装 |
|------|------|
| 路線表示 | GeoJSON LineString レイヤー |
| 駅表示 | GeoJSON Point レイヤー (白丸) |
| 電車表示 | Symbol レイヤー (矢印アイコン) |
| My Train | HTML Marker (赤色、追跡中) |
| 経路ハイライト | 3セグメント描画 (乗車前/乗車中/乗車後) |
| アニメーション | requestAnimationFrame (60fps) |

---

## バックエンドアーキテクチャ

### 技術スタック

| 技術 | バージョン | 用途 |
|------|-----------|------|
| Python | 3.10+ | 言語 |
| FastAPI | 0.104+ | Webフレームワーク |
| Uvicorn | 0.24+ | ASGIサーバー |
| SQLAlchemy | 2.0+ | ORM |
| SQLite | - | データベース |
| httpx | 0.25+ | 非同期HTTP |
| gtfs-realtime-bindings | 1.0+ | Protobuf解析 |

### モジュール構成

```
backend/
├── main.py                  # FastAPI アプリ (APIエンドポイント)
├── config.py                # 路線設定 (51路線定義)
├── constants.py             # 定数 (ODPT API URL等)
│
├── data_cache.py            # データキャッシュ (JSON/DB)
├── database.py              # SQLAlchemy定義
│
├── gtfs_rt_tripupdate.py    # GTFS-RT TripUpdate解析
├── gtfs_rt_vehicle.py       # GTFS-RT VehiclePosition解析
├── train_position_v4.py     # 電車位置計算 (物理演算)
├── train_state.py           # 列車状態計算
│
├── otp_client.py            # OTP GraphQLクライアント
├── station_ranks.py         # 駅ランク定義
└── timetable_models.py      # 時刻表データモデル
```

### データフロー

```
1. 起動時
   ┌─────────────────────────────────────────────────────────────┐
   │ data_cache.load_all()                                       │
   │  ├─ railways.json → self.railways                           │
   │  ├─ stations.json → self.stations, self.station_positions   │
   │  ├─ coordinates.json → self.coordinates                     │
   │  └─ nowtrain.db → self.station_rank_cache                   │
   └─────────────────────────────────────────────────────────────┘

2. 電車位置取得 (/api/trains/{line_id}/positions/v4)
   ┌─────────────────────────────────────────────────────────────┐
   │ ODPT API (TripUpdate Protobuf)                              │
   │          ↓                                                  │
   │ gtfs_rt_tripupdate.fetch_trip_updates()                     │
   │          ↓                                                  │
   │ TrainSchedule (各列車の予測発着時刻)                        │
   │          ↓                                                  │
   │ train_position_v4.compute_all_progress()                    │
   │          ↓                                                  │
   │ SegmentProgress (区間・進捗率・遅延)                        │
   │          ↓                                                  │
   │ calculate_coordinates() (座標計算)                          │
   │          ↓                                                  │
   │ JSON Response (position, delay, status)                     │
   └─────────────────────────────────────────────────────────────┘

3. 経路検索 (/api/route/search)
   ┌─────────────────────────────────────────────────────────────┐
   │ 駅名 → 座標変換 (stations.json)                             │
   │          ↓                                                  │
   │ OTP GraphQL API (localhost:8080)                            │
   │          ↓                                                  │
   │ itineraries (legs, trip_id, times)                          │
   │          ↓                                                  │
   │ JSON Response                                               │
   └─────────────────────────────────────────────────────────────┘
```

---

## API仕様

### 駅検索 API

```
GET /api/stations/search?q={query}&limit={n}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|-----|------|
| q | string | Yes | 検索クエリ (日本語/英語) |
| limit | int | No | 最大件数 (デフォルト: 10) |

**レスポンス例:**
```json
{
  "stations": [
    {
      "id": "JR-East.Yamanote.Tokyo",
      "name_ja": "東京",
      "name_en": "Tokyo",
      "coord": { "lon": 139.7671, "lat": 35.6812 },
      "lines": ["山手線", "中央線", "京浜東北線"]
    }
  ]
}
```

### 経路検索 API

```
GET /api/route/search?from_station={}&to_station={}&date={}&time={}&arrive_by={}
```

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|-----|------|
| from_station | string | Yes | 出発駅名 |
| to_station | string | Yes | 到着駅名 |
| date | string | No | 日付 (YYYY-MM-DD) |
| time | string | No | 時刻 (HH:MM) |
| arrive_by | bool | No | 到着時刻指定 |

**レスポンス例:**
```json
{
  "status": "success",
  "itineraries": [
    {
      "start_time": "2025-01-20T08:00:00+09:00",
      "end_time": "2025-01-20T08:30:00+09:00",
      "duration_minutes": 30,
      "legs": [
        {
          "mode": "RAIL",
          "from": { "name": "東京" },
          "to": { "name": "渋谷" },
          "route": {
            "short_name": "山手線",
            "color": "80C342"
          },
          "trip_id": "1:4211004G"
        }
      ]
    }
  ]
}
```

### 電車位置 API

```
GET /api/trains/{line_id}/positions/v4
```

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| line_id | string | 路線ID (例: yamanote, chuo_rapid) |

**レスポンス例:**
```json
{
  "source": "tripupdate_v4",
  "status": "success",
  "total_trains": 26,
  "positions": [
    {
      "trip_id": "4211004G",
      "train_number": "1004G",
      "direction": "InnerLoop",
      "status": "running",
      "progress": 0.67,
      "delay": 0,
      "location": {
        "latitude": 35.628541,
        "longitude": 139.720505,
        "bearing": 180.5
      },
      "segment": {
        "prev_station_id": "JR-East.Yamanote.Meguro",
        "next_station_id": "JR-East.Yamanote.Gotanda"
      }
    }
  ]
}
```

### 路線形状 API

```
GET /api/shapes?lineId={id}
```

**レスポンス:** GeoJSON FeatureCollection (LineString)

### 駅一覧 API

```
GET /api/stations?lineId={id}
```

**レスポンス例:**
```json
{
  "stations": [
    {
      "id": "JR-East.Yamanote.Tokyo",
      "name_ja": "東京",
      "name_en": "Tokyo",
      "coord": { "lon": 139.7671, "lat": 35.6812 }
    }
  ]
}
```

---

## 外部サービス連携

### ODPT (公共交通オープンデータセンター)

| 項目 | 値 |
|------|-----|
| Base URL | https://api-challenge.odpt.org/api/v4 |
| 認証 | API Key (ヘッダー or クエリパラメータ) |
| データ形式 | GTFS-RT (Protobuf) |

**エンドポイント:**
- TripUpdate: `/gtfs/realtime/jreast_odpt_train_trip_update`
- VehiclePosition: `/gtfs/realtime/jreast_odpt_train_vehicle`

### OpenTripPlanner

| 項目 | 値 |
|------|-----|
| URL | http://localhost:8080 |
| API | GraphQL |
| データ | JR東日本 GTFS |

**GraphQL エンドポイント:**
```
POST /otp/routers/default/index/graphql
```

---

## データ形式

### 駅データ (stations.json)

```json
{
  "id": "JR-East.Yamanote.Tokyo",
  "title": { "ja": "東京", "en": "Tokyo" },
  "coord": [139.7671, 35.6812],
  "railway": "JR-East.Yamanote"
}
```

### 路線座標データ (coordinates.json)

```json
{
  "id": "JR-East.Yamanote",
  "sublines": [
    {
      "id": "JR-East.Yamanote.0",
      "coords": [[139.7671, 35.6812], [139.7701, 35.6852], ...]
    }
  ]
}
```

### 路線設定 (config.py)

```python
class LineConfig(BaseModel):
    name: str           # "山手線"
    gtfs_route_id: str  # "JR-East.Yamanote"
    mt3d_id: str        # Mini Tokyo 3D ID

SUPPORTED_LINES = {
    "yamanote": LineConfig(
        name="山手線",
        gtfs_route_id="JR-East.Yamanote",
        mt3d_id="JR-East.Yamanote"
    ),
    # ... 51路線
}
```

---

## デプロイ構成

### 開発環境

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Vite Dev       │     │   FastAPI        │     │   OTP Docker     │
│   :5173          │ ←→  │   :8000          │ ←→  │   :8080          │
└──────────────────┘     └──────────────────┘     └──────────────────┘
         │                        │
         └───── /api proxy ───────┘
```

### 本番環境 (推奨)

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Nginx          │     │   Uvicorn        │     │   OTP Docker     │
│   :80/:443       │ ←→  │   :8000          │ ←→  │   :8080          │
│   + 静的ファイル │     │   workers=4      │     │                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## パフォーマンス考慮事項

### フロントエンド

| 項目 | 対策 |
|------|------|
| 地図レンダリング | Mapbox GL JS (WebGL) |
| 電車アニメーション | requestAnimationFrame (60fps) |
| API ポーリング | 2秒間隔、補間アニメーションで滑らか化 |
| メモリ | 列車位置は Ref で保持、不要なre-render回避 |

### バックエンド

| 項目 | 対策 |
|------|------|
| データキャッシュ | 起動時にJSON/DBをメモリにロード |
| GTFS-RT取得 | httpx 非同期クライアント (タイムアウト10秒) |
| 座標計算 | 線路点群キャッシュ、最近傍探索の最適化 |
| OTP連携 | GraphQL クエリ最適化 |

---

## セキュリティ

| 項目 | 対策 |
|------|------|
| CORS | FRONTEND_URL 環境変数で許可オリジン制御 |
| API Key | ODPT_API_KEY を .env で管理、Git除外 |
| Mapbox Token | VITE_MAPBOX_ACCESS_TOKEN を .env.local で管理 |
| 入力検証 | Pydantic モデルによるバリデーション |
