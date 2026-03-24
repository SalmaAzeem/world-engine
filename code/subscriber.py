import asyncio
from gmqtt import Client

BROKER = "broker.hivemq.com"

def on_message(client, topic, payload, qos, properties):
    print(f"\n Topic: {topic}")
    print(f"Message: {payload.decode()}")

async def main():
    client = Client("subscriber")

    client.on_message = on_message

    await client.connect(BROKER, port=1883)

    # subscribe to alll topics
    # client.subscribe("campus/#")
    client.subscribe("campus/bldg_01/floor_05/room_502/telemetry")

    print(" Listening for messages...\n")

    await asyncio.Event().wait()  #

if __name__ == "__main__":
    asyncio.run(main())