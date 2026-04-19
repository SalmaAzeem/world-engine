import csv
import json
import paho.mqtt.client as mqtt

tokens = {}
with open('devices.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sensor_id = f"b01-f{int(row['floor']):02d}-r{row['room']}"
        tokens[sensor_id] = row['token']

tb_clients = {}

def get_tb_client(token):
    if token not in tb_clients:
        c = mqtt.Client()
        c.username_pw_set(token)
        c.connect("localhost", 1884, 60)  
        c.loop_start()
        tb_clients[token] = c
    return tb_clients[token]

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
        if "metadata" in payload and "sensors" in payload:
            sensor_id = payload["metadata"]["sensor_id"]
            token = tokens.get(sensor_id)
            
            if token:
                tb_client = get_tb_client(token)
                tb_client.publish("v1/devices/me/telemetry", json.dumps(payload["sensors"]))
                print(f"✅ Bridged data for {sensor_id} -> ThingsBoard")
    except Exception:
        pass

print("🚀 Starting HiveMQ -> ThingsBoard Bridge...")

hivemq_client = mqtt.Client()
hivemq_client.on_message = on_message
hivemq_client.connect("localhost", 18830, 60)  
hivemq_client.subscribe("campus/#")
hivemq_client.loop_forever()