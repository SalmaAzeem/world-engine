from __future__ import annotations

import math
import time
from dataclasses import dataclass


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


@dataclass
class RoomState:
    building_id: str
    floor_id: int
    room_number: int
    protocol: str
    temperature: float
    humidity: float
    hvac_mode: str
    target_temp: float
    occupancy: bool = False
    light_level: int = 100
    lighting_dimmer: int = 0
    coap_host: str | None = None
    coap_port: int | None = None

    def __post_init__(self):
        self.last_update = int(time.time())
        self.last_heartbeat = time.time()

    @property
    def room_slot(self):
        return self.room_number - (self.floor_id * 100)

    @property
    def room_id(self):
        return f"b{self.building_id}-f{self.floor_id:02d}-r{self.room_number}"

    @property
    def mqtt_base_topic(self):
        return f"campus/b{self.building_id}/f{self.floor_id:02d}/r{self.room_number}"

    @property
    def telemetry_topic(self):
        return f"{self.mqtt_base_topic}/telemetry"

    @property
    def command_topic(self):
        return f"{self.mqtt_base_topic}/cmd"

    @property
    def status_topic(self):
        return f"{self.mqtt_base_topic}/status"

    @property
    def response_topic(self):
        return f"{self.mqtt_base_topic}/response"

    @property
    def coap_room_segment(self):
        return f"r{self.room_number}"

    @property
    def coap_floor_segment(self):
        return f"f{self.floor_id:02d}"

    @property
    def coap_telemetry_uri(self):
        if self.coap_host is None or self.coap_port is None:
            return None
        return (
            f"coap://{self.coap_host}:{self.coap_port}/"
            f"{self.coap_floor_segment}/{self.coap_room_segment}/telemetry"
        )

    def status_payload(self, status):
        return {
            "room_id": self.room_id,
            "protocol": self.protocol,
            "status": status,
            "timestamp": int(time.time()),
        }

    def telemetry_payload(self):
        return {
            "metadata": {
                "sensor_id": self.room_id,
                "building": self.building_id,
                "floor": self.floor_id,
                "room": self.room_number,
                "timestamp": self.last_update,
                "protocol": self.protocol,
            },
            "sensors": {
                "temperature": round(self.temperature, 2),
                "humidity": round(self.humidity, 2),
                "occupancy": self.occupancy,
                "light_level": self.light_level,
            },
            "actuators": {
                "hvac_mode": self.hvac_mode,
                "target_temp": round(self.target_temp, 2),
                "lighting_dimmer": self.lighting_dimmer,
            },
        }

    def command_response(self, source):
        return {
            "room_id": self.room_id,
            "protocol": self.protocol,
            "source": source,
            "timestamp": int(time.time()),
            "applied_state": {
                "hvac_mode": self.hvac_mode,
                "target_temp": round(self.target_temp, 2),
                "lighting_dimmer": self.lighting_dimmer,
            },
        }

    def apply_command(self, command):
        if "hvac_mode" in command:
            self.hvac_mode = command["hvac_mode"]

        if "target_temp" in command:
            self.target_temp = float(command["target_temp"])

        if "lighting_dimmer" in command:
            self.lighting_dimmer = clamp(int(command["lighting_dimmer"]), 0, 100)

        self.last_update = int(time.time())

    def tick(self, simulated_time, config):
        self.occupancy = self._calculate_occupancy(simulated_time)
        outside_temp = self._outside_temperature(simulated_time, config)

        self._update_temperature(outside_temp, config)
        self._update_humidity(simulated_time)
        self._update_light_level(config)

        now = time.time()
        self.last_update = int(simulated_time)
        self.last_heartbeat = now
        return self.telemetry_payload()

    def _calculate_occupancy(self, simulated_time):
        hour = int((simulated_time // 3600) % 24)
        daytime = 8 <= hour < 18
        pattern = int((simulated_time // 900) + self.floor_id + self.room_slot) % 4
        return daytime and pattern != 0

    def _outside_temperature(self, simulated_time, config):
        hour = (simulated_time / 3600.0) % 24.0
        angle = ((hour - 6.0) / 24.0) * 2.0 * math.pi
        day_ratio = (math.sin(angle) + 1.0) / 2.0
        return config["outside_temp_night"] + (
            (config["outside_temp_day"] - config["outside_temp_night"]) * day_ratio
        )

    def _update_temperature(self, outside_temp, config):
        alpha = config["alpha"]
        beta = config["beta"]

        if self.hvac_mode == "ON":
            hvac_strength = beta
        elif self.hvac_mode == "ECO":
            hvac_strength = beta * 0.5
        else:
            hvac_strength = 0.0

        leakage = alpha * (outside_temp - self.temperature)
        direction_to_target = self.target_temp - self.temperature

        if hvac_strength == 0.0:
            hvac_effect = 0.0
        else:
            hvac_effect = clamp(direction_to_target, -hvac_strength, hvac_strength)

        occupancy_heat = config["occupancy_heat"] if self.occupancy else 0.0
        self.temperature += leakage + hvac_effect + occupancy_heat
        self.temperature = clamp(self.temperature, 15.0, 50.0)

    def _update_humidity(self, simulated_time):
        hour = int((simulated_time // 3600) % 24)
        baseline = 55.0 if hour < 7 or hour >= 18 else 45.0
        if self.occupancy:
            baseline += 5.0

        self.humidity += 0.08 * (baseline - self.humidity)
        self.humidity = clamp(self.humidity, 0.0, 100.0)

    def _update_light_level(self, config):
        if self.occupancy:
            desired_light = max(config["occupied_light_threshold"], self.lighting_dimmer * 10)
        else:
            desired_light = self.lighting_dimmer * 5

        self.light_level = int(clamp(desired_light, 0, 1000))
