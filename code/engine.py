import asyncio
import sqlite3
import sys
import time
import yaml

from gmqtt import Client
from room import Room
from db_manager import DBManager


def load_config(path="config.yaml"):
    """Load configuration from YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def create_rooms(db_manager, config, heartbeat_tracker):
    """Instantiate Room objects from persisted DB state."""
    rooms = []
    states = db_manager.load_state()

    for rid, state in states.items():
        parts = rid.split("-")
        building = parts[0][1:]          # "01"
        floor    = int(parts[1][1:])     # 5
        room_num = int(parts[2][1:])     # 502

        init_state = {
            "temperature": state["last_temp"],
            "humidity":    state["last_humidity"],
            "occupancy":   False,
            "light_level": 100,
            "hvac_mode":   state["hvac_mode"],
        }

        rooms.append(
            Room(building, room_num, floor, init_state, db_manager, config, heartbeat_tracker)
        )

    return rooms


#  MQTT callbacks


def on_connect(client, flags, rc, properties):
    print("[MQTT] Connected to broker")


def on_disconnect(client, packet, exc=None):
    if exc:
        print(f"[MQTT] Disconnected with error: {exc} — waiting for auto-reconnect...")
    else:
        print("[MQTT] Disconnected cleanly — waiting for auto-reconnect...")


# Heartbeat monitor 

async def check_heartbeats(heartbeat_tracker, timeout):
    """Periodically scan the heartbeat tracker and warn about silent rooms."""
    while True:
        await asyncio.sleep(10)
        now = time.time()
        for room_id, last_seen in heartbeat_tracker.items():
            if now - last_seen > timeout:
                print(f"[WARNING] {room_id} is OFFLINE (last seen {int(now - last_seen)}s ago)")



async def main():
    config = load_config("config.yaml")

   
    db = DBManager(config)
    db.start_background_sync(sync_interval=30)

   
    heartbeat_tracker = {}

    
    broker = config.get("broker", "broker.hivemq.com")
    port   = config.get("port", 1883)

    client = Client("world-engine")
    client.set_config({"reconnect_retries": -1})   
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect

    await client.connect(broker, port=port)

    
    rooms = create_rooms(db, config, heartbeat_tracker)
    print(f"[ENGINE] {len(rooms)} rooms loaded")

   
    timeout = config.get("heartbeat_timeout", 60)
    tasks = [asyncio.create_task(room.run_simulation(client)) for room in rooms]
    tasks.append(asyncio.create_task(check_heartbeats(heartbeat_tracker, timeout)))

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except KeyboardInterrupt:
        pass
    finally:
        
        print("\n[SHUTDOWN] Flushing DB state...")
        try:
            con = sqlite3.connect(db.db_path)
            db._sync_impl(con)
            con.close()
            print("[SHUTDOWN] DB flushed successfully.")
        except Exception as e:
            print(f"[SHUTDOWN] DB flush error: {e}")

        for t in tasks:
            t.cancel()

        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[ENGINE] Stopped by user.")
        sys.exit(0)