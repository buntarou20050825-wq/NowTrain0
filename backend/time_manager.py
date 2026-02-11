# backend/time_manager.py
"""
タイムトラベル型モックデータ供給エンジン: 時間管理モジュール

システム全体の「現在時刻」を仮想時刻に差し替えるシングルトン。
環境変数 VIRTUAL_TIME で起動時に設定可能。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
JST = ZoneInfo("Asia/Tokyo")


class TimeManager:
    """仮想時刻管理シングルトン"""

    def __init__(self) -> None:
        self._offset_sec: int = 0  # real time からのオフセット（秒）
        self._virtual: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def now(self) -> int:
        """現在時刻を Unix 秒で返す（仮想時刻が有効ならオフセット適用）"""
        return int(time.time()) + self._offset_sec

    def now_datetime(self) -> datetime:
        """現在時刻を JST datetime で返す"""
        return datetime.fromtimestamp(self.now(), tz=JST)

    def is_virtual(self) -> bool:
        """仮想時刻モードかどうか"""
        return self._virtual

    def set_virtual_time(self, iso_str: str) -> None:
        """
        仮想時刻を ISO 8601 文字列で設定する。

        例: "2026-02-12T08:30:00+09:00"
        """
        try:
            target_dt = datetime.fromisoformat(iso_str)
            if target_dt.tzinfo is None:
                target_dt = target_dt.replace(tzinfo=JST)

            target_ts = int(target_dt.timestamp())
            real_now = int(time.time())
            self._offset_sec = target_ts - real_now
            self._virtual = True

            logger.info(
                "TimeManager: virtual time set to %s (offset=%+d sec)",
                target_dt.isoformat(),
                self._offset_sec,
            )
        except Exception as e:
            logger.error("TimeManager: failed to parse '%s': %s", iso_str, e)
            raise ValueError(f"Invalid ISO time string: {iso_str}") from e

    def set_offset(self, offset_sec: int) -> None:
        """オフセット値を直接設定する"""
        self._offset_sec = offset_sec
        self._virtual = offset_sec != 0
        logger.info("TimeManager: offset set to %+d sec", offset_sec)

    def reset(self) -> None:
        """リアルタイムに戻す"""
        self._offset_sec = 0
        self._virtual = False
        logger.info("TimeManager: reset to real time")

    def get_status(self) -> dict:
        """現在の状態を辞書で返す（デバッグ/API用）"""
        now_dt = self.now_datetime()
        return {
            "mode": "virtual" if self._virtual else "realtime",
            "virtual_now": now_dt.isoformat(),
            "offset_sec": self._offset_sec,
            "real_now": datetime.now(JST).isoformat(),
        }


# グローバル・シングルトン
time_mgr = TimeManager()
