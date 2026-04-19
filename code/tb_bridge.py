import csv
import json
import paho.mqtt.client as mqtt

# 1. Load the generated tokens and map them to your engine's sensor IDs
tokens = {}
with open('devices.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Converts "MQTT-F01-R101" info into the engine's format "b01-f01-r101"
        sensor_id = f"b01-f{int(row['floor']):02d}-r{row['room']}"
        tokens[sensor_id] = row['token']

# 2. Keep connections open to ThingsBoard
tb_clients = {}

def get_tb_client(token):
    if token not in tb_clients:
        # Create a dedicated connection for this specific virtual room
        c = mqtt.Client()
        c.username_pw_set(token)
        c.connect("localhost", 1884, 60)  # Port 1884 is ThingsBoard
        c.loop_start()
        tb_clients[token] = c
    return tb_clients[token]

# 3. Intercept HiveMQ data and forward it
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
        # Ensure it's a telemetry packet
        if "metadata" in payload and "sensors" in payload:
            sensor_id = payload["metadata"]["sensor_id"]
            token = tokens.get(sensor_id)
            
            if token:
                tb_client = get_tb_client(token)
                # Forward ONLY the sensors payload directly to ThingsBoard's required topic
                tb_client.publish("v1/devices/me/telemetry", json.dumps(payload["sensors"]))
                print(f"✅ Bridged data for {sensor_id} -> ThingsBoard")
    except Exception:
        pass

print("🚀 Starting HiveMQ -> ThingsBoard Bridge...")

# 4. Listen to HiveMQ
hivemq_client = mqtt.Client()
hivemq_client.on_message = on_message
hivemq_client.connect("localhost", 18830, 60)  # Port 18830 is HiveMQ
hivemq_client.subscribe("campus/#")
hivemq_client.loop_forever()