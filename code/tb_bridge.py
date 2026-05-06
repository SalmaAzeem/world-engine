import json
import time
import logging
import paho.mqtt.client as mqtt
import random
from services.security_utils import calculate_fingerprint

HIVE_BROKER = "hivemq"  
HIVE_PORT = 1883
TB_BROKER = "thingsboard"
TB_PORT = 1883           
GATEWAY_TOKEN = "pf3piz4d4yb6ouxf68vc" 

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("TB-BRIDGE")

hive_client = mqtt.Client(client_id=f"bridge-hive-{random.randint(1000, 9999)}")
tb_client = mqtt.Client(client_id=f"bridge-tb-{random.randint(1000, 9999)}")

def on_hive_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to HiveMQ Broker")
        client.subscribe("campus/+/+/+/telemetry")
    else:
        logger.error(f"Failed to connect to HiveMQ, code: {rc}")

def on_tb_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to ThingsBoard Gateway successfully")
        client.subscribe("v1/gateway/rpc")
    else:

        logger.error(f"ThingsBoard Connection Refused! Code: {rc}")
        if rc == 4:
            logger.error("TIP: Ensure your device in ThingsBoard is marked as 'Is Gateway' and the token is correct.")

def on_tb_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"Unexpectedly disconnected from ThingsBoard (code {rc}). Retrying...")

def on_tb_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
        device_name = data.get("device")
        rpc_data = data.get("data", {})
        method = rpc_data.get("method")
        params = rpc_data.get("params")
        request_id = data.get("id")

        logger.info(f"Incoming RPC for {device_name}: {method}({params})")

        parts = device_name.split("-")
        floor = parts[1].replace("F", "").lower()
        room = parts[2].replace("R", "").lower()
        
        hive_topic = f"campus/b01/f{floor}/r{room}/cmd"
        command_payload = {
            "action": method,
            "value": params,
            "message_id": f"tb-rpc-{request_id}-{int(time.time())}"
        }
        
        command_payload["signature"] = calculate_fingerprint(command_payload)
        
        hive_client.publish(hive_topic, json.dumps(command_payload), qos=1)
        logger.info(f"Forwarded command to HiveMQ: {hive_topic}")

    except Exception as e:
        logger.error(f"Error handling TB RPC: {e}")

def on_hive_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
        metadata = payload.get("metadata", {})
        
        protocol = metadata.get("protocol", "mqtt").upper()
        floor = f"{metadata.get('floor', 0):02d}"
        room = metadata.get("room", 0)
        device_name = f"{protocol}-F{floor}-R{room}"
        device_type = f"{protocol}-ThermalSensor"

        ts = metadata.get("timestamp", time.time())
        if ts < 10000000000: 
            ts = int(ts * 1000)
        else:
            ts = int(ts)
        
        tb_payload = {
            device_name: [
                {
                    "ts": ts,
                    "values": {
                        **payload.get("sensors", {}),
                        **payload.get("actuators", {}),
                        **payload.get("security_alerts", {})
                    }
                }
            ]
        }
        
        tb_client.publish("v1/gateway/connect", json.dumps({"device": device_name, "type": device_type}))
        tb_client.publish("v1/gateway/telemetry", json.dumps(tb_payload), qos=1)
        logger.info(f"Bridged {device_name} (TS: {ts}) to ThingsBoard")
    except Exception as e:
        logger.error(f"Error bridging telemetry: {e}")

hive_client.on_connect = on_hive_connect
hive_client.on_message = on_hive_message

tb_client.on_connect = on_tb_connect
tb_client.on_disconnect = on_tb_disconnect
tb_client.on_message = on_tb_message
tb_client.username_pw_set(GATEWAY_TOKEN)

def run():
    logger.info("Starting HiveMQ <-> ThingsBoard Gateway Bridge...")
    
    while True:
        try:
            hive_client.connect(HIVE_BROKER, HIVE_PORT, 60)
            tb_client.connect(TB_BROKER, TB_PORT, 60)
            break
        except Exception as e:
            logger.warning(f"Initial connection failed ({e}), retrying...")
            time.sleep(5)

    hive_client.loop_start()
    tb_client.loop_forever()

if __name__ == "__main__":
    run()
