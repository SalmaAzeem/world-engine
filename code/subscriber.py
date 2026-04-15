import asyncio

from gmqtt import Client

from config_loader import load_config

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
