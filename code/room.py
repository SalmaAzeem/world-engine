from db_manager import DBManager
import time
import paho.mqtt.client as mqtt
import json

broker = "test.mosquitto.org"
port = 1883
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(broker, port, 60)

class Room:
    def __init__(self, building, room_no, floor, state, db_manager):
        self.id = f"b{building}-f{floor}-r{room_no}"
        self.building=building
        self.floor=floor
        self.room_no=room_no
        self.path = f"campus/{self.id}" 
        self.temp = state["temperature"] if state else 22.0
        self.humidity = state["humidity"] if state else 40
        self.occupancy = state["occupancy"] if state else False
        self.light_level = state["light_level"] if state else 0  # light level coming from the sensor
        self.lighting_dimmer = state["lighting_dimmer"] if state else 0  #what you set the light to
        self.hvac_mode = state["hvac_mode"]
        self.db_manager = db_manager

    def update_temperature(self, outside_temp):
        # should query the values from the db first
        alpha = 0.01
        beta = 0.2
        if self.hvac_mode == "ON":
            hvac_power=1
        elif self.hvac_mode == "ECO":
            hvac_power = 0.5
        else:
            hvac_power=0
        self.temp = (self.temp + alpha*(outside_temp - self.temp) + beta*hvac_power) 
        self.db_manager.update_room(room_id=self.id, last_temp=self.temp, hvac_mode=self.hvac_mode)
        self.db_manager.save_room_immediate(room_id=self.id)
    
    def update_light(self):
        # should query the values from the db first
        if self.occupancy == True:
            self.light_level =  max(self.light_level, self.lighting_dimmer)
            self.temp+=1            # Occupancy must increase the temperature slightly
        # there is no data about the light or occupancy in the db
    
    def send_telemetry(self):
        data={
            "metadata": {
                "building": self.building, 
                "floor": self.floor, 
                "room": self.room_no, 
                "sensor_id": self.id, 
                "timestamp": int(time.time())
            }, 
            "actuators": {
                "lighting_dimmer":self.lighting_dimmer , 
                "hvac_mode": self.hvac_mode
            }, 
            "sensors": {
                "humidity": self.humidity, 
                "temperature": self.temp, 
                "occupancy": self.occupancy, 
                "light_level": self.light_level
            }
        }
        topic = f"campus/bldg_{self.building}/floor_{self.floor}/room_{self.room_no}/telemetry"
        payload = json.dumps(data)
        client.publish(topic=topic, payload=payload)
    
    # run simulation function should be implemented here?
    # Night cycle must influence outside temperature (via virtual clock), state = pending
    # add fault modeling

state ={                    # should be replaced by the data coming from the sensors
    "temperature":12,
    "humidity": 40,
    "occupancy": True,
    "light_level":500,
    "hvac_mode": "ON",
    "lighting_dimmer": 75
}
db_manager = DBManager()
room = Room(building="01", room_no="502",floor="05", state=state, db_manager=db_manager)
room.update_temperature(19)
room.send_telemetry()