import time
import unittest

from gtfs_rt_tripupdate import RealtimeStationSchedule, TrainSchedule
from gtfs_rt_vehicle import YamanoteTrainPosition
from train_position_v4 import SegmentProgress, compute_progress_for_train


class TestOriginLogic(unittest.TestCase):
    def test_future_departure_with_vehicle_position(self):
        # 1. Setup Mock Schedule (Departure in 30 mins)
        now_ts = int(time.time())
        future_dep = now_ts + 1800  # 30 mins later

        schedule = TrainSchedule(
            trip_id="test_trip",
            train_number="1234G",
            start_date="20240101",
            direction="OuterLoop",
            feed_timestamp=now_ts,
            ordered_sequences=[1, 2],
            schedules_by_seq={
                1: RealtimeStationSchedule(
                    stop_sequence=1,
                    station_id="OriginSt",
                    arrival_time=None,
                    departure_time=future_dep,
                    resolved=True,
                    raw_stop_id="OriginSt",
                ),
                2: RealtimeStationSchedule(
                    stop_sequence=2,
                    station_id="NextSt",
                    arrival_time=future_dep + 300,
                    departure_time=future_dep + 360,
                    resolved=True,
                    raw_stop_id="NextSt",
                ),
            },
        )

        # 2. Case A: No VehiclePosition -> TripUpdate-only origin detection
        # MS14: バッファが30分に拡大されたため、30分前でも stopped として検出される
        result_no_vp = compute_progress_for_train(schedule, now_ts=now_ts)
        self.assertEqual(result_no_vp.status, "stopped")
        self.assertTrue(result_no_vp.is_starting_station)
        self.assertEqual(result_no_vp.prev_station_id, "OriginSt")

        # 3. Case B: With VehiclePosition at Origin
        vp = YamanoteTrainPosition(
            trip_id="test_trip",
            train_number="1234G",
            direction="OuterLoop",
            latitude=35.0,
            longitude=139.0,
            stop_sequence=1,
            status=1,  # STOPPED_AT
            timestamp=now_ts,
        )

        result_with_vp = compute_progress_for_train(schedule, now_ts=now_ts, vehicle_position=vp)

        self.assertEqual(result_with_vp.status, "stopped")
        self.assertEqual(result_with_vp.prev_station_id, "OriginSt")
        self.assertTrue(result_with_vp.is_starting_station)
        print("Success: Future train with VP is detected as stopped at origin.")

    def test_outside_buffer_returns_unknown(self):
        """バッファ外（45分前）の始発列車は unknown になること"""
        now_ts = int(time.time())
        future_dep = now_ts + 2700  # 45 mins later (> 30 min buffer)

        schedule = TrainSchedule(
            trip_id="test_trip_far",
            train_number="5678G",
            start_date="20240101",
            direction="OuterLoop",
            feed_timestamp=now_ts,
            ordered_sequences=[1, 2],
            schedules_by_seq={
                1: RealtimeStationSchedule(
                    stop_sequence=1,
                    station_id="OriginSt",
                    arrival_time=None,
                    departure_time=future_dep,
                    resolved=True,
                    raw_stop_id="OriginSt",
                ),
                2: RealtimeStationSchedule(
                    stop_sequence=2,
                    station_id="NextSt",
                    arrival_time=future_dep + 300,
                    departure_time=future_dep + 360,
                    resolved=True,
                    raw_stop_id="NextSt",
                ),
            },
        )

        result = compute_progress_for_train(schedule, now_ts=now_ts)
        self.assertNotEqual(result.status, "stopped")
        self.assertIn(result.status, ("unknown",))
        print("Success: Train 45 mins before departure is unknown (outside buffer).")


if __name__ == "__main__":
    unittest.main()
