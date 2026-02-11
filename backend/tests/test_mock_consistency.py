# backend/tests/test_mock_consistency.py
"""
タイムトラベル型モックデータ供給エンジン: 整合性テスト

静的時刻表から生成されたモックデータが、既存の物理演算パイプラインを
正しく通過できるかを検証する。
"""
import sys
import os
import unittest
from datetime import datetime

# backendをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zoneinfo import ZoneInfo
from time_manager import TimeManager
from train_state import determine_service_type, get_service_date

JST = ZoneInfo("Asia/Tokyo")


class TestTimeManager(unittest.TestCase):
    """TimeManager の基本動作テスト"""

    def setUp(self):
        self.tm = TimeManager()

    def test_initial_state(self):
        """初期状態はリアルタイムモード"""
        self.assertFalse(self.tm.is_virtual())
        status = self.tm.get_status()
        self.assertEqual(status["mode"], "realtime")
        self.assertEqual(status["offset_sec"], 0)
        print("--- TimeManager: initial state OK ---")

    def test_set_virtual_time(self):
        """仮想時刻を設定するとオフセットが適用される"""
        self.tm.set_virtual_time("2026-02-12T08:30:00+09:00")
        self.assertTrue(self.tm.is_virtual())

        now_dt = self.tm.now_datetime()
        # 仮想時刻が 8:30 の近辺であること確認
        self.assertEqual(now_dt.hour, 8)
        self.assertAlmostEqual(now_dt.minute, 30, delta=1)
        print(f"--- TimeManager: virtual time = {now_dt.isoformat()} ---")

    def test_reset(self):
        """reset() でリアルタイムに戻る"""
        self.tm.set_virtual_time("2026-02-12T12:00:00+09:00")
        self.assertTrue(self.tm.is_virtual())

        self.tm.reset()
        self.assertFalse(self.tm.is_virtual())
        self.assertEqual(self.tm.get_status()["mode"], "realtime")
        print("--- TimeManager: reset OK ---")


class TestMockGenerator(unittest.TestCase):
    """モックデータ生成のテスト（DataCache の all_trains を模擬）"""

    def _make_minimal_data_cache(self):
        """テスト用の簡易 DataCache モック"""
        from timetable_models import TimetableTrain, StopTime

        # 山手線の列車 1本（平日、3駅）
        train = TimetableTrain(
            base_id="JR-East.Yamanote.400G",
            service_type="Weekday",
            line_id="JR-East.Yamanote",
            number="400G",
            train_type="JR-East.Local",
            direction="OuterLoop",
            origin_stations=["JR-East.Yamanote.Osaki"],
            destination_stations=["JR-East.Yamanote.Shibuya"],
            stops=[
                StopTime(
                    station_id="JR-East.Yamanote.Osaki",
                    arrival_sec=30600,     # 08:30:00
                    departure_sec=30620,   # 08:30:20
                ),
                StopTime(
                    station_id="JR-East.Yamanote.Gotanda",
                    arrival_sec=30740,     # 08:32:20
                    departure_sec=30760,   # 08:32:40
                ),
                StopTime(
                    station_id="JR-East.Yamanote.Meguro",
                    arrival_sec=30880,     # 08:34:40
                    departure_sec=30900,   # 08:35:00
                ),
            ],
        )

        # DataCache のモック
        class MockDataCache:
            all_trains = [train]

        return MockDataCache()

    def test_generate_basic(self):
        """仮想時刻での基本的なモック生成"""
        from mock_trip_generator import generate_mock_schedules

        cache = self._make_minimal_data_cache()
        # 2026年2月12日は木曜日 → Weekday
        dt = datetime(2026, 2, 12, 8, 31, 0, tzinfo=JST)
        virtual_now = int(dt.timestamp())

        schedules = generate_mock_schedules(cache, virtual_now)

        self.assertGreater(len(schedules), 0, "Weekday 08:31 should find active trains")

        for trip_id, sched in schedules.items():
            self.assertGreaterEqual(len(sched.ordered_sequences), 2)
            self.assertIsNotNone(sched.feed_timestamp)
            print(f"  trip_id={trip_id}, stops={len(sched.ordered_sequences)}, dir={sched.direction}")

        print(f"--- MockGenerator: generated {len(schedules)} schedules for 08:31 ---")

    def test_generate_midnight(self):
        """深夜2時は列車なし（正しく0件を返す）"""
        from mock_trip_generator import generate_mock_schedules

        cache = self._make_minimal_data_cache()
        dt = datetime(2026, 2, 12, 2, 0, 0, tzinfo=JST)
        virtual_now = int(dt.timestamp())

        schedules = generate_mock_schedules(cache, virtual_now)
        self.assertEqual(len(schedules), 0, "深夜2時は列車なしのはず")
        print("--- MockGenerator: midnight = 0 trains (correct) ---")

    def test_schedule_passes_physics(self):
        """生成された TrainSchedule が compute_progress_for_train を通過する"""
        from mock_trip_generator import generate_mock_schedules
        from train_position_v4 import compute_progress_for_train

        cache = self._make_minimal_data_cache()
        dt = datetime(2026, 2, 12, 8, 31, 0, tzinfo=JST)
        virtual_now = int(dt.timestamp())

        schedules = generate_mock_schedules(cache, virtual_now)
        self.assertGreater(len(schedules), 0)

        for trip_id, sched in schedules.items():
            result = compute_progress_for_train(sched, now_ts=virtual_now)

            self.assertIn(result.status, ("running", "stopped", "unknown"),
                          f"Status should be valid, got '{result.status}' for {trip_id}")

            # invalid でないことを確認
            self.assertNotEqual(result.status, "invalid",
                                f"TrainSchedule for {trip_id} should not be invalid")

            print(
                f"  {trip_id}: status={result.status}, "
                f"progress={result.progress}, "
                f"prev={result.prev_station_id}, next={result.next_station_id}"
            )

        print("--- Physics pipeline: all schedules passed ---")

    def test_time_consistency(self):
        """生成データの時刻整合性をチェック（arr < dep < next_arr）"""
        from mock_trip_generator import generate_mock_schedules

        cache = self._make_minimal_data_cache()
        dt = datetime(2026, 2, 12, 8, 31, 0, tzinfo=JST)
        virtual_now = int(dt.timestamp())

        schedules = generate_mock_schedules(cache, virtual_now)
        self.assertGreater(len(schedules), 0)

        for trip_id, sched in schedules.items():
            seqs = sched.ordered_sequences
            prev_dep = None
            for seq in seqs:
                stu = sched.schedules_by_seq[seq]

                # arrival <= departure
                if stu.arrival_time is not None and stu.departure_time is not None:
                    self.assertLessEqual(
                        stu.arrival_time, stu.departure_time,
                        f"{trip_id} seq={seq}: arrival > departure"
                    )

                # prev_departure <= current_arrival (monotonic)
                arr = stu.arrival_time or stu.departure_time
                if prev_dep is not None and arr is not None:
                    self.assertLessEqual(
                        prev_dep, arr,
                        f"{trip_id} seq={seq}: non-monotonic times"
                    )

                prev_dep = stu.departure_time or stu.arrival_time

        print("--- Time consistency check: PASSED ---")


class TestServiceTypeDetection(unittest.TestCase):
    """サービスタイプ判定のテスト"""

    def test_weekday(self):
        # 2026-02-12 は木曜日
        dt = datetime(2026, 2, 12, 10, 0, tzinfo=JST)
        self.assertEqual(determine_service_type(dt), "Weekday")

    def test_saturday(self):
        # 2026-02-14 は土曜日
        dt = datetime(2026, 2, 14, 10, 0, tzinfo=JST)
        self.assertEqual(determine_service_type(dt), "SaturdayHoliday")

    def test_midnight_belongs_to_previous_day(self):
        # 2026-02-13 02:00 → サービス日は 2026-02-12
        dt = datetime(2026, 2, 13, 2, 0, tzinfo=JST)
        svc_date = get_service_date(dt)
        self.assertEqual(svc_date.day, 12, "深夜2時は前日のサービス日")
        print(f"--- Service day for 02:00: {svc_date} (correct: 12th) ---")


if __name__ == "__main__":
    unittest.main()
