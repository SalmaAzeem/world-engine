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

building = "01"
floor = 5
room = 502
sensor_id = f"b{building}-f{floor}-r{room}"

def handle_command(topic, msg):
    try:
        payload = ujson.loads(msg)
        target_device = payload.get("target_device")
        action = payload.get("action")
        value = payload.get("value")
        print("subscribed topic: ", topic)
        print(sensor_id)
        if target_device != sensor_id:

            print("invalid device")
            return
        if action == "set_hvac":
            if value not in ["ON", "OFF", "ECO"]:
                return
            print("action is: ", action, "and value is: ", value)
            # do something
        elif action == "set_lighting":
            try:
                value_light = int(value)
                if 0 <= value_light <= 100:
                    print("light dimmed")
                else:
                    print("value outside range")
            except ValueError:
                print("rejected")
        else: 
            print(f"rejected action: {action}")
    except ValueError:
        print("rejected json payload")

def main():
    wifi_connection()

    client = MQTTClient("phase1", "broker.hivemq.com")

    client.set_callback(handle_command)
    client.connect()
    client.subscribe(f"campus/bldg_{building}/floor_{floor:02d}/room_{room}/command")
    print("mqtt connected")

    last_published = time.ticks_ms() - 5000
    interval = 5000

    while True:
        try:
            client.check_msg()
            if time.ticks_diff(time.ticks_ms(), last_published) >= interval:
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
                            "hvac_mode": "ECO",
                            "lighting_dimmer": 100 if motion else 0
                        }
                    }
                    json_payload = ujson.dumps(payload)
                    client.publish(f"campus/bldg_{building}/floor_{floor:02d}/room_{room}/telemetry", json_payload)
                    print("published")
                else:
                    print("data is invalid")
                last_published = time.ticks_ms()
                print("temp: ", temp)
                print("humidity", humidity)
                print("motion", motion)
        except OSError as e:
            print("network error or failed to read data from sensors")
        time.sleep(0.1)

main()