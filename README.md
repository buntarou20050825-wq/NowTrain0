# NowTrain

JR東日本の電車をリアルタイムで追跡し、経路検索・ナビゲーションを行うWebアプリケーション。

## 主な機能

- **リアルタイム電車位置表示**: ODPT (公共交通オープンデータ) APIを使用して、51路線の電車位置をリアルタイムで表示
- **経路検索**: OpenTripPlannerによる乗換案内
- **My Train機能**: 乗車予定の電車を自動追跡・ハイライト表示
- **物理演算ベースの位置計算**: E235系の加減速特性を考慮した滑らかな電車移動表示
- **60fps アニメーション**: クライアントサイド補間による滑らかな電車移動

---

## 機能一覧と必要環境

| 機能 | Python + Node.js のみ | Docker も必要 |
|------|----------------------|---------------|
| 電車位置のリアルタイム表示 | OK | - |
| 路線選択・地図表示 | OK | - |
| 経路検索（乗換案内） | NG | OK |
| My Train（乗車電車追跡） | NG | OK |

※ Dockerをインストールしない場合でも、電車位置表示機能は使用できます。

---

## 必要なソフトウェアのインストール

### 1. Python 3.11

1. https://www.python.org/downloads/ にアクセス
2. 「Download Python 3.11.x」をクリックしてダウンロード
3. インストーラーを実行
4. **重要**: 最初の画面で「Add python.exe to PATH」に必ずチェックを入れる
5. 「Install Now」をクリック

**確認方法**: コマンドプロンプトを開いて以下を実行
```
python --version
```
`Python 3.11.x` と表示されればOK

### 2. Node.js 20 LTS

1. https://nodejs.org/ にアクセス
2. 「LTS」と書かれた緑のボタンをクリックしてダウンロード
3. インストーラーを実行し、すべてデフォルト設定でインストール

**確認方法**: コマンドプロンプトを開いて以下を実行
```
node --version
```
`v20.x.x` または `v18.x.x` と表示されればOK

### 3. Docker Desktop（経路検索機能を使う場合のみ）

経路検索機能が不要な場合、この手順はスキップできます。

1. https://www.docker.com/products/docker-desktop/ にアクセス
2. 「Download for Windows」をクリック
3. インストーラーを実行
4. インストール完了後、PCを再起動
5. Docker Desktop を起動（初回起動時に利用規約への同意が必要）
6. WSL 2 のインストールを求められた場合は、画面の指示に従ってインストール

**確認方法**: コマンドプロンプトを開いて以下を実行
```
docker --version
```
`Docker version 24.x.x` などと表示されればOK

---

## セットアップ手順

### 1. フォルダの準備

1. `NowTrain.zip` を任意の場所に解凍
2. 解凍してできた `NowTrain` フォルダを開く

以降の手順では、このフォルダを「プロジェクトフォルダ」と呼びます。

### 2. 環境変数ファイルの作成

#### バックエンド用 (`backend/.env`)

1. プロジェクトフォルダ内の `backend` フォルダを開く
2. 右クリック → 「新規作成」→「テキスト ドキュメント」
3. ファイル名を `.env` に変更（拡張子 `.txt` は削除）
4. ファイルを開いて以下を記入して保存:

```
ODPT_API_KEY=ここにAPIキーを入力
FRONTEND_URL=http://localhost:5173
```

**ODPT APIキーの取得方法:**
1. https://developer.odpt.org/ にアクセス
2. 右上の「ユーザー登録」からアカウントを作成
3. メール認証を完了
4. ログイン後、「APIアクセス」メニューから APIキーを取得
5. 取得したキーを `.env` ファイルの `ODPT_API_KEY=` の後ろに貼り付け

#### フロントエンド用 (`frontend/.env.local`)

1. プロジェクトフォルダ内の `frontend` フォルダを開く
2. 右クリック → 「新規作成」→「テキスト ドキュメント」
3. ファイル名を `.env.local` に変更
4. ファイルを開いて以下を記入して保存:

```
VITE_MAPBOX_ACCESS_TOKEN=ここにトークンを入力
```

**Mapboxトークンの取得方法:**
1. https://account.mapbox.com/ にアクセス
2. 「Sign up」からアカウントを作成（無料）
3. ログイン後、ダッシュボードの「Access tokens」セクションを確認
4. 「Default public token」をコピー
5. `.env.local` ファイルの `VITE_MAPBOX_ACCESS_TOKEN=` の後ろに貼り付け

### 3. バックエンドのセットアップ

コマンドプロンプトを開き、以下を1行ずつ実行:

```bash
cd プロジェクトフォルダのパス\backend
```

例: `cd C:\Users\username\Desktop\NowTrain\backend`

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

プロンプトの先頭に `(.venv)` と表示されればOK

```bash
c
```

インストールが完了するまで数分待ちます。

### 4. フロントエンドのセットアップ

新しいコマンドプロンプトを開き、以下を実行:

```bash
cd プロジェクトフォルダのパス\frontend
```

```bash
npm install
```

インストールが完了するまで数分待ちます。

### 5. OpenTripPlanner の起動（経路検索を使う場合のみ）

Docker Desktop が起動していることを確認してから、コマンドプロンプトで以下を実行:

```bash
cd プロジェクトフォルダのパス
```

```bash
docker-compose up -d otp
```

初回起動時は5〜10分かかります。

**確認方法**: ブラウザで http://localhost:8080 にアクセスし、OTPの画面が表示されればOK

---

## 起動方法

毎回、以下の手順でアプリを起動します。

### 1. バックエンドの起動

コマンドプロンプトを開いて以下を実行:

```bash
cd プロジェクトフォルダのパス\backend
.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

「Uvicorn running on http://127.0.0.1:8000」と表示されればOK

**このウィンドウは閉じないでください。**

### 2. OTP の起動（経路検索を使う場合のみ）

Docker Desktop を起動してから、新しいコマンドプロンプトで:

```bash
cd プロジェクトフォルダのパス
docker-compose up -d otp
```

### 3. フロントエンドの起動

新しいコマンドプロンプトを開いて以下を実行:

```bash
cd プロジェクトフォルダのパス\frontend
npm run dev
```

「Local: http://localhost:5173/」と表示されればOK

### 4. ブラウザでアクセス

ブラウザで http://localhost:5173 にアクセス

---

## 使い方

### 1. 経路検索 (検索画面)
1. 出発駅と到着駅を入力（入力中に候補が表示されます）
2. 日時を選択
3. 「経路を検索」ボタンをクリック

### 2. 経路選択 (結果画面)
1. 複数の経路候補から選択
2. カードをクリックして詳細を展開
3. 「この経路でナビ開始」ボタンをクリック

### 3. ナビゲーション (地図画面)
- 選択した経路が地図上にハイライト表示
- 乗車予定の電車が赤色マーカーでリアルタイム追跡
- ボトムシートで運行状況を確認

---

## トラブルシューティング

### 「python」コマンドが認識されない

Pythonインストール時に「Add python.exe to PATH」にチェックを入れ忘れた可能性があります。
Pythonを再インストールし、チェックを入れてください。

### 「npm」コマンドが認識されない

Node.js のインストール後、コマンドプロンプトを再起動してください。

### Docker が起動しない

1. PCを再起動
2. Docker Desktop を管理者として実行
3. WSL 2 がインストールされているか確認

### 地図が表示されない

`frontend/.env.local` ファイルの Mapbox トークンが正しく設定されているか確認してください。

### 電車が表示されない

`backend/.env` ファイルの ODPT APIキーが正しく設定されているか確認してください。

### 経路検索ができない

1. Docker Desktop が起動しているか確認
2. `docker-compose up -d otp` を実行したか確認
3. http://localhost:8080 でOTPが起動しているか確認

---

## エラートラッキング（オプション）

Sentry.io を使用してエラーを自動検知・通知する機能があります。この機能は任意であり、設定しなくてもアプリは動作します。

### Sentry のセットアップ

1. https://sentry.io でアカウントを作成（無料枠: 5,000エラー/月）
2. 2つのプロジェクトを作成:
   - フロントエンド用: プラットフォーム「React」を選択
   - バックエンド用: プラットフォーム「Python」→「FastAPI」を選択
3. 各プロジェクトの DSN（Data Source Name）を取得

### 環境変数の設定

**フロントエンド** (`frontend/.env.local` に追加):
```
VITE_SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
```

**バックエンド** (`backend/.env` に追加):
```
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
```

設定後、アプリを再起動するとエラートラッキングが有効になります。

---

## 技術スタック

### バックエンド
| 技術 | バージョン | 用途 |
|------|-----------|------|
| Python | 3.10+ | 言語 |
| FastAPI | 0.104+ | Webフレームワーク |
| Uvicorn | 0.24+ | ASGIサーバー |
| SQLAlchemy | 2.0+ | ORM |
| SQLite | - | データベース |
| GTFS-RT Bindings | 1.0+ | Protobuf解析 |
| OpenTripPlanner | 2.5.0 | 経路検索エンジン (Docker) |

### フロントエンド
| 技術 | バージョン | 用途 |
|------|-----------|------|
| React | 19.x | UIフレームワーク |
| Vite | 7.x | ビルドツール |
| Mapbox GL JS | 3.16+ | 地図表示 |
| React Router | 6.x | ルーティング |

---

## システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │SearchScreen │→│ResultsScreen│→│NavigationScreen     │   │
│  │ (駅入力)    │ │ (経路一覧)  │ │ (地図+BottomSheet)  │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
│                         ↓                                   │
│                    ┌─────────┐                              │
│                    │ MapView │ (Mapbox GL JS)               │
│                    └─────────┘                              │
└─────────────────────────────────────────────────────────────┘
                            │
                      Fetch API
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │ 駅検索 API   │ │ 経路検索 API │ │ 電車位置 API     │    │
│  │/api/stations │ │/api/route    │ │/api/trains/{id}  │    │
│  └──────────────┘ └──────────────┘ └──────────────────┘    │
│         │                │                   │              │
│         ↓                ↓                   ↓              │
│  ┌──────────┐    ┌────────────┐    ┌─────────────────┐     │
│  │DataCache │    │ OTP Client │    │train_position_v4│     │
│  │(JSON/DB) │    │ (GraphQL)  │    │ (物理演算)      │     │
│  └──────────┘    └────────────┘    └─────────────────┘     │
└─────────────────────────────────────────────────────────────┘
           │              │                    │
           ↓              ↓                    ↓
    ┌──────────┐   ┌────────────┐      ┌──────────────┐
    │  SQLite  │   │    OTP     │      │   ODPT API   │
    │(駅ランク)│   │(Docker:8080)│     │ (GTFS-RT)    │
    └──────────┘   └────────────┘      └──────────────┘
```

詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照。

---

## 対応路線

JR東日本の51路線に対応:

| カテゴリ | 路線 |
|---------|------|
| 環状線 | 山手線 |
| 東西線 | 京浜東北線、中央線快速、総武線各駅停車、中央総武線 |
| 南北線 | 東海道線、横須賀線、京葉線、内房線、外房線 |
| 埼玉方面 | 埼京線、川越線、高崎線、宇都宮線 |
| 千葉方面 | 常磐線快速/各停、成田線、総武線快速 |
| 神奈川方面 | 横浜線、南武線、根岸線 |
| 多摩方面 | 青梅線、五日市線、八高線 |
| その他 | 武蔵野線、湘南新宿ライン、上野東京ライン等 |

---

## ドキュメント

- [システムアーキテクチャ](docs/ARCHITECTURE.md) - 詳細なアーキテクチャとAPI仕様
- [電車位置計算の仕様](docs/TRAIN_POSITION.md) - 物理演算と位置計算のアルゴリズム

---

## ライセンス

MIT License

---

## 謝辞

- [ODPT (公共交通オープンデータセンター)](https://www.odpt.org/) - リアルタイム電車データ
- [OpenTripPlanner](https://www.opentripplanner.org/) - 経路検索エンジン
- [Mini Tokyo 3D](https://minitokyo3d.com/) - 駅・路線座標データ形式の参考
- [Mapbox](https://www.mapbox.com/) - 地図表示

---

## CI / ローカル検証

GitHub Actions により、`main` / `develop` ブランチへの push および Pull Request で自動テストが実行されます。
ローカルで同じ検証を行うには、以下のコマンドを実行してください。

### バックエンド検証

```bash
cd backend

# 仮想環境の作成（初回のみ）
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

# dev依存のインストール（ruff, pytest 含む）
pip install -r requirements-dev.txt

# Lint (ruff)
ruff check .

# ユニットテスト (pytest)
pytest -v
```

### フロントエンド検証

```bash
cd frontend

# 依存のインストール
npm ci

# Lint (ESLint)
npm run lint

# ユニットテスト (Vitest)
npm run test

# ビルド確認
npm run build
```

### E2E テスト（Playwright）

```bash
cd frontend

# Playwright ブラウザのインストール（初回のみ）
npx playwright install --with-deps chromium

# バックエンドをモックモードで起動（別ターミナル）
cd ../backend
VIRTUAL_TIME="2026-02-12T08:30:00+09:00" python -m uvicorn main:app --port 8000

# フロントエンドをプレビューモードで起動（別ターミナル）
cd ../frontend
npm run build && npx vite preview --port 4173

# E2E テスト実行
npm run e2e
```

> **Note**: E2E テストはバックエンドを `VIRTUAL_TIME` 環境変数でモックモード起動するため、ODPT APIキーは不要です。

