import time
import asyncio
import random
import json


class Room:
    def __init__(self, building, room, floor, state, db_manager, config, heartbeat_tracker):
        self.building = building
        self.floor = floor
        self.room = room

        self.id = f"b{building}-f{floor:02d}-r{room}"
        self.path = f"campus/bldg_{building}/floor_{floor:02d}/room_{room}"

        self.temp = state["temperature"]
        self.humidity = state["humidity"]
        self.occupancy = state["occupancy"]
        self.light_level = state["light_level"]
        self.hvac_mode = state["hvac_mode"]

        self.db_manager = db_manager
        self.config = config
        self.heartbeat_tracker = heartbeat_tracker

    def update_temperature(self, outside_temp):
        alpha = self.config["alpha"]
        beta = self.config["beta"]

        if self.hvac_mode == "ON":
            hvac_power = 1
        elif self.hvac_mode == "ECO":
            hvac_power = 0.5
        else:
            hvac_power = 0

        self.temp = (
            self.temp
            + alpha * (outside_temp - self.temp)
            + beta * hvac_power
        )

    def update_light(self, threshold):
        if self.occupancy:
            self.light_level = max(self.light_level, threshold)
            self.temp += 1

    async def run_simulation(self, mqtt_client):
        await asyncio.sleep(random.uniform(0, self.config["max_jitter"]))

        while True:
            start = time.perf_counter()

            outside_temp = self.config["outside_temp"]

            self.update_temperature(outside_temp)
            self.update_light(300)

            self.db_manager.update_room(
                self.id,
                last_temp=self.temp,
                last_humidity=self.humidity,
                hvac_mode=self.hvac_mode,
                timestamp=int(time.time())
            )

            payload = {
                "metadata": {
                    "sensor_id": self.id,
                    "building": self.building,
                    "floor": self.floor,
                    "room": self.room,
                    "timestamp": int(time.time())
                },
                "sensors": {
                    "temperature": round(self.temp, 2),
                    "humidity": round(self.humidity, 2),
                    "occupancy": self.occupancy,
                    "light_level": self.light_level
                },
                "actuators": {
                    "hvac_mode": self.hvac_mode,
                    "lighting_dimmer": 100 if self.occupancy else 0
                }
            }

            
            self.heartbeat_tracker[self.id] = time.time()

            if mqtt_client.is_connected:
                mqtt_client.publish(f"{self.path}/telemetry", json.dumps(payload), qos=2)
                mqtt_client.publish(f"{self.path}/status", "alive")

            elapsed = time.perf_counter() - start
            interval = self.config["publish_interval"]
            await asyncio.sleep(max(0, interval - elapsed))