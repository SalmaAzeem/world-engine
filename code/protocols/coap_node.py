from __future__ import annotations
import asyncio
import time

import aiocoap
import aiocoap.resource as resource

from protocols.coap_resources import (
    HVACActuatorResource,
    LightingActuatorResource,
    TelemetryResource,
)
import json
import aiocoap.credentials
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "security_keys.json", "r") as f:
    SECURITY_KEYS = json.load(f)


class CoAPNode:
    def __init__(self, room, config, health_monitor):
        self.room = room
        self.config = config
        self.health_monitor = health_monitor
        self.site = resource.Site()
        self.telemetry_resource = TelemetryResource(room)
        self.context = None
        self.running = False
        self._sentinel_task = None

        self.site.add_resource(
            [self.room.coap_floor_segment, self.room.coap_room_segment, "telemetry"],
            self.telemetry_resource,
        )
        self.site.add_resource(
            [self.room.coap_floor_segment, self.room.coap_room_segment, "actuators", "hvac"],
            HVACActuatorResource(room, self.telemetry_resource, self.health_monitor),
        )
        self.site.add_resource(
            [self.room.coap_floor_segment, self.room.coap_room_segment, "actuators", "lighting"],
            LightingActuatorResource(room, self.telemetry_resource, self.health_monitor),
        )

    async def start(self):
        bind_host = self.config["coap_bind_host"]
        if bind_host == "0.0.0.0":
            import socket
            bind_host = socket.gethostbyname(socket.gethostname())

        self.context = await aiocoap.Context.create_server_context(
            self.site,
            bind=(bind_host, self.room.coap_port),
            transports=["tinydtls_server"] if self.config.get("coap_enable_dtls", True) else self.config.get("coap_server_transports"),
        )
        psk_hex = SECURITY_KEYS[self.room.room_id]["psk"]
        self.context.server_credentials.load_from_dict({
            f":client:{self.room.room_id}": {
                "dtls": {
                    "psk": bytes.fromhex(psk_hex),
                    "client_identity": self.room.room_id.encode("utf-8")
                }
            }
        })

        self.health_monitor.set_status(self.room.room_id, "ONLINE")
        print(
            f"[CoAP] {self.room.room_id} listening on "
            f"{self.config['coap_bind_host']}:{self.room.coap_port}"
        )
        
        self.running = True
        self._sentinel_task = asyncio.create_task(self._sentinel_monitor())

    async def _sentinel_monitor(self):
        last_smoke_state = False
        while self.running:
            if self.room.smoke_detected and not last_smoke_state:
                last_smoke_state = True
                print(f"[SENTINEL] {self.room.room_id} Smoke Detected! Firing CoAP CON to Gateway...")
                try:
                    payload = json.dumps({
                        "room_id": self.room.room_id,
                        "alert": "SMOKE_DETECTED",
                        "timestamp": int(time.time()),
                        "message_id": f"sentinel-{self.room.room_id}-{int(time.time())}"
                    }).encode("utf-8")
                    
                    gateway_url = f"coap://gateway_f{self.room.floor_id:02d}:5683/sentinel"
                    
                    client_context = await aiocoap.Context.create_client_context()
                    request = aiocoap.Message(code=aiocoap.POST, mtype=aiocoap.CON, payload=payload, uri=gateway_url)
                    response = await client_context.request(request).response
                    print(f"[SENTINEL ACK] {self.room.room_id} received ACK from Gateway: {response.code}")
                    await client_context.shutdown()
                except Exception as e:
                    print(f"[SENTINEL ERR] {self.room.room_id} failed to reach gateway: {e}")
            elif not self.room.smoke_detected and last_smoke_state:
                last_smoke_state = False
                
            await asyncio.sleep(1)

    async def stop(self):
        self.running = False
        if self._sentinel_task:
            self._sentinel_task.cancel()
            
        if self.context is not None:
            await self.context.shutdown()

    async def publish_telemetry(self, payload):
        self.telemetry_resource.set_payload(payload)
        self.health_monitor.record_heartbeat(self.room.room_id, self.room.protocol)
