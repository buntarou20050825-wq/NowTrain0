import urllib.request
import json

def fetch(url):
    r = urllib.request.urlopen(url)
    return json.loads(r.read())

print("=== Time Status ===")
status = fetch("http://localhost:8000/api/debug/time-status")
print(json.dumps(status, indent=2))

print()
print("=== Yamanote v4 (mock) ===")
data = fetch("http://localhost:8000/api/trains/yamanote/positions/v4")
print(f"source: {data.get('source')}")
print(f"total_trains: {data.get('total_trains')}")
tt = data.get("time_travel")
if tt:
    print(f"time_travel.mode: {tt.get('mode')}")
    print(f"time_travel.virtual_now: {tt.get('virtual_now')}")

positions = data.get("positions", [])
print(f"\nFirst 10 positions:")
for p in positions[:10]:
    loc = p.get("location", {})
    print(
        f"  {p.get('train_number','?'):>6s} "
        f"{p.get('direction','?'):>12s} "
        f"{p.get('status','?'):>8s} "
        f"prog={p.get('progress')} "
        f"lat={loc.get('latitude')} lon={loc.get('longitude')}"
    )
if len(positions) > 10:
    print(f"  ... ({len(positions)} total)")

print()
print("=== Chuo Rapid v4 (mock) ===")
data2 = fetch("http://localhost:8000/api/trains/chuo_rapid/positions/v4")
print(f"source: {data2.get('source')}")
print(f"total_trains: {data2.get('total_trains')}")
for p in data2.get("positions", [])[:5]:
    loc = p.get("location", {})
    print(
        f"  {p.get('train_number','?'):>6s} "
        f"{p.get('direction','?'):>12s} "
        f"{p.get('status','?'):>8s} "
        f"prog={p.get('progress')} "
        f"lat={loc.get('latitude')} lon={loc.get('longitude')}"
    )

print()
print("=== DONE ===")
