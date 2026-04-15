from __future__ import annotations

import asyncio
import time


class HealthMonitor:
    def __init__(self, timeout_seconds, check_interval):
        self.timeout_seconds = timeout_seconds
        self.check_interval = check_interval
        self.rooms = {}

    def register_room(self, room):
        self.rooms[room.room_id] = {
            "protocol": room.protocol,
            "status": "STARTING",
            "last_seen": None,
        }

    def record_heartbeat(self, room_id, protocol):
        room_health = self.rooms.setdefault(
            room_id,
            {"protocol": protocol, "status": "STARTING", "last_seen": None},
        )
        room_health["last_seen"] = time.time()
        if room_health["status"] in {"STARTING", "DEAD"}:
            room_health["status"] = "ONLINE"

    def set_status(self, room_id, status):
        if room_id not in self.rooms:
            return
        self.rooms[room_id]["status"] = status
        if status == "ONLINE":
            self.rooms[room_id]["last_seen"] = time.time()

    def snapshot(self):
        return dict(self.rooms)

    async def run(self):
        while True:
            await asyncio.sleep(self.check_interval)
            now = time.time()
            for room_id, health in self.rooms.items():
                if health["protocol"] != "coap":
                    continue

                last_seen = health["last_seen"]
                if last_seen is None:
                    continue

                if now - last_seen > self.timeout_seconds:
                    health["status"] = "DEAD"
