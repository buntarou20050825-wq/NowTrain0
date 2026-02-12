
import asyncio
import os
import logging
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2
import httpx

from pathlib import Path
from datetime import datetime
from data_cache import DataCache

# Import your modules
# Assuming running from backend/ directory
import sys
sys.path.append(".")
from gtfs_rt_vehicle import fetch_vehicle_positions
from gtfs_rt_tripupdate import fetch_trip_updates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize real DataCache
BASE_DIR = Path(__file__).resolve().parent.parent # NowTrain-v2/
DATA_DIR = BASE_DIR / "data"
data_cache = DataCache(DATA_DIR)

async def main():
    load_dotenv()
    api_key = os.getenv("ODPT_API_KEY")
    if not api_key:
        print("Error: ODPT_API_KEY not found")
        return

    target_route_id = "JR-East.Yokohama"
    # User said 1630K, but internally it might be 1630K or 1630K:1 or similar. 
    # Let's search for "1630K" substring.
    target_train_number = "1630K"

    print(f"Fetching data for {target_route_id}...")
    
    # Client setup
    async with httpx.AsyncClient() as client:
        # Fetch TripUpdates
        print("Fetching TripUpdates...")
        schedules = await fetch_trip_updates(
            client, 
            api_key, 
            data_cache, 
            target_route_id=target_route_id,
            mt3d_prefix="JR-East.Yokohama"
        )
        
        # Fetch VehiclePositions
        print("Fetching VehiclePositions...")
        vehicle_positions = await fetch_vehicle_positions(api_key, target_route_id=target_route_id)


    # Analyze TripUpdates
    print(f"\n--- TripUpdates ({len(schedules)} trains) ---")
    target_schedule = None
    
    # Debug: Print all train numbers to find the right one
    print("Listing all trains found in TripUpdates:")
    for trip_id, schedule in schedules.items():
        t_num = schedule.train_number
        if "1630K" in t_num or "1630K" in trip_id:
            print(f"MATCH FOUND! TripID: {trip_id}, TrainNum: {t_num}")
            target_schedule = schedule
            target_train_number = t_num # Update target to specific found number/id
        
    if target_schedule:
        print(f"\nTarget Schedule Details for {target_schedule.train_number}:")
        print(f"  Trip ID: {target_schedule.trip_id}")
        if target_schedule.ordered_sequences:
            first_seq = target_schedule.ordered_sequences[0]
            first = target_schedule.schedules_by_seq[first_seq]
            print(f"  First Stop: {first.station_id} (Seq: {first.stop_sequence})")
            print(f"    Arr: {first.arrival_time}")
            print(f"    Dep: {first.departure_time}")
    else:
        print("\nTarget train 1630K NOT FOUND in TripUpdates. Listing ALL trains:")
        for trip_id, s in schedules.items():
            print(f"  {trip_id} : {s.train_number}")
            
    # Check for Hachioji (JH32) departures
    print("\n--- Trains at Hachioji (JH32) ---")
    current_time = datetime.now() # rough check
    print(f"Current System Time: {current_time}")

    for trip_id, s in schedules.items():
        # iterate sorted schedules
        for seq in s.ordered_sequences:
            stop = s.schedules_by_seq[seq]
            # Hachioji station ID might vary (JH32, or others). Searching for 'Hachioji' or 'JH32'.
            if stop.station_id == "JH32": 
                # Check for 16:47 (around 16:47)
                dep_ts = stop.departure_time or stop.arrival_time
                if not dep_ts: continue
                
                dep_dt = datetime.fromtimestamp(dep_ts)
                # Format to HH:MM
                dep_str = dep_dt.strftime("%H:%M")
                
                # Check if it's within range (e.g. 16:30 - 17:00)
                # Just print all Hachioji departures for today/now to be sure
                print(f"Train {s.train_number} ({trip_id}) at JH32: {dep_str}")

    # Analyze VehiclePositions
    print(f"\n--- VehiclePositions ({len(vehicle_positions)} trains) ---")
    target_vp = None
    for vp in vehicle_positions:
        # Check if trip_id matches or if train_number matches (if available)
        if target_train_number in vp.trip_id:
            print(f"FOUND VP: {vp.trip_id}")
            print(f"  Status: {vp.status} (STOPPED_AT=1)")
            print(f"  Stop Seq: {vp.stop_sequence}")
            # print(f"  Station ID: {vp.station_id}") # Not available in YamanoteTrainPosition
            print(f"  Timestamp: {vp.timestamp}")
            target_vp = vp

    print(f"\n--- Analysis for 1630K ---")
    if target_schedule and target_vp:
        print(f"Schedule TripID: '{target_schedule.trip_id}'")
        print(f"VP TripID:       '{target_vp.trip_id}'")
        
        if target_schedule.trip_id == target_vp.trip_id:
            print("  IDs MATCH PERFECTLY.")
        else:
            print("  IDs DO NOT MATCH!")
            
        # Check sequences
        print(f"VP Stop Seq: {target_vp.stop_sequence}")
        print(f"Schedule Keys: {sorted(list(target_schedule.schedules_by_seq.keys()))}")
        
        # Simulate logic check
        origin_seq = target_vp.stop_sequence if target_vp.stop_sequence > 0 else 1
        origin_stu = target_schedule.schedules_by_seq.get(origin_seq)
        if origin_stu:
            print(f"  Origin Schedule Found for Seq {origin_seq}. Override should work.")
        else:
            print(f"  Origin Schedule NOT FOUND for Seq {origin_seq}.")
    else:
        print("  Missing Schedule or VP for 1630K.")
    
    if not target_schedule:
        print(f"\nWARNING: Schedule for {target_train_number} NOT FOUND.")
    
    if not target_vp:
        print(f"\nWARNING: VehiclePosition for {target_train_number} NOT FOUND.")
        # Print all VPs to see if we missed it due to ID mismatch
        print("Dumping all VP trip_ids:")
        for vp in vehicle_positions:
            print(f"  - {vp.trip_id}")
    else:
        print("\nVP Found!")

if __name__ == "__main__":
    asyncio.run(main())
