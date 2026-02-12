# System Design Document: NowTrain (詳細版)

## 1. プロジェクト概要 (Project Overview)

**システム名**: NowTrain - Realtime Train Tracker & Navigator

**不変の目的**:
「まるでゲームのような滑らかな電車移動」と「実用的な乗り換え案内」の融合。
JR東日本の首都圏主要51路線を対象に、ODPT (公共交通オープンデータ) のリアルタイム位置情報と、OpenTripPlanner (OTP) の経路検索エンジンを組み合わせ、ユーザーが今乗っている（あるいは乗る予定の）電車を地図上でリアルタイムに追跡できるWebアプリケーションである。

**アーキテクチャ概要**:

```mermaid
graph TD
    User[User (Browser / Mobile)] -->|HTTPS| FE[Frontend (React 19 + Vite)]
    FE -->|Mapbox GL JS| Map[Mapbox Service]
    
    subgraph "Backend System (FastAPI)"
        FE -->|REST API (Polling)| BE[Main Application (main.py)]
        BE -->|Physics Logic| Physics[Train Position Engine v4]
        BE -->|Cache Access| Cache[Data Cache (In-Memory)]
    end
    
    subgraph "External Services & Data"
        BE -.->|GTFS-RT (PB)| ODPT[ODPT API (Train Locations)]
        BE -.->|Route Search| OTP[OpenTripPlanner (Docker)]
        OTP -.->|GTFS Static| StaticData[GTFS Data Files]
    end
```

**技術スタック詳細**:

| Category | Technology | Version / Details |
| :--- | :--- | :--- |
| **Frontend** | React | **19.0.0** (Latest) |
| | Build Tool | Vite 7.0 |
| | Map Library | **Mapbox GL JS** (Vector Maps) |
| | State Mgmt | React Hooks + Refs (High perf animation) |
| | HTTP Client | Native `fetch` with AbortController |
| **Backend** | Python | **3.11+** |
| | Framework | **FastAPI** + Uvicorn |
| | ORM | SQLAlchemy (v2.0 style) |
| | Data Format | Protocol Buffers (gtfs-realtime) |
| | Routing | **OpenTripPlanner 2.5.0** (Java based) |
| **Infra** | Docker | Compose for OTP orchestration |
| | CI | GitHub Actions (Lint/Test/E2E) |

---

## 2. バックエンド詳細仕様 (Backend Specifications)

### 2.1. API エンドポイント詳細
`backend/main.py` に実装された主要エンドポイントの仕様。

| Group | Method | Path | Params | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Static Data** | GET | `/api/lines` | `operator` | 対応する51路線のID、名称、カラーコード等を返す。 |
| | GET | `/api/stations` | `lineId` | 指定路線の駅リスト（順序付き）と座標を返す。 |
| | GET | `/api/shapes` | `lineId` | 路線の描画用 GeoJSON LineString を返す。 |
| **Realtime** | GET | `/api/trains/{line_id}/positions/v4` | `lineId` | **[Core]** 指定路線の全列車位置を物理演算済みで返す。 |
| **Routing** | GET | `/api/route/search` | `from`, `to`, `date`, `time` | OTPを利用した経路検索。結果にその電車の現在位置を付加する。 |
| **Debug** | POST | `/api/debug/time-travel` | `virtual_time` | サーバー時刻を仮想時刻に固定し、モックデータを生成するモード。 |

### 2.2. 列車位置計算ロジック (`train_position_v4.py`)
本システムの核となる「物理演算ベース位置推定」のロジック。
単なる線形補間ではなく、E235系等の性能特性を模した**台形速度制御モデル**を使用している。

#### A. 加減速モデル (Physics Model)
`calculate_physics_progress(elapsed_time, total_duration)` 関数にて実装。
*   **加速時間 ($T_{acc}$)**: 30.0秒 (0 → 巡航速度)
*   **減速時間 ($T_{dec}$)**: 25.0秒 (巡航速度 → 0)
*   区間所要時間が短すぎる場合は、加速・減速時間を比率で短縮する。
*   **進捗率 ($P$)**: $0.0$ (前駅) 〜 $1.0$ (次駅) で算出される。

#### B. 座標マッピング (Track Snapping)
1.  **進捗率の距離変換**: 区間の総線路長 $\times P$ で、始点からの走行距離を算出。
2.  **線路形状データ**: `get_merged_coords` により、複雑な枝分かれやループを持つ線路データを一本の LineString として扱う。
3.  **マッピング**: 算出された走行距離に対応する線路上の座標 (Lat, Lon) と、その地点の線路の方位角 (Bearing) を計算する。
4.  **Threshold**: 線路データと駅座標が 500m 以上離れている場合、データ不整合とみなし**直線補間 (Linear Fallback)** に切り替える安全策が実装されている。

### 2.3. データ処理とキャッシュ
*   **GTFS-RT Parsing**: `gtfs_rt_tripupdate.py` にて、ODPTからのProtocol Buffersデータを解析。
*   **DataCache**: `backend/data_cache.py` (Singleton)。
    *   駅座標、路線形状（GeoJSON）、静的時刻表データをメモリ上に保持。
    *   起動時に `data/` ディレクトリからJSONファイルをロードする。

---

## 3. フロントエンド詳細仕様 (Frontend Specifications)

### 3.1. マップ描画とアニメーション (`MapView.jsx`)
Mapbox GL JS 上で、バックエンドのポーリング間隔 (2000ms) を埋める **60fps 補間アニメーション** をクライアントサイドで実装している。

#### A. State & Refs
Reactの `useState` は描画トリガーに使い、高頻度更新が必要なデータは `useRef` で管理している。
*   `trainPositionsRef`: 全列車の現在位置、目標位置、開始時刻を保持。
*   `animationRef`: `requestAnimationFrame` のハンドル。

#### B. アニメーションループ (`animateTrains`)
1.  **Time Delta**: `performance.now()` を使用して、前回のデータ取得からの経過時間を計測。
2.  **Interpolation**:
    $$Pos_{current} = Pos_{start} + (Pos_{target} - Pos_{start}) \times \frac{Elapsed}{2000ms}$$
3.  **Marker Update**:
    *   **通常列車**: Mapbox の `SymbolLayer` (`train-arrow` アイコン) の GeoJSON Source を更新。
    *   **My Train (追跡中)**: HTML Marker (`div`要素) を使用し、詳細なツールチップ（遅延、次の駅など）を表示。

### 3.2. 検索機能とナビゲーション
*   **SearchScreen (`SearchScreen.jsx`)**:
    *   駅名のインクリメンタルサーチ（`serverData.js` 経由でAPI `api/stations/search` を叩く）。
    *   日付・時刻選択UI。
*   **API Client (`serverData.js`)**:
    *   `fetch` API のラッパー。
    *   環境変数 `VITE_API_BASE` で接続先を切り替え可能（デフォルト `localhost:8000`）。

---

## 4. データモデル定義 (Data Models)

### 4.1. `SegmentProgress` (Internal Model)
列車が現在「どの駅間」を「どの程度進んだか」を表す中心的なデータ構造。

```python
@dataclass
class SegmentProgress:
    trip_id: str          # 列車ID (GTFS Trip ID)
    train_number: str     # 列車番号 (例: "1234G")
    direction: str        # 方面 (例: "Inbound", "Outbound")
    status: str           # "running" | "stopped" | "invalid"
    
    # 区間情報
    prev_station_id: str  # 前駅ID
    next_station_id: str  # 次駅ID
    
    # 時間計算用
    now_ts: int           # 現在計算時刻 (Unix Sec)
    t0_departure: int     # 前駅発時刻
    t1_arrival: int       # 次駅着時刻
    
    # 物理演算結果
    progress: float       # 進捗率 (0.0 - 1.0)
    delay: int            # 遅延秒数
```

### 4.2. `LineConfig` (Configuration)
`backend/config.py` に定義された路線設定。51路線がハードコードされており、`mt3d_id` (MiniTokyo3D互換ID) と `gtfs_route_id` をマッピングしている。

---

## 5. インフラストラクチャ詳細

### 5.1. 外部連携システム
*   **ODPT API**:
    *   JR東日本のリアルタイムデータを `GTFS-RT` 形式で取得。
    *   API Keyは `ODPT_API_KEY` 環境変数で管理。
*   **OpenTripPlanner (OTP)**:
    *   Docker コンテナ (`opentripplanner/opentripplanner:2.5.0`) で稼働。
    *   `otp_data/` に配置された静的GTFSとOSM (OpenStreetMap) データをロードしてグラフを構築。
    *   Backendからは HTTP API で経路探索を依頼する。

### 5.2. Time Travel Mode (Debugging)
E2Eテストやデモのために、サーバー時刻を「過去」や「未来」に固定する機能。
*   **仕組み**: `time_manager.py` が現在時刻をフックする。
*   **データ生成**: リアルタイムデータが無い時間帯の場合、`mock_trip_generator.py` が静的時刻表から「仮想のGTFS-RT」をオンザフライで生成し、あたかもその時間に電車が走っているかのように振る舞う。

---

## 6. 今後の改善ロードマップ (Roadmap)

### Phase 1: 通信の最適化
*   **課題**: 現在のポーリング(2秒間隔)は、クライアント数が増えるとサーバー負荷が線形に増大する。
*   **対策**: FastAPI の WebSocket を使用し、列車位置の差分更新(Delta Update)をプッシュ配信するアーキテクチャへ移行する。

### Phase 2: マップ描画の高度化
*   **課題**: GeoJSONの全件配信はデータ量が大きい。
*   **対策**: Mapbox Vector Tiles (MVT) を導入し、線路データをベクトルタイルとして配信することで、初期ロード時間を短縮し、ズームレベルに応じた詳細度制御を行う。

### Phase 3: エリア拡大
*   **課題**: 現在はJR東日本のみ。
*   **対策**: 東京メトロ、都営地下鉄のODPTデータも統合し、首都圏の完全網羅を目指す。`LineConfig` の拡張が必要。
