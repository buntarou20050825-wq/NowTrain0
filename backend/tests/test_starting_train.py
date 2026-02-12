
import unittest
from datetime import datetime, timedelta
import sys
import os

# パスを通す
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from train_position_v4 import compute_progress_for_train, SegmentProgress
from gtfs_rt_tripupdate import TrainSchedule, RealtimeStationSchedule

class TestStartingTrain(unittest.TestCase):
    def test_starting_train_detection(self):
        """
        始発駅で出発待ちの列車が正しく 'stopped' として検出されるかテスト
        """
        # 現在時刻: 10:00:00
        now_ts = datetime(2024, 1, 1, 10, 0, 0).timestamp()
        
        # 列車: 10:02:00 発 (2分後)
        dep_ts = datetime(2024, 1, 1, 10, 2, 0).timestamp()
        
        # 始発駅のみのスケジュール（次の駅などの情報は最低限あればよい）
        # GTFS-RT TripUpdate では始発駅は departure のみで arrival がないことが多い
        schedules = {
            1: RealtimeStationSchedule(
                stop_sequence=1,
                station_id="StationA",
                arrival_time=None,  # 始発なのでNone
                departure_time=int(dep_ts),
                resolved=True,
                raw_stop_id="A",
                delay=0
            ),
            2: RealtimeStationSchedule(
                stop_sequence=2,
                station_id="StationB",
                arrival_time=int(dep_ts + 300),
                departure_time=int(dep_ts + 360),
                resolved=True,
                raw_stop_id="B",
                delay=0
            )
        }
        
        train_schedule = TrainSchedule(
            trip_id="test_trip",
            train_number="1000G",
            start_date="20240101",
            direction="Outbound",
            feed_timestamp=int(now_ts),
            schedules_by_seq=schedules,
            ordered_sequences=[1, 2]
        )
        
        # 計算実行
        result = compute_progress_for_train(train_schedule, now_ts=int(now_ts))
        
        print(f"\nResult Status: {result.status}")
        print(f"Result Progress: {result.progress}")
        
        # 検証
        # 現状のバグでは 'unknown' になるはずだが、理想は 'stopped'
        self.assertEqual(result.status, "stopped", f"Expected 'stopped' but got '{result.status}'")
        self.assertIsNotNone(result.progress)
        self.assertEqual(result.progress, 0.0)
        self.assertEqual(result.prev_station_id, "StationA")

if __name__ == "__main__":
    unittest.main()
