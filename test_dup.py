import asyncio
import json
import ssl
from pathlib import Path
from gmqtt import Client as MQTTClient

BASE_DIR = Path(__file__).resolve().parent / "code"

with open(BASE_DIR / "security_keys.json", "r") as f:
    SECURITY_KEYS = json.load(f)

room_id = "b01-f01-r101"
password = SECURITY_KEYS[room_id]["password"]
topic = f"campus/b01/f01/r101/cmd"

async def main():
    client = MQTTClient("test-dup-injector")
    client.set_auth_credentials(room_id, password)
    
    ssl_context = ssl.create_default_context(cafile=str(BASE_DIR.parent / "certs" / "server.crt"))
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    await client.connect("localhost", 8883, ssl=ssl_context)
    
    payload = {
        "hvac_mode": "ON",
        "target_temp": 24.5,
        "message_id": "test-dup-12345"
    }
    
    payload_json = json.dumps(payload)
    print(f"Sending Payload 1: {payload_json}")
    client.publish(topic, payload_json, qos=2)
    
    print(f"Sending Payload 2 (Duplicate ID): {payload_json}")
    client.publish(topic, payload_json, qos=2)
    
    await asyncio.sleep(2)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
