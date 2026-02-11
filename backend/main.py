# backend/main.py
from __future__ import annotations

import logging
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import get_line_config  # MS10: 路線設定のインポート
from data_cache import DataCache
from database import SessionLocal, StationRank
from geometry import build_all_railways_cache, merge_sublines_fallback, merge_sublines_v2

# Sentry エラートラッキング初期化 (環境変数が設定されている場合のみ)
load_dotenv()  # 先に環境変数を読み込む
_sentry_dsn = os.getenv("SENTRY_DSN")
if _sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=os.getenv("ENVIRONMENT", "development"),
        # パフォーマンストレースのサンプルレート（10%）
        traces_sample_rate=0.1,
        # プロファイリングのサンプルレート
        profiles_sample_rate=0.1,
    )

# OTP クライアント（経路検索用）
try:
    from otp_client import extract_trip_ids, parse_otp_response
    from otp_client import search_route as otp_search_route
except ImportError as e:
    logging.warning(f"OTP client import failed: {e}. Route search will not work.")
    otp_search_route = None
    parse_otp_response = None
    extract_trip_ids = None

# GTFS解析 & 列車位置計算 (MS11: 汎用化)
try:
    from gtfs_rt_tripupdate import fetch_trip_updates
    from train_position_v4 import calculate_coordinates, compute_all_progress
except ImportError as e:
    logging.warning(f"Module import failed: {e}. V4 API will not work.")
    fetch_trip_updates = None
    compute_all_progress = None
    calculate_coordinates = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
JST = ZoneInfo("Asia/Tokyo")

load_dotenv()

app = FastAPI()

# CORS: フロントエンド (Vite dev server) からの直接アクセスを許可
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent  # NowTrain-v2/
DATA_DIR = BASE_DIR / "data"

data_cache = DataCache(DATA_DIR)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class StationRankUpdate(BaseModel):
    rank: str
    dwell_time: int


# MS11: ID解決用ヘルパー関数
def resolve_line_id(input_id: str) -> str:
    """
    chuo_rapid -> JR-East.ChuoRapid のようにIDを変換する。
    設定がない場合はそのまま返す。
    """
    conf = get_line_config(input_id)
    if conf:
        return conf.mt3d_id
    return input_id


@app.on_event("startup")
async def startup_event():
    # CI/E2Eでは外部ファイル(mini-tokyo-3d/*.json)に依存しない
    if os.getenv("SKIP_DATA_LOAD") == "1":
        print("SKIP_DATA_LOAD=1: skipping data_cache.load_all()")
        return

    data_cache.load_all()
    logger.info(
        "Data loaded: %d railways, %d stations",
        len(data_cache.railways),
        len(data_cache.stations),
    )
    # MS1-TripUpdate: httpx.AsyncClient を作成
    app.state.http_client = httpx.AsyncClient()
    logger.info("httpx.AsyncClient initialized")

    # タイムトラベル: VIRTUAL_TIME 環境変数でモック時刻を設定
    from time_manager import time_mgr

    virtual_time_str = os.getenv("VIRTUAL_TIME", "").strip()
    if virtual_time_str:
        try:
            time_mgr.set_virtual_time(virtual_time_str)
            logger.info("Time travel enabled: %s", time_mgr.get_status())
        except ValueError as e:
            logger.error("Invalid VIRTUAL_TIME env: %s", e)


@app.on_event("shutdown")
async def shutdown_event():
    # MS1-TripUpdate: httpx.AsyncClient をクローズ
    if hasattr(app.state, "http_client"):
        await app.state.http_client.aclose()
        logger.info("httpx.AsyncClient closed")


# CORS 設定
_default_origins = "http://localhost:5173,http://localhost:5174"  # 5174を追加
_raw_origins = os.getenv("FRONTEND_URL", _default_origins)
frontend_urls = [origin.strip() for origin in _raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_urls,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.api_route("/api/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


@app.get("/api/lines")
async def get_lines(operator: Optional[str] = None):
    logger.info("GET /api/lines called with operator=%s", operator)

    lines = data_cache.railways

    if operator:
        prefix = operator + "."
        lines = [line for line in lines if line.get("id", "").startswith(prefix)]
        # TODO (MS6): operators.json を使った厳密な事業者フィルタを検討

    def to_line_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
        title = raw.get("title", {})
        station_ids = raw.get("stations", [])
        line_id = raw.get("id", "")
        operator_id = line_id.split(".")[0] if "." in line_id else ""
        return {
            "id": line_id,
            "name_ja": title.get("ja", ""),
            "name_en": title.get("en", ""),
            "color": raw.get("color", "#000000"),
            "operator": operator_id,
            "station_count": len(station_ids),
        }

    return {"lines": [to_line_summary(line) for line in lines]}


@app.get("/api/lines/{line_id}")
async def get_line(line_id: str):
    logger.info("GET /api/lines/%s", line_id)

    # MS11: ID解決
    target_id = resolve_line_id(line_id)

    raw = next((railway for railway in data_cache.railways if railway.get("id") == target_id), None)
    if not raw:
        raise HTTPException(status_code=404, detail=f"Line not found: {line_id} (resolved: {target_id})")
    if not raw:
        raise HTTPException(status_code=404, detail=f"Line not found: {line_id} (resolved: {target_id})")

    title = raw.get("title", {})
    operator_id = target_id.split(".")[0] if "." in target_id else ""

    return {
        "id": raw.get("id"),
        "name_ja": title.get("ja", ""),
        "name_en": title.get("en", ""),
        "color": raw.get("color", "#000000"),
        "operator": operator_id,
        "stations": raw.get("stations", []),
        "ascending": raw.get("ascending"),
        "descending": raw.get("descending"),
        "car_composition": raw.get("carComposition"),  # 元データ camelCase → API では snake_case に揃え済み
    }


@app.get("/api/stations")
async def get_stations(
    lineId: Optional[str] = None,
    line_id: Optional[str] = None,  # エイリアス対応
):
    # 1. パラメータの正規化
    target_param = lineId or line_id
    logger.info(f"GET /api/stations called. Param: {target_param}")

    if target_param is None:
        raise HTTPException(status_code=400, detail="lineId (or line_id) query parameter is required")

    # 2. ID解決
    target_id = resolve_line_id(target_param)
    logger.info(f"Resolving Stations ID: '{target_param}' -> '{target_id}'")

    # 3. データ検索 (FROM DB)
    exists = any(railway.get("id") == target_id for railway in data_cache.railways)
    if not exists:
        logger.warning(f"Station lookup failed: Line ID '{target_id}' not found in railways.")
        raise HTTPException(status_code=404, detail=f"Line not found: {target_param} -> {target_id}")

    stations = data_cache.get_stations_by_line(target_id)
    logger.info(f"Found {len(stations)} stations for {target_id} (from DB)")

    def to_station(raw: Dict[str, Any]) -> Dict[str, Any]:
        title = raw.get("title", {})
        coord_raw = raw.get("coord")
        lon, lat = None, None
        if isinstance(coord_raw, (list, tuple)) and len(coord_raw) >= 2:
            lon, lat = coord_raw[0], coord_raw[1]

        station_id = raw.get("id")
        rank_entry = data_cache.station_rank_cache.get(station_id) if station_id else None
        rank = rank_entry.get("rank") if rank_entry else "B"
        dwell_time = rank_entry.get("dwell_time") if rank_entry else data_cache.get_station_dwell_time(station_id)

        return {
            "id": station_id,
            "line_id": raw.get("railway"),
            "name_ja": title.get("ja", ""),
            "name_en": title.get("en", ""),
            "coord": {"lon": lon, "lat": lat},
            "rank": rank,
            "dwell_time": dwell_time,
        }

    return {"stations": [to_station(st) for st in stations]}


@app.get("/api/stations/search")
async def search_stations(
    q: str = Query(..., min_length=1, description="検索キーワード（日本語または英語）"),
    limit: int = Query(10, ge=1, le=50, description="最大件数"),
):
    """
    駅名で駅を検索する（部分一致）

    Args:
        q: 検索キーワード
        limit: 最大件数（デフォルト10、最大50）

    Returns:
        マッチした駅のリスト
    """
    logger.info(f"GET /api/stations/search called with q={q}, limit={limit}")

    results = data_cache.search_stations_by_name(q, limit=limit)

    return {"query": q, "count": len(results), "stations": results}


@app.put("/api/stations/{station_id}/rank")
async def update_station_rank(
    station_id: str,
    update_data: StationRankUpdate,
    db: Session = Depends(get_db),
):
    if update_data.dwell_time < 0:
        raise HTTPException(status_code=400, detail="dwell_time must be >= 0")
    if update_data.rank not in {"S", "A", "B"}:
        raise HTTPException(status_code=400, detail="rank must be one of: S, A, B")

    rank_obj = db.query(StationRank).filter(StationRank.station_id == station_id).first()

    if not rank_obj:
        rank_obj = StationRank(station_id=station_id)
        db.add(rank_obj)

    rank_obj.rank = update_data.rank
    rank_obj.dwell_time = update_data.dwell_time

    db.commit()
    db.refresh(rank_obj)

    data_cache.station_rank_cache[station_id] = {
        "rank": rank_obj.rank,
        "dwell_time": rank_obj.dwell_time,
    }

    logger.info(
        "Station Rank Updated: %s -> %s (%ds)",
        station_id,
        update_data.rank,
        update_data.dwell_time,
    )

    return {
        "status": "success",
        "data": {
            "station_id": rank_obj.station_id,
            "rank": rank_obj.rank,
            "dwell_time": rank_obj.dwell_time,
        },
    }


# ============================================================
# API エンドポイント: 線路形状
# ============================================================


@app.get("/api/shapes")
async def get_shapes(
    lineId: Optional[str] = None,
    line_id: Optional[str] = None,  # エイリアス対応
):
    # 1. パラメータの正規化
    target_param = lineId or line_id
    logger.info(f"GET /api/shapes called. Param: {target_param}")

    if target_param is None:
        raise HTTPException(status_code=400, detail="lineId (or line_id) query parameter is required")

    # 2. ID解決
    target_id = resolve_line_id(target_param)
    logger.info(f"Resolving Shape ID: '{target_param}' -> '{target_id}'")

    # 3. Railwaysデータの確認
    exists = any(railway.get("id") == target_id for railway in data_cache.railways)
    if not exists:
        logger.error(f"Shape lookup failed: ID '{target_id}' not found in railways.")
        raise HTTPException(status_code=404, detail=f"Line not found in railways: {target_id}")

    # 2. Coordinatesデータの検索
    railway_coords = data_cache.coordinates.get("railways", [])
    entry = next((c for c in railway_coords if c.get("id") == target_id), None)

    if not entry:
        logger.error(f"Target ID {target_id} not found in coordinates.json")
        # デバッグ: 近いIDがないか探す
        candidates = [c.get("id") for c in railway_coords if "Chuo" in c.get("id", "")]
        logger.info(f"Did you mean one of these? {candidates}")
        raise HTTPException(status_code=404, detail=f"Shape not found in coordinates: {lineId} -> {target_id}")

    # 3. 座標結合処理 (MS12: グラフベースのマージに改善 + 参照解決)
    sublines = entry.get("sublines", [])
    is_loop = entry.get("loop", False)

    logger.info(f"Found entry for {target_id}, has {len(sublines)} sublines, loop={is_loop}")

    # 参照解決用のキャッシュを構築（全路線の座標）
    all_railways_cache = build_all_railways_cache(data_cache.coordinates)

    # グラフベースのマージを試行（参照解決を含む）
    merged_coords = merge_sublines_v2(sublines, is_loop=is_loop, all_railways_cache=all_railways_cache)

    # フォールバック: グラフベースが失敗した場合
    if not merged_coords:
        logger.warning(f"Graph-based merge failed for {target_id}, trying fallback")
        merged_coords = merge_sublines_fallback(sublines)

    if not merged_coords:
        logger.error(f"Merged coords empty for {target_id}")
        raise HTTPException(status_code=404, detail=f"Shape coordinates are empty: {lineId}")

    logger.info(f"Successfully merged {len(merged_coords)} points for {target_id}")

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": merged_coords,
        },
        "properties": {
            "line_id": target_id,
            "color": entry.get("color", "#000000"),
            "segment_type": "main",
        },
    }

    return {
        "type": "FeatureCollection",
        "features": [feature],
    }


# ▼▼▼ 追加: デバッグ用エンドポイント (ファイルの末尾などに追加) ▼▼▼
@app.get("/api/debug/available_shapes")
async def debug_available_shapes():
    """coordinates.json に含まれる全線路IDを返す"""
    railway_coords = data_cache.coordinates.get("railways", [])
    ids = [c.get("id") for c in railway_coords]
    return {"count": len(ids), "ids": sorted(ids), "chuo_related": [i for i in ids if "Chuo" in i]}


@app.get("/api/trains/yamanote/positions")
async def get_yamanote_positions():
    """
    山手線のリアルタイム列車位置を取得

    Returns:
        {
            "timestamp": 1760072237,
            "trains": [
                {
                    "tripId": "4201301G",
                    "trainNumber": "301G",
                    "direction": "OuterLoop",
                    "latitude": 35.7204,
                    "longitude": 139.7063,
                    "stopSequence": 11,
                    "status": 1
                },
                ...
            ]
        }
    """
    api_key = os.getenv("ODPT_API_KEY", "").strip()

    try:
        from gtfs_rt_vehicle import fetch_yamanote_positions

        positions = await fetch_yamanote_positions(api_key)

        return {
            "timestamp": positions[0].timestamp if positions else 0,
            "count": len(positions),
            "trains": [
                {
                    "tripId": p.trip_id,
                    "trainNumber": p.train_number,
                    "direction": p.direction,
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "stopSequence": p.stop_sequence,
                    "status": p.status,
                }
                for p in positions
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trains/yamanote/positions/v2")
async def get_yamanote_positions_v2():
    """
    山手線のリアルタイム列車位置を取得（出発時刻付き）
    """
    api_key = os.getenv("ODPT_API_KEY", "").strip()

    try:
        from gtfs_rt_vehicle import fetch_yamanote_positions_with_schedule

        positions = await fetch_yamanote_positions_with_schedule(api_key)

        return {
            "timestamp": positions[0].timestamp if positions else 0,
            "count": len(positions),
            "trains": [
                {
                    "tripId": p.trip_id,
                    "trainNumber": p.train_number,
                    "direction": p.direction,
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "stopSequence": p.stop_sequence,
                    "status": p.status,
                    # 新規追加
                    "departureTime": p.departure_time,
                    "nextArrivalTime": p.next_arrival_time,
                    "timestamp": p.timestamp,  # GTFS-RT更新時刻
                }
                for p in positions
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 注: v3 エンドポイントは削除されました
# 代わりに /api/trains/{line_id}/positions/v4 を使用してください


# ============================================================================
# MS1-TripUpdate: Debug Endpoint
# ============================================================================


@app.get("/api/debug/trip_updates")
async def debug_trip_updates():
    """
    MS1 TripUpdate デバッグ用エンドポイント。
    TripUpdate の取得結果をサンプルとして返す。
    """
    from gtfs_rt_tripupdate import fetch_trip_updates

    api_key = os.getenv("ODPT_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="ODPT_API_KEY not set")

    try:
        client = app.state.http_client
        schedules = await fetch_trip_updates(client, api_key, data_cache)

        # サンプル3件を抽出
        sample_keys = list(schedules.keys())[:3]
        samples = []

        for trip_id in sample_keys:
            schedule = schedules[trip_id]

            # schedules_by_seq を list形式に変換
            stops_list = []
            for seq in schedule.ordered_sequences:
                stu = schedule.schedules_by_seq.get(seq)
                if stu:
                    stops_list.append(
                        {
                            "stop_sequence": stu.stop_sequence,
                            "station_id": stu.station_id,
                            "arrival_time": stu.arrival_time,
                            "departure_time": stu.departure_time,
                            "resolved": stu.resolved,
                            "raw_stop_id": stu.raw_stop_id,
                        }
                    )

            samples.append(
                {
                    "trip_id": schedule.trip_id,
                    "train_number": schedule.train_number,
                    "start_date": schedule.start_date,
                    "direction": schedule.direction,
                    "feed_timestamp": schedule.feed_timestamp,
                    "stop_count": len(schedule.ordered_sequences),
                    "stops": stops_list,
                }
            )

        # 統計情報
        total_count = len(schedules)
        resolved_count = 0
        direction_counts = {"InnerLoop": 0, "OuterLoop": 0, "Unknown": 0}

        for schedule in schedules.values():
            for stu in schedule.schedules_by_seq.values():
                if stu.resolved:
                    resolved_count += 1

            if schedule.direction in direction_counts:
                direction_counts[schedule.direction] += 1
            else:
                direction_counts["Unknown"] += 1

        return {
            "status": "success",
            "total_trains": total_count,
            "resolved_station_count": resolved_count,
            "direction_counts": direction_counts,
            "samples": samples,
        }

    except Exception as e:
        logger.error(f"Error in debug_trip_updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/debug/gtfs_route_ids")
async def debug_gtfs_route_ids():
    """
    デバッグ用: GTFS-RT フィードに含まれる全 route_id を一覧表示する。
    """
    import httpx
    from google.transit import gtfs_realtime_pb2

    from constants import TRIP_UPDATE_URL

    api_key = os.getenv("ODPT_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="ODPT_API_KEY not set")

    try:
        async with httpx.AsyncClient() as client:
            url = f"{TRIP_UPDATE_URL}?acl:consumerKey={api_key}"
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            # 全 route_id を収集
            route_ids = {}
            for entity in feed.entity:
                if entity.HasField("trip_update"):
                    route_id = entity.trip_update.trip.route_id or "(empty)"
                    trip_id = entity.trip_update.trip.trip_id
                    if route_id not in route_ids:
                        route_ids[route_id] = {"count": 0, "sample_trip_ids": []}
                    route_ids[route_id]["count"] += 1
                    if len(route_ids[route_id]["sample_trip_ids"]) < 3:
                        route_ids[route_id]["sample_trip_ids"].append(trip_id)

            return {
                "total_entities": len(feed.entity),
                "unique_route_ids": len(route_ids),
                "route_ids": route_ids,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/debug/gtfs_stop_ids/{line_id}")
async def debug_gtfs_stop_ids(line_id: str):
    """
    デバッグ用: 特定路線のGTFS stop_id をサンプル表示
    """
    from gtfs_rt_tripupdate import fetch_trip_updates

    line_config = get_line_config(line_id)
    if not line_config:
        raise HTTPException(status_code=404, detail=f"Line '{line_id}' not found")

    api_key = os.getenv("ODPT_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="ODPT_API_KEY not set")

    try:
        client = app.state.http_client
        schedules = await fetch_trip_updates(
            client, api_key, data_cache, target_route_id=line_config.gtfs_route_id, mt3d_prefix=line_config.mt3d_id
        )

        samples = []
        for trip_id, schedule in list(schedules.items())[:3]:
            stops = []
            for seq, stu in list(schedule.schedules_by_seq.items())[:5]:
                stops.append(
                    {
                        "seq": seq,
                        "station_id": stu.station_id,
                        "raw_stop_id": stu.raw_stop_id,
                        "resolved": stu.resolved,
                    }
                )
            samples.append(
                {
                    "trip_id": trip_id,
                    "train_number": schedule.train_number,
                    "stops": stops,
                }
            )

        return {
            "line_id": line_id,
            "total_schedules": len(schedules),
            "samples": samples,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MS3: TripUpdate-only v4 API
# ============================================================================


def _get_station_coord(station_id: str | None) -> tuple[float, float] | None:
    """
    駅IDから座標を取得する。
    data_cache.station_positions は (lon, lat) 形式。
    返却は (lat, lon) 形式に変換。
    """
    if not station_id:
        return None

    coord = data_cache.station_positions.get(station_id)
    if coord:
        lon, lat = coord
        return (lat, lon)
    return None


def _calculate_position(
    status: str,
    progress: float | None,
    prev_station_id: str | None,
    next_station_id: str | None,
) -> tuple[float | None, float | None]:
    """
    列車の現在座標を計算する。

    Returns:
        (latitude, longitude) のタプル。計算不能なら (None, None)。
    """
    # 1) stopped: 停車駅の座標
    if status == "stopped":
        # stopped時は prev_station_id == next_station_id
        coord = _get_station_coord(prev_station_id)
        if coord:
            return coord
        # フォールバック
        coord = _get_station_coord(next_station_id)
        if coord:
            return coord
        return (None, None)

    # 2) running: 駅間の線形補間
    if status == "running":
        if progress is None:
            return (None, None)

        prev_coord = _get_station_coord(prev_station_id)
        next_coord = _get_station_coord(next_station_id)

        if prev_coord is None or next_coord is None:
            # どちらかの座標が取れない
            if prev_coord:
                return prev_coord
            if next_coord:
                return next_coord
            return (None, None)

        # 線形補間
        lat0, lon0 = prev_coord
        lat1, lon1 = next_coord

        lat = lat0 + (lat1 - lat0) * progress
        lon = lon0 + (lon1 - lon0) * progress

        return (lat, lon)

    # 3) unknown / invalid: 基本 null
    return (None, None)


@app.get("/api/trains/yamanote/positions/v4")
async def get_yamanote_positions_v4():
    """
    MS3/MS5: TripUpdate-only v4 API エンドポイント。

    TripUpdate から列車位置を計算し、線路形状に沿った座標付きで返す。
    タイムトラベルモード時はモックデータを使用。
    """
    from gtfs_rt_tripupdate import fetch_trip_updates
    from mock_trip_generator import generate_mock_schedules
    from time_manager import time_mgr
    from train_position_v4 import calculate_coordinates, compute_all_progress

    try:
        # タイムトラベルモード: モックデータを使用
        if time_mgr.is_virtual():
            schedules = generate_mock_schedules(
                data_cache,
                time_mgr.now(),
                target_route_id="JR-East.Yamanote",
            )
        else:
            # 実データモード: ODPT API から取得
            api_key = os.getenv("ODPT_API_KEY", "").strip()
            if not api_key:
                return {
                    "source": "tripupdate_v4",
                    "status": "error",
                    "error": "ODPT_API_KEY not set",
                    "timestamp": int(datetime.now(JST).timestamp()),
                    "total_trains": 0,
                    "positions": [],
                }
            client = app.state.http_client
            schedules = await fetch_trip_updates(client, api_key, data_cache)

        if not schedules:
            return {
                "source": "mock_v4" if time_mgr.is_virtual() else "tripupdate_v4",
                "status": "no_data",
                "timestamp": time_mgr.now() if time_mgr.is_virtual() else int(datetime.now(JST).timestamp()),
                "total_trains": 0,
                "positions": [],
            }

        # 2. MS2: 進捗計算 (タイムトラベル時は仮想時刻を使う)
        mock_now = time_mgr.now() if time_mgr.is_virtual() else None
        results = compute_all_progress(schedules, now_ts=mock_now, data_cache=data_cache)

        # 3. レスポンス構築
        positions = []
        now_ts = None

        for r in results:
            # invalid は除外（デバッグには残したい場合は別途）
            if r.status == "invalid":
                continue

            # MS5: 座標計算（線路形状追従）
            coord = calculate_coordinates(r, data_cache, "JR-East.Yamanote")
            lat = coord[0] if coord else None
            lon = coord[1] if coord else None

            # now_ts を最初の列車から取得
            if now_ts is None:
                now_ts = r.now_ts

            positions.append(
                {
                    "trip_id": r.trip_id,
                    "train_number": r.train_number,
                    "direction": r.direction,
                    "status": r.status,
                    "progress": round(r.progress, 4) if r.progress is not None else None,
                    "delay": r.delay,  # MS6: 遅延秒数
                    "location": {
                        "latitude": round(lat, 6) if lat is not None else None,
                        "longitude": round(lon, 6) if lon is not None else None,
                    },
                    "segment": {
                        "prev_seq": r.prev_seq,
                        "next_seq": r.next_seq,
                        "prev_station_id": r.prev_station_id,
                        "next_station_id": r.next_station_id,
                    },
                    "times": {
                        "now_ts": r.now_ts,
                        "t0_departure": r.t0_departure,
                        "t1_arrival": r.t1_arrival,
                    },
                    "debug": {
                        "feed_timestamp": r.feed_timestamp,
                    },
                }
            )

        # ソート: direction -> train_number
        positions.sort(key=lambda p: (p["direction"] or "", p["train_number"] or ""))

        return {
            "source": "mock_v4" if time_mgr.is_virtual() else "tripupdate_v4",
            "status": "success",
            "timestamp": now_ts or (time_mgr.now() if time_mgr.is_virtual() else int(datetime.now(JST).timestamp())),
            "total_trains": len(positions),
            "positions": positions,
            "time_travel": time_mgr.get_status() if time_mgr.is_virtual() else None,
        }

    except Exception as e:
        logger.error(f"Error in v4 endpoint: {e}")
        return {
            "source": "tripupdate_v4",
            "status": "error",
            "error": str(e),
            "timestamp": int(datetime.now(JST).timestamp()),
            "total_trains": 0,
            "positions": [],
        }


# ============================================================================
# MS10: Multi-Line Generic v4 API
# ============================================================================


@app.get("/api/trains/{line_id}/positions/v4")
async def get_train_positions_v4(line_id: str):
    """
    MS10: 汎用路線の列車位置 v4 API。

    URLパスパラメータから路線を動的に切り替えて列車位置を取得する。

    Args:
        line_id: 路線識別子 ("yamanote", "chuo_rapid", "keihin_tohoku", "sobu_local")
    """
    from gtfs_rt_tripupdate import fetch_trip_updates
    from mock_trip_generator import generate_mock_schedules
    from time_manager import time_mgr
    from train_position_v4 import calculate_coordinates, compute_all_progress

    # 1. 路線設定のロード
    line_config = get_line_config(line_id)
    if not line_config:
        # 利用可能な路線一覧を取得
        from config import SUPPORTED_LINES

        available = ", ".join(sorted(SUPPORTED_LINES.keys())[:10]) + "..."
        raise HTTPException(
            status_code=404, detail=f"Line '{line_id}' is not supported. Available lines: {available} (51 lines total)"
        )

    try:
        # タイムトラベルモード: モックデータを使用
        if time_mgr.is_virtual():
            schedules = generate_mock_schedules(
                data_cache,
                time_mgr.now(),
                target_route_id=line_config.gtfs_route_id,
            )
        else:
            # 実データモード: ODPT API から取得
            api_key = os.getenv("ODPT_API_KEY", "").strip()
            if not api_key:
                return {
                    "source": "tripupdate_v4",
                    "line_id": line_id,
                    "line_name": line_config.name,
                    "status": "error",
                    "error": "ODPT_API_KEY not set",
                    "timestamp": int(datetime.now(JST).timestamp()),
                    "total_trains": 0,
                    "positions": [],
                }
            client = app.state.http_client
            schedules = await fetch_trip_updates(
                client, api_key, data_cache, target_route_id=line_config.gtfs_route_id, mt3d_prefix=line_config.mt3d_id
            )

        if not schedules:
            return {
                "source": "mock_v4" if time_mgr.is_virtual() else "tripupdate_v4",
                "line_id": line_id,
                "line_name": line_config.name,
                "status": "no_data",
                "timestamp": time_mgr.now() if time_mgr.is_virtual() else int(datetime.now(JST).timestamp()),
                "total_trains": 0,
                "positions": [],
            }

        # 3. MS2: 進捗計算 (タイムトラベル時は仮想時刻を使う)
        mock_now = time_mgr.now() if time_mgr.is_virtual() else None
        results = compute_all_progress(schedules, now_ts=mock_now, data_cache=data_cache)

        # 4. レスポンス構築
        positions = []
        now_ts = None

        # デバッグ: direction 分布の統計
        direction_stats = {}
        status_stats = {}

        for r in results:
            # 統計収集（invalidも含む）
            d = r.direction or "None"
            direction_stats[d] = direction_stats.get(d, 0) + 1
            status_stats[r.status] = status_stats.get(r.status, 0) + 1

            if r.status == "invalid":
                continue

            # MS5: 座標計算（線路形状追従）
            coord = calculate_coordinates(r, data_cache, line_config.mt3d_id)
            lat = coord[0] if coord else None
            lon = coord[1] if coord else None
            bearing = coord[2] if coord and len(coord) > 2 else 0.0

            if now_ts is None:
                now_ts = r.now_ts

            positions.append(
                {
                    "trip_id": r.trip_id,
                    "train_number": r.train_number,
                    "direction": r.direction,
                    "status": r.status,
                    "progress": round(r.progress, 4) if r.progress is not None else None,
                    "delay": r.delay,
                    "location": {
                        "latitude": round(lat, 6) if lat is not None else None,
                        "longitude": round(lon, 6) if lon is not None else None,
                        "bearing": round(bearing, 2) if bearing is not None else 0.0,
                    },
                    "segment": {
                        "prev_seq": r.prev_seq,
                        "next_seq": r.next_seq,
                        "prev_station_id": r.prev_station_id,
                        "next_station_id": r.next_station_id,
                    },
                    "times": {
                        "now_ts": r.now_ts,
                        "t0_departure": r.t0_departure,
                        "t1_arrival": r.t1_arrival,
                    },
                    "debug": {
                        "feed_timestamp": r.feed_timestamp,
                    },
                }
            )

        # ソート: direction -> train_number
        positions.sort(key=lambda p: (p["direction"] or "", p["train_number"] or ""))

        return {
            "source": "mock_v4" if time_mgr.is_virtual() else "tripupdate_v4",
            "line_id": line_id,
            "line_name": line_config.name,
            "status": "success",
            "timestamp": now_ts or (time_mgr.now() if time_mgr.is_virtual() else int(datetime.now(JST).timestamp())),
            "total_trains": len(positions),
            "positions": positions,
            "time_travel": time_mgr.get_status() if time_mgr.is_virtual() else None,
            # デバッグ情報
            "debug": {
                "direction_stats": direction_stats,
                "status_stats": status_stats,
                "schedules_count": len(schedules),
            },
        }

    except Exception as e:
        logger.error(f"Error in generic v4 endpoint for {line_id}: {e}")
        return {
            "source": "tripupdate_v4",
            "line_id": line_id,
            "line_name": line_config.name,
            "status": "error",
            "error": str(e),
            "timestamp": int(datetime.now(JST).timestamp()),
            "total_trains": 0,
            "positions": [],
        }


# ============================================================================
# タイムトラベル制御API
# ============================================================================


@app.post("/api/debug/time-travel")
async def set_time_travel(body: dict):
    """
    仮想時刻を設定/解除する。

    リクエスト例:
        {"virtual_time": "2026-02-12T08:30:00+09:00"}  → 仮想時刻に設定
        {"virtual_time": null}                           → リアルタイムに戻す
    """
    from time_manager import time_mgr

    virtual_time = body.get("virtual_time")

    if virtual_time is None:
        time_mgr.reset()
        return {
            "status": "ok",
            "message": "Reset to real time",
            **time_mgr.get_status(),
        }
    else:
        try:
            time_mgr.set_virtual_time(str(virtual_time))
            return {
                "status": "ok",
                "message": f"Virtual time set to {virtual_time}",
                **time_mgr.get_status(),
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/debug/time-status")
async def get_time_status():
    """現在の時間モード（リアルタイム/仮想）を返す"""
    from time_manager import time_mgr

    return time_mgr.get_status()


# ============================================================================
# Route Search API (OTP + Train Position Integration)
# ============================================================================


def _identify_line_from_route_id(route_gtfs_id: str) -> Optional[str]:
    """
    OTPの route.gtfsId から路線IDを特定する。

    Args:
        route_gtfs_id: OTPの route.gtfsId (例: "1:11" または "1:JR-East.Yamanote")

    Returns:
        路線ID (例: "yamanote") または None
    """
    # "FeedId:RouteId" 形式から RouteId を抽出
    if ":" in route_gtfs_id:
        route_id = route_gtfs_id.split(":", 1)[1]
    else:
        route_id = route_gtfs_id

    # 既知の路線IDとのマッピング
    # OTPのGTFSデータでは数字IDが使われる場合がある
    route_to_line = {
        # 数字ID形式 (JR東日本GTFSデータ)
        "10": "yamanote",  # 山手線
        "11": "chuo_rapid",  # 中央線快速
        "12": "sobu_local",  # 中央・総武緩行線
        "22": "keihin_tohoku",  # 京浜東北・根岸線
        # フルID形式 (バックアップ)
        "JR-East.Yamanote": "yamanote",
        "JR-East.ChuoRapid": "chuo_rapid",
        "JR-East.KeihinTohokuNegishi": "keihin_tohoku",
        "JR-East.ChuoSobuLocal": "sobu_local",
    }

    return route_to_line.get(route_id)


def _extract_trip_id_suffix(trip_gtfs_id: str) -> str:
    """
    OTPの trip.gtfsId から trip_id サフィックスを抽出する。

    Args:
        trip_gtfs_id: OTPの trip.gtfsId (例: "1:4201301G")

    Returns:
        trip_id (例: "4201301G")
    """
    if ":" in trip_gtfs_id:
        return trip_gtfs_id.split(":", 1)[1]
    return trip_gtfs_id


async def _get_train_positions_for_lines(
    line_ids: List[str], client: httpx.AsyncClient, api_key: str
) -> Dict[str, Dict]:
    """
    指定された路線の全列車位置を取得し、trip_idでアクセス可能な辞書を返す。

    Returns:
        { "trip_id_suffix": position_dict, ... }
    """
    from gtfs_rt_tripupdate import fetch_trip_updates
    from train_position_v4 import calculate_coordinates, compute_all_progress

    all_positions: Dict[str, Dict] = {}

    for line_id in set(line_ids):  # 重複を除去
        line_config = get_line_config(line_id)
        if not line_config:
            continue

        try:
            schedules = await fetch_trip_updates(
                client, api_key, data_cache, target_route_id=line_config.gtfs_route_id, mt3d_prefix=line_config.mt3d_id
            )

            if not schedules:
                continue

            results = compute_all_progress(schedules, data_cache=data_cache)

            for r in results:
                if r.status == "invalid":
                    continue

                coord = calculate_coordinates(r, data_cache, line_config.mt3d_id)
                lat = coord[0] if coord else None
                lon = coord[1] if coord else None

                all_positions[r.trip_id] = {
                    "status": r.status,
                    "latitude": round(lat, 6) if lat is not None else None,
                    "longitude": round(lon, 6) if lon is not None else None,
                    "delay": r.delay,
                    "progress": round(r.progress, 4) if r.progress is not None else None,
                    "segment": {
                        "prev_station_id": r.prev_station_id,
                        "next_station_id": r.next_station_id,
                    },
                }
        except Exception as e:
            logger.error(f"Failed to get positions for {line_id}: {e}")
            continue

    return all_positions


@app.get("/api/route/search")
async def route_search(
    # 座標指定（駅名指定と排他）
    from_lat: Optional[float] = Query(None, description="出発地の緯度"),
    from_lon: Optional[float] = Query(None, description="出発地の経度"),
    to_lat: Optional[float] = Query(None, description="目的地の緯度"),
    to_lon: Optional[float] = Query(None, description="目的地の経度"),
    # 駅名指定（座標指定と排他）
    from_station: Optional[str] = Query(None, description="出発駅名（日本語または英語）"),
    to_station: Optional[str] = Query(None, description="到着駅名（日本語または英語）"),
    # 共通パラメータ
    date: str = Query(..., description="日付 (YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    time: str = Query(..., description="時刻 (HH:MM)", regex=r"^\d{2}:\d{2}$"),
    arrive_by: bool = Query(False, description="True: 到着時刻指定, False: 出発時刻指定"),
):
    """
    乗換案内検索 + 使用電車の現在位置

    座標または駅名で経路検索を行い、各電車区間について現在位置を付加して返す。

    - 座標指定: from_lat, from_lon, to_lat, to_lon を使用
    - 駅名指定: from_station, to_station を使用
    """
    if otp_search_route is None:
        raise HTTPException(status_code=500, detail="OTP client not available")

    # 駅名から座標を解決
    resolved_from_station = None
    resolved_to_station = None

    if from_station:
        coord = data_cache.get_station_coord_by_name(from_station)
        if coord is None:
            raise HTTPException(status_code=400, detail=f"出発駅 '{from_station}' が見つかりません")
        from_lat, from_lon = coord
        resolved_from_station = from_station

    if to_station:
        coord = data_cache.get_station_coord_by_name(to_station)
        if coord is None:
            raise HTTPException(status_code=400, detail=f"到着駅 '{to_station}' が見つかりません")
        to_lat, to_lon = coord
        resolved_to_station = to_station

    # 座標のバリデーション
    if from_lat is None or from_lon is None:
        raise HTTPException(
            status_code=400,
            detail="出発地が指定されていません。from_lat/from_lon または from_station を指定してください",
        )
    if to_lat is None or to_lon is None:
        raise HTTPException(
            status_code=400, detail="目的地が指定されていません。to_lat/to_lon または to_station を指定してください"
        )

    api_key = os.getenv("ODPT_API_KEY", "").strip()

    try:
        client = app.state.http_client

        # 1. OTP で経路検索
        otp_response = await otp_search_route(client, from_lat, from_lon, to_lat, to_lon, date, time, arrive_by)

        if "errors" in otp_response:
            return {
                "status": "error",
                "error": otp_response["errors"],
                "query": {
                    "from": {"lat": from_lat, "lon": from_lon},
                    "to": {"lat": to_lat, "lon": to_lon},
                    "date": date,
                    "time": time,
                    "arrive_by": arrive_by,
                },
                "itineraries": [],
            }

        # 2. OTP レスポンスをパース
        itineraries = parse_otp_response(otp_response)

        # 2.5. 徒歩のみの経路を除外
        transit_modes_check = {"RAIL", "BUS", "SUBWAY", "TRAM", "FERRY", "CABLE_CAR", "GONDOLA", "FUNICULAR", "TRANSIT"}
        itineraries = [
            itin for itin in itineraries if any(leg.get("mode") in transit_modes_check for leg in itin.get("legs", []))
        ]

        if not itineraries:
            return {
                "status": "no_routes",
                "query": {
                    "from": {"lat": from_lat, "lon": from_lon},
                    "to": {"lat": to_lat, "lon": to_lon},
                    "date": date,
                    "time": time,
                    "arrive_by": arrive_by,
                },
                "itineraries": [],
            }

        # 3. 使用される路線を特定
        transit_modes = {"RAIL", "BUS", "SUBWAY", "TRAM", "FERRY", "CABLE_CAR", "GONDOLA", "FUNICULAR", "TRANSIT"}
        line_ids_needed = set()
        for itin in itineraries:
            for leg in itin.get("legs", []):
                if leg.get("mode") in transit_modes:
                    route_info = leg.get("route", {})
                    if route_info:
                        route_gtfs_id = route_info.get("gtfs_id", "")
                        line_id = _identify_line_from_route_id(route_gtfs_id)
                        if line_id:
                            line_ids_needed.add(line_id)

        # 4. 必要な路線の列車位置を取得
        train_positions = {}
        if api_key and line_ids_needed:
            train_positions = await _get_train_positions_for_lines(list(line_ids_needed), client, api_key)

        # 5. 各 leg に現在位置情報を付加
        for itin in itineraries:
            for leg in itin.get("legs", []):
                if leg.get("mode") in transit_modes:
                    trip_gtfs_id = leg.get("trip_id", "")
                    trip_id_suffix = _extract_trip_id_suffix(trip_gtfs_id)

                    position = train_positions.get(trip_id_suffix)
                    if position:
                        leg["current_position"] = position
                    else:
                        leg["current_position"] = None

        # クエリ情報を構築
        query_info = {
            "from": {"lat": from_lat, "lon": from_lon},
            "to": {"lat": to_lat, "lon": to_lon},
            "date": date,
            "time": time,
            "arrive_by": arrive_by,
        }
        # 駅名で検索した場合は駅名も含める
        if resolved_from_station:
            query_info["from"]["station"] = resolved_from_station
        if resolved_to_station:
            query_info["to"]["station"] = resolved_to_station

        return {"status": "success", "query": query_info, "itineraries": itineraries}

    except Exception as e:
        logger.error(f"Route search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
