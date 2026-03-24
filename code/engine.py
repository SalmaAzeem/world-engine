import asyncio
from gmqtt import Client
from room import Room
from db_manager import DBManager
import yaml
import time 

BROKER = "broker.hivemq.com"
PORT = 1883


def create_rooms(db_manager, config, heartbeat_tracker): 
    rooms = []
    states = db_manager.load_state()

    for rid, state in states.items():
        parts = rid.split("-")
        building = parts[0][1:]
        floor = int(parts[1][1:])
        room_num = int(parts[2][1:])

        init_state = {
            "temperature": state["last_temp"],
            "humidity": state["last_humidity"],
            "occupancy": False,
            "light_level": 100,
            "hvac_mode": state["hvac_mode"]
        }

        rooms.append(
            Room(building, room_num, floor, init_state, db_manager, config, heartbeat_tracker)
        )

    return rooms


def on_connect(client, flags, rc, properties):
    print("MQTT connected")


def on_disconnect(client, packet, exc=None):
    print("MQTT disconnected, reconnecting...")



with open("config.yaml") as f:
    config = yaml.safe_load(f)

async def check_heartbeats(heartbeat_tracker, timeout=60):
    while True:
        now = time.time()

        for room_id, last_seen in heartbeat_tracker.items():
            if now - last_seen > timeout:
                print(f"[WARNING] {room_id} is OFFLINE ")

        await asyncio.sleep(10)  

async def main():
    db = DBManager(config)
    db.start_background_sync()

    heartbeat_tracker = {}  

    client = Client("world-engine")

    client.set_config({
        'reconnect_retries': -1
    })

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    await client.connect(BROKER, port=PORT)

    rooms = create_rooms(db, config, heartbeat_tracker)
    print(f"{len(rooms)} rooms loaded")

    tasks = []
    for room in rooms:
        tasks.append(asyncio.create_task(room.run_simulation(client)))
    
    tasks.append(asyncio.create_task(check_heartbeats(heartbeat_tracker)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())