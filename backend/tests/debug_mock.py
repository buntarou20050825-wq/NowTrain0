import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from datetime import datetime
from zoneinfo import ZoneInfo
JST = ZoneInfo("Asia/Tokyo")

print("=== Step 1: TimeManager ===")
try:
    from time_manager import TimeManager
    tm = TimeManager()
    tm.set_virtual_time("2026-02-12T08:30:00+09:00")
    print("  Virtual:", tm.is_virtual(), "now:", tm.now_datetime().isoformat())
    tm.reset()
    print("  Reset OK:", not tm.is_virtual())
    print("  PASS")
except Exception:
    traceback.print_exc()

print()
print("=== Step 2: MockGenerator ===")
schedules = None
vt = None
try:
    from timetable_models import TimetableTrain, StopTime
    from mock_trip_generator import generate_mock_schedules

    train = TimetableTrain(
        base_id="test", service_type="Weekday",
        line_id="JR-East.Yamanote", number="400G",
        train_type="Local", direction="OuterLoop",
        origin_stations=[], destination_stations=[],
        stops=[
            StopTime("JR-East.Yamanote.Osaki", 30600, 30620),
            StopTime("JR-East.Yamanote.Gotanda", 30740, 30760),
            StopTime("JR-East.Yamanote.Meguro", 30880, 30900),
        ],
    )

    class MockCache:
        all_trains = [train]

    dt = datetime(2026, 2, 12, 8, 31, 0, tzinfo=JST)
    vt = int(dt.timestamp())
    schedules = generate_mock_schedules(MockCache(), vt)
    print("  Schedules:", len(schedules))
    for tid, s in schedules.items():
        print("  ", tid, "seqs=", len(s.ordered_sequences))
    print("  PASS")
except Exception:
    traceback.print_exc()

print()
print("=== Step 3: Physics ===")
try:
    if schedules and vt:
        from train_position_v4 import compute_progress_for_train
        for tid, sched in schedules.items():
            result = compute_progress_for_train(sched, now_ts=vt)
            print("  status:", result.status, "progress:", result.progress)
            print("  prev:", result.prev_station_id, "next:", result.next_station_id)
        print("  PASS")
    else:
        print("  SKIP (no schedules)")
except Exception:
    traceback.print_exc()

print()
print("=== Step 4: Midnight ===")
try:
    dt2 = datetime(2026, 2, 12, 2, 0, 0, tzinfo=JST)
    vt2 = int(dt2.timestamp())

    class MockCache2:
        all_trains = [train]

    s2 = generate_mock_schedules(MockCache2(), vt2)
    print("  Midnight schedules:", len(s2), "(expect 0)")
    print("  PASS")
except Exception:
    traceback.print_exc()

print()
print("=== ALL DONE ===")
