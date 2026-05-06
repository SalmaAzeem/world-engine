from __future__ import annotations

import json

import aiocoap
import aiocoap.resource as resource

from services.command_parser import parse_command_payload
from services.security_utils import verify_fingerprint


JSON_CONTENT_FORMAT = 50
CONTENT_CODE = getattr(aiocoap, "CONTENT", None)
CHANGED_CODE = getattr(aiocoap, "CHANGED", None)
BAD_REQUEST_CODE = getattr(aiocoap, "BAD_REQUEST", None)


class TelemetryResource(resource.ObservableResource):
    def __init__(self, room):
        super().__init__()
        self.room = room
        self.payload = json.dumps(self.room.telemetry_payload()).encode("utf-8")

    def set_payload(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")
        self.updated_state()

    async def render_get(self, request):
        response_kwargs = {
            "payload": self.payload,
            "content_format": JSON_CONTENT_FORMAT,
        }
        if CONTENT_CODE is not None:
            response_kwargs["code"] = CONTENT_CODE
        return aiocoap.Message(**response_kwargs)


class HVACActuatorResource(resource.Resource):
    def __init__(self, room, telemetry_resource, health_monitor):
        super().__init__()
        self.room = room
        self.telemetry_resource = telemetry_resource
        self.health_monitor = health_monitor

    async def render_put(self, request):
        try:
            raw_data = json.loads(request.payload)
        except Exception:
            return _build_error_response("Invalid JSON payload")

        if not verify_fingerprint(raw_data):
            print(f"[SECURITY TAMPERING ALERT] Invalid hash detected for {self.room.room_id} (HVAC)!")
            alert_payload = self.room.tampering_alert_payload("SHA-256 Signature Mismatch or Missing")
            self.telemetry_resource.set_payload(alert_payload)
            return _build_error_response("Security Tampering Alert: Invalid Hash")

        command = parse_command_payload(raw_data, default_action="set_hvac_mode")
        if command is None:
            return _build_error_response("Invalid HVAC command")

        self.room.apply_command(command)
        self.telemetry_resource.set_payload(self.room.telemetry_payload())
        self.health_monitor.record_heartbeat(self.room.room_id, self.room.protocol)
        return _build_change_response(self.room.command_response("coap"))


class LightingActuatorResource(resource.Resource):
    def __init__(self, room, telemetry_resource, health_monitor):
        super().__init__()
        self.room = room
        self.telemetry_resource = telemetry_resource
        self.health_monitor = health_monitor

    async def render_put(self, request):
        try:
            raw_data = json.loads(request.payload)
        except Exception:
            return _build_error_response("Invalid JSON payload")

        if not verify_fingerprint(raw_data):
            print(f"[SECURITY TAMPERING ALERT] Invalid hash detected for {self.room.room_id} (Lighting)!")
            alert_payload = self.room.tampering_alert_payload("SHA-256 Signature Mismatch or Missing")
            self.telemetry_resource.set_payload(alert_payload)
            return _build_error_response("Security Tampering Alert: Invalid Hash")

        command = parse_command_payload(raw_data, default_action="set_lighting")
        if command is None:
            return _build_error_response("Invalid lighting command")

        self.room.apply_command(command)
        self.telemetry_resource.set_payload(self.room.telemetry_payload())
        self.health_monitor.record_heartbeat(self.room.room_id, self.room.protocol)
        return _build_change_response(self.room.command_response("coap"))


def _build_change_response(payload):
    response_kwargs = {
        "payload": json.dumps(payload).encode("utf-8"),
        "content_format": JSON_CONTENT_FORMAT,
    }
    if CHANGED_CODE is not None:
        response_kwargs["code"] = CHANGED_CODE
    return aiocoap.Message(**response_kwargs)


def _build_error_response(message):
    response_kwargs = {
        "payload": json.dumps({"error": message}).encode("utf-8"),
        "content_format": JSON_CONTENT_FORMAT,
    }
    if BAD_REQUEST_CODE is not None:
        response_kwargs["code"] = BAD_REQUEST_CODE
    return aiocoap.Message(**response_kwargs)
