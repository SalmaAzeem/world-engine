import asyncio
import json
import random
import time


class Room:
    def __init__(self, building, room, floor, state, db_manager, config, heartbeat_tracker):
        self.building = building
        self.floor    = floor
        self.room     = room

        
        self.id   = f"b{building}-f{floor:02d}-r{room}"

        self.path = f"campus/bldg_{building}/floor_{floor:02d}/room_{room:03d}"

        self.temp        = state["temperature"]
        self.humidity    = state["humidity"]
        self.occupancy   = state["occupancy"]
        self.light_level = state["light_level"]
        self.hvac_mode   = state["hvac_mode"]

        self.db_manager       = db_manager
        self.config           = config
        self.heartbeat_tracker = heartbeat_tracker
        
        self.enable_drift = False   # these variables are for fault modeling 
        self.enable_freeze = False
        self.enable_dropout = False
        self.drift_bias = 0
        self.frozen_temp = None

    # Thermal model 
    def update_temperature(self, outside_temp):
        alpha = self.config["alpha"]   # insulation constant
        beta  = self.config["beta"]    # HVAC strength

        if self.hvac_mode == "ON":
            hvac_power = 1.0
        elif self.hvac_mode == "ECO":
            hvac_power = 0.5
        else:
            hvac_power = 0.0

        leakage    = alpha * (outside_temp - self.temp)
        hvac_effect = beta * hvac_power
        self.temp  = self.temp + leakage + hvac_effect

  
    def update_light(self, threshold=300):
        if self.occupancy:
            self.light_level = max(self.light_level, threshold)
            self.temp += 0.1   

    def trigger_faults(self):
        if self.enable_drift and random.random() < 0.05:
            self.enable_drift = False
        if self.enable_freeze and random.random() < 0.05:
            self.enable_freeze = False
        if self.enable_dropout and random.random() < 0.10:
            self.enable_dropout = False

        fault_prob = self.config.get("fault_probability", 0.01)
        if random.random() < fault_prob:
            fault_type = random.choice(["drift", "freeze", "dropout"])
            if fault_type == "drift" and not self.enable_drift:
                self.enable_drift = True
                self.drift_bias = random.uniform(-5.0, 5.0)
            elif fault_type == "freeze" and not self.enable_freeze:
                self.enable_freeze = True
                self.frozen_temp = self.temp
            elif fault_type == "dropout":
                self.enable_dropout = True

    #Main async simulation loop 
    async def run_simulation(self, mqtt_client):
        await asyncio.sleep(random.uniform(0, self.config["max_jitter"]))

        # Time acceleration
        time_accel = self.config.get("time_acceleration", 1.0)

        while True:
            tick_start = time.perf_counter()

            outside_temp = self.config["outside_temp"]

           
            self.update_temperature(outside_temp)
            
            self.update_light(threshold=300)

           
            self.db_manager.update_room(
                self.id,
                last_temp=self.temp,
                last_humidity=self.humidity,
                hvac_mode=self.hvac_mode,
                timestamp=int(time.time()),
            )

            self.trigger_faults()
            reported_temp = self.temp
            if self.enable_freeze:
                reported_temp = self.frozen_temp
            elif self.enable_drift:
                reported_temp += self.drift_bias

            payload = {
                "metadata": {
                    "sensor_id": self.id,
                    "building":  self.building,
                    "floor":     self.floor,
                    "room":      self.room,
                    "timestamp": int(time.time()),
                },
                "sensors": {
                    "temperature": round(reported_temp, 2),
                    "humidity": round(self.humidity, 2),
                    "occupancy": self.occupancy,
                    "light_level": self.light_level
                },
                "actuators": {
                    "hvac_mode":       self.hvac_mode,
                    "lighting_dimmer": 100 if self.occupancy else 0,
                },
            }

            if not self.enable_dropout:
                self.heartbeat_tracker[self.id] = time.time()
                if mqtt_client.is_connected:
                    mqtt_client.publish(f"{self.path}/telemetry", json.dumps(payload), qos=2)
                    mqtt_client.publish(f"{self.path}/status", "alive")

            elapsed = time.perf_counter() - tick_start
            interval = self.config["publish_interval"]
            await asyncio.sleep(max(0, interval - elapsed))