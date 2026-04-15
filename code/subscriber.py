import asyncio
import json
import ssl
from pathlib import Path

from gmqtt import Client

import yaml
BASE_DIR = Path(__file__).resolve().parent
with open(BASE_DIR / "config.yaml", "r") as f:
    config = yaml.safe_load(f)

with open(BASE_DIR / "security_keys.json", "r") as f:
    SECURITY_KEYS = json.load(f)

def on_message(client, topic, payload, qos, properties):
    print(f"\n Topic: {topic}")
    print(f"Message: {payload.decode()}")

async def main():
    client = Client("subscriber")
    client.set_auth_credentials("subscriber", SECURITY_KEYS["subscriber"]["password"])

    client.on_message = on_message

    ssl_context = ssl.create_default_context(cafile=str(BASE_DIR.parent / "certs" / "server.crt"))
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    await client.connect(config["mqtt_broker"], port=config.get("mqtt_tls_port", 8883), ssl=ssl_context)

    client.subscribe("campus/#")

    print(" Listening for messages...\n")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
