from __future__ import annotations

import asyncio
import csv
import os
import sqlite3
import sys
import time

from config_loader import BASE_DIR, load_config
from db_manager import DBManager
from fleet import build_fleet
from protocols import CoAPNode, MQTTNode
from services import HealthMonitor


def load_device_tokens():
    """Loads ThingsBoard tokens from the CSV file into a dictionary."""
    tokens = {}
    csv_path = str(BASE_DIR / "devices.csv")
    
    if not os.path.exists(csv_path):
        csv_path = "devices.csv"
        if not os.path.exists(csv_path):
            print("[ENGINE] WARNING: devices.csv not found! Nodes will connect without auth.")
            return tokens

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            protocol = row['protocol'].lower()
            room_num = int(row['room'])
            tokens[(protocol, room_num)] = row['token']
            
    print(f"[ENGINE] Loaded {len(tokens)} device tokens from CSV.")
    return tokens


def create_transports(rooms, config, health_monitor, device_tokens):
    transports = {}
    for room in rooms:
        room_num = int(''.join(filter(str.isdigit, room.room_id)))
        
        token = device_tokens.get((room.protocol, room_num))

        if room.protocol == "mqtt":
            transports[room.room_id] = MQTTNode(room, config, health_monitor, token=token)
        else:
            transports[room.room_id] = CoAPNode(room, config, health_monitor, token=token)
    return transports


async def room_loop(room, transport, db_manager, health_monitor, config, real_start, simulated_start):
    await asyncio.sleep(_startup_jitter(config))

    while True:
        tick_started = time.perf_counter()
        simulated_now = simulated_start + (
            (tick_started - real_start) * config["time_acceleration"]
        )

        payload = room.tick(simulated_now, config)
        db_manager.update_room(
            room.room_id,
            last_temp=room.temperature,
            last_humidity=room.humidity,
            hvac_mode=room.hvac_mode,
            target_temp=room.target_temp,
            timestamp=int(simulated_now),
        )
        health_monitor.record_heartbeat(room.room_id, room.protocol)
        await transport.publish_telemetry(payload)

        elapsed = time.perf_counter() - tick_started
        await asyncio.sleep(max(0.0, config["tick_interval"] - elapsed))


def _startup_jitter(config):
    import random
    return random.uniform(0, config["max_jitter"])


async def main():
    config = load_config()

    db_path = os.getenv("DB_PATH", str(BASE_DIR / "state.db"))
    db = DBManager(config, db_path=db_path)
    db.start_background_sync(sync_interval=config["db_sync_interval"])

    health_monitor = HealthMonitor(
        timeout_seconds=config["heartbeat_timeout"],
        check_interval=config["health_check_interval"],
    )

    rooms = build_fleet(db, config)
    for room in rooms:
        health_monitor.register_room(room)

    device_tokens = load_device_tokens()
    
    transports = create_transports(rooms, config, health_monitor, device_tokens)
    
    await asyncio.gather(*(transport.start() for transport in transports.values()))

    print(
        f"[ENGINE] Loaded {len(rooms)} rooms "
        f"({sum(room.protocol == 'mqtt' for room in rooms)} MQTT / "
        f"{sum(room.protocol == 'coap' for room in rooms)} CoAP)"
    )

    real_start = time.perf_counter()
    simulated_start = time.time()

    tasks = [
        asyncio.create_task(
            room_loop(
                room,
                transports[room.room_id],
                db,
                health_monitor,
                config,
                real_start,
                simulated_start,
            )
        )
        for room in rooms
    ]
    tasks.append(asyncio.create_task(health_monitor.run()))

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        pass
    finally:
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.gather(*(transport.stop() for transport in transports.values()), return_exceptions=True)

        print("\n[SHUTDOWN] Flushing DB state...")
        try:
            con = sqlite3.connect(db.db_path)
            db._sync_impl(con)
            con.close()
            print("[SHUTDOWN] DB flushed successfully.")
        except Exception as exc:
            print(f"[SHUTDOWN] DB flush error: {exc}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[ENGINE] Stopped by user.")
        sys.exit(0)