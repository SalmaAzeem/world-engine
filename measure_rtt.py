import asyncio
import json
import ssl
import time
from pathlib import Path
from gmqtt import Client as MQTTClient

BASE_DIR = Path(__file__).resolve().parent / "code"

with open(BASE_DIR / "security_keys.json", "r") as f:
    SECURITY_KEYS = json.load(f)

room_id = "b01-f01-r101"
password = SECURITY_KEYS[room_id]["password"]
topic_cmd = f"campus/b01/f01/r101/cmd"
topic_telemetry = f"campus/b01/f01/r101/telemetry"

rtt_results = []
start_time = 0

async def on_message(client, topic, payload, qos, properties):
    global start_time, rtt_results
    if time.time() - start_time > 0.001:  
        rtt = (time.time() - start_time) * 1000
        rtt_results.append(rtt)
        client.stop_flag = True

async def main():
    global start_time, rtt_results
    
    with open("rtt_log.txt", "w") as x:
        x.write("Iteration,RTT_ms\n")
        
    for i in range(50):
        client = MQTTClient(f"tester-rtt-{i}")
        client.set_auth_credentials(room_id, password)
        client.on_message = on_message
        client.stop_flag = False
        
        ssl_context = ssl.create_default_context(cafile=str(BASE_DIR.parent / "certs" / "server.crt"))
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        await client.connect("localhost", 8883, ssl=ssl_context)
        client.subscribe(topic_telemetry, qos=1)
        
        payload = {"target_temp": 22.0 + (i % 5), "message_id": f"ping-{i}"}
        start_time = time.time()
        client.publish(topic_cmd, json.dumps(payload), qos=1)
        
        while not client.stop_flag:
            await asyncio.sleep(0.01)
            
        await client.disconnect()
        with open("rtt_log.txt", "a") as x:
            x.write(f"{i},{rtt_results[-1]:.2f}\n")
            
        print(f"Pined {i}/50: {rtt_results[-1]:.2f} ms")
        await asyncio.sleep(0.2)

if __name__ == "__main__":
    asyncio.run(main())
