# backend/mock_trip_generator.py
"""
タイムトラベル型モックデータ供給エンジン: TripUpdate 生成モジュール

静的時刻表 (TimetableTrain) から TrainSchedule を生成し、
fetch_trip_updates() の代替として機能する。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional
from zoneinfo import ZoneInfo

from gtfs_rt_tripupdate import RealtimeStationSchedule, TrainSchedule
from timetable_models import StopTime, TimetableTrain
from train_state import determine_service_type, get_service_date

if TYPE_CHECKING:
    from data_cache import DataCache

logger = logging.getLogger(__name__)
JST = ZoneInfo("Asia/Tokyo")


def _get_midnight_unix(virtual_now_ts: int) -> int:
    """
    仮想時刻の「サービス日 00:00:00 JST」の Unix タイムスタンプを返す。

    サービス日のルール:
      04:00〜翌03:59 が同一サービス日。
      深夜 0:00〜3:59 は前日のサービス日に属する。
    """
    dt = datetime.fromtimestamp(virtual_now_ts, tz=JST)
    svc_date = get_service_date(dt)
    midnight = datetime(svc_date.year, svc_date.month, svc_date.day, 0, 0, 0, tzinfo=JST)
    return int(midnight.timestamp())


def _is_train_active(
    train: TimetableTrain,
    virtual_now_ts: int,
    midnight_unix: int,
    window_sec: int,
) -> bool:
    """
    指定列車が仮想時刻の前後 window_sec の間に運行しているか判定する。
    """
    stops = train.stops
    if len(stops) < 2:
        return False

    # 列車の最初の出発時刻と最後の到着時刻を取得
    first_dep = None
    for s in stops:
        t = s.departure_sec if s.departure_sec is not None else s.arrival_sec
        if t is not None:
            first_dep = midnight_unix + t
            break

    last_arr = None
    for s in reversed(stops):
        t = s.arrival_sec if s.arrival_sec is not None else s.departure_sec
        if t is not None:
            last_arr = midnight_unix + t
            break

    if first_dep is None or last_arr is None:
        return False

    # 列車の運行時間帯が、仮想時刻 ± window のウィンドウと重なるか
    window_start = virtual_now_ts - window_sec
    window_end = virtual_now_ts + window_sec

    return not (last_arr < window_start or first_dep > window_end)


def _timetable_to_train_schedule(
    train: TimetableTrain,
    midnight_unix: int,
    virtual_now_ts: int,
) -> TrainSchedule:
    """
    TimetableTrain を TrainSchedule に変換する。

    StopTime.arrival_sec / departure_sec (0時からの秒数) を
    midnight_unix + sec で Unix タイムスタンプに変換する。
    """
    schedules_by_seq: Dict[int, RealtimeStationSchedule] = {}
    ordered_sequences: List[int] = []

    for seq_idx, stop in enumerate(train.stops):
        seq = seq_idx + 1  # 1-based stop_sequence

        arr_unix = None
        dep_unix = None

        if stop.arrival_sec is not None:
            arr_unix = midnight_unix + stop.arrival_sec
        if stop.departure_sec is not None:
            dep_unix = midnight_unix + stop.departure_sec

        # arrival も departure も None なら停車情報として意味がないのでスキップ
        if arr_unix is None and dep_unix is None:
            continue

        rss = RealtimeStationSchedule(
            stop_sequence=seq,
            station_id=stop.station_id,
            arrival_time=arr_unix,
            departure_time=dep_unix,
            resolved=True,  # 静的時刻表なので常に解決済み
            raw_stop_id=None,
            delay=0,  # モックは定刻運行
        )

        schedules_by_seq[seq] = rss
        ordered_sequences.append(seq)

    # trip_id を一意に生成: "mock_{line_id}_{number}_{service_type}"
    trip_id = f"mock_{train.line_id}.{train.number}.{train.service_type}"

    return TrainSchedule(
        trip_id=trip_id,
        train_number=train.number,
        start_date=None,
        direction=train.direction,
        feed_timestamp=virtual_now_ts,  # モックの feed_timestamp は仮想時刻
        schedules_by_seq=schedules_by_seq,
        ordered_sequences=ordered_sequences,
    )


def generate_mock_schedules(
    data_cache: "DataCache",
    virtual_now_ts: int,
    target_route_id: Optional[str] = None,
    window_minutes: int = 30,
) -> Dict[str, TrainSchedule]:
    """
    静的時刻表から、仮想時刻における TrainSchedule の辞書を生成する。

    fetch_trip_updates() と同じインターフェースの戻り値を返すので、
    そのまま compute_all_progress() に渡せる。

    Args:
        data_cache: DataCache （all_trains が読み込み済み）
        virtual_now_ts: 仮想時刻 (Unix 秒)
        target_route_id: 特定路線に絞る (例: "JR-East.Yamanote")。None なら全路線。
        window_minutes: 列車を含めるウィンドウ幅（前後N分）

    Returns:
        {trip_id: TrainSchedule} の辞書
    """
    dt = datetime.fromtimestamp(virtual_now_ts, tz=JST)
    service_type = determine_service_type(dt)
    midnight_unix = _get_midnight_unix(virtual_now_ts)
    window_sec = window_minutes * 60

    result: Dict[str, TrainSchedule] = {}
    filtered_count = 0
    active_count = 0

    for train in data_cache.all_trains:
        # 1. service_type フィルタ
        st = train.service_type or ""
        if st not in ("Weekday", "SaturdayHoliday"):
            continue
        if st != service_type:
            continue

        # 2. 路線フィルタ（指定時のみ）
        if target_route_id and train.line_id != target_route_id:
            continue

        filtered_count += 1

        # 3. 時間ウィンドウ内の列車のみ
        if not _is_train_active(train, virtual_now_ts, midnight_unix, window_sec):
            continue

        # 4. TrainSchedule に変換
        schedule = _timetable_to_train_schedule(train, midnight_unix, virtual_now_ts)

        # 有効な駅が2つ未満なら無視
        if len(schedule.ordered_sequences) < 2:
            continue

        result[schedule.trip_id] = schedule
        active_count += 1

    logger.info(
        "MockGenerator: service=%s, route=%s, candidates=%d, active=%d (window=±%dmin)",
        service_type,
        target_route_id or "ALL",
        filtered_count,
        active_count,
        window_minutes,
    )

    return result
