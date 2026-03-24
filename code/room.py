import asyncio
import time
import random
import json

class Room:
    def __init__(self, building, room, floor, state):
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

    def update_temperature(self, outside_temp):
        alpha = 0.01
        beta = 0.2

        if self.hvac_mode == "ON":
            hvac_power = 1
        elif self.hvac_mode == "ECO":
            hvac_power = 0.5
        else:
            hvac_power = 0

        self.temp = self.temp + alpha * (outside_temp - self.temp) + beta * hvac_power

    def update_light(self, threshold):
        if self.occupancy:
            self.light_level = max(self.light_level, threshold)
            self.temp += 1

    async def run_simulation(self, mqtt_client):
        # startup jitter
        await asyncio.sleep(random.uniform(0, 5))

        while True:
            start = time.perf_counter()

            outside_temp = 30

            # physics updates
            self.update_temperature(outside_temp)
            self.update_light(threshold=300)

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

            topic = f"{self.path}/telemetry"

            # publish telemetry
            await mqtt_client.publish(topic, json.dumps(payload))

            # heartbeat
            heartbeat_topic = f"{self.path}/status"
            await mqtt_client.publish(heartbeat_topic, "alive")

            # drift compensation
            elapsed = time.perf_counter() - start
            await asyncio.sleep(max(0, 5 - elapsed))