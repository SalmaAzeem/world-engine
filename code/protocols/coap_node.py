from __future__ import annotations

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
        self.context = await aiocoap.Context.create_server_context(
            self.site,
            bind=(self.config["coap_bind_host"], self.room.coap_port),
            transports=["tinydtls_server"] if self.config.get("coap_enable_dtls", True) else self.config.get("coap_server_transports"),
        )
        psk_hex = SECURITY_KEYS[self.room.room_id]["psk"]
        self.context.server_credentials.load_from_dict({
            ":client": {
                "dtls": {
                    "psk": {
                        self.room.room_id.encode("utf-8"): bytes.fromhex(psk_hex)
                    }
                }
            }
        })

        self.health_monitor.set_status(self.room.room_id, "ONLINE")
        print(
            f"[CoAP] {self.room.room_id} listening on "
            f"{self.config['coap_bind_host']}:{self.room.coap_port}"
        )

    async def stop(self):
        if self.context is not None:
            await self.context.shutdown()

    async def publish_telemetry(self, payload):
        self.telemetry_resource.set_payload(payload)
        self.health_monitor.record_heartbeat(self.room.room_id, self.room.protocol)
