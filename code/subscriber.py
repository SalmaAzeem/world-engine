import asyncio
from pathlib import Path

import yaml
from gmqtt import Client


BASE_DIR = Path(__file__).resolve().parent


def load_config():
    with open(BASE_DIR / "config.yaml", "r", encoding="utf-8") as file_handle:
        return yaml.safe_load(file_handle)

def on_message(client, topic, payload, qos, properties):
    print(f"\n Topic: {topic}")
    print(f"Message: {payload.decode()}")

async def main():
    config = load_config()
    client = Client("subscriber")

    client.on_message = on_message

    await client.connect(config["mqtt_broker"], port=config["mqtt_port"])

    client.subscribe("campus/#")

    print(" Listening for messages...\n")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
