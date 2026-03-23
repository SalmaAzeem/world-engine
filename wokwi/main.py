import dht
from machine import Pin
import network
import ntptime
import time 
import ujson
from umqtt.simple import MQTTClient

EPOCH_OFFSET = 946684800

dht_sensor = dht.DHT22(Pin(18))
pir = Pin(14, Pin.IN)

def wifi_connection():
    net = network.WLAN(network.STA_IF)
    net.active(True)
    net.connect('Wokwi-GUEST', '')
    while not net.isconnected():
        print(".")
    print("connected")
    ntptime.settime()

def validations(temp, humidity):
    if (temp < 15.0) or (temp > 50.0):
        return False
    if (humidity < 0.0) or (humidity > 100.0):
        return False
    return True

building = "b01"
floor = 5
room = 502
sensor_id = f"{building}-f{floor}-r{room}"
def main():
    wifi_connection()

    client = MQTTClient("phase1", "broker.hivemq.com")
    client.connect()
    print("mqtt connected")

    while True:
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            humidity = dht_sensor.humidity()
            motion = bool(pir.value())

            validated = validations(temp, humidity)
            light_level = 800 if motion else 50
            if validated:
                payload = {
                    "metadata": {
                        "sensor_id": sensor_id,
                        "building": building,
                        "floor": floor,
                        "room": room,
                        "timestamp": time.time() + EPOCH_OFFSET
                    },
                    "sensors": {
                        "temperature": temp,
                        "humidity": humidity,
                        "occupancy": motion,
                        "light_level": light_level
                    },
                    "actuators": {
                        "hvac_mode": "eco",
                        "lighting_dimmer": 100 if motion else 0
                    }
                }
                json_payload = ujson.dumps(payload)
                client.publish(f"campus/bldg_{building}/floor_{floor}/room_{room}/telemetry", json_payload)
                print("published")
            else:
                print("data is invalid")
            print("temp: ", temp)
            print("humidity", humidity)
            print("motion", motion)
        except OSError as e:
            print("failed to read data from sensors")
        time.sleep(5)

main()