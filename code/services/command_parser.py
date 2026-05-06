from __future__ import annotations

import json


VALID_HVAC_MODES = {"ON", "OFF", "ECO"}


def parse_command_payload(payload, default_action=None):
    try:
        data = _coerce_to_dict(payload)
        action = data.get("action", default_action)
        command = {}

        if "hvac_mode" in data:
            hvac_mode = str(data["hvac_mode"]).upper()
            if hvac_mode not in VALID_HVAC_MODES:
                return None
            command["hvac_mode"] = hvac_mode
        elif action in {"set_hvac", "set_hvac_mode"}:
            hvac_mode = str(data.get("value", "")).upper()
            if hvac_mode not in VALID_HVAC_MODES:
                return None
            command["hvac_mode"] = hvac_mode

        if "target_temp" in data:
            command["target_temp"] = float(data["target_temp"])
        elif action == "set_target_temp":
            command["target_temp"] = float(data["value"])

        if "lighting_dimmer" in data:
            command["lighting_dimmer"] = _validate_dimmer(data["lighting_dimmer"])
        elif action in {"set_lighting", "set_lighting_dimmer"}:
            command["lighting_dimmer"] = _validate_dimmer(data["value"])

        if "message_id" in data:
            command["message_id"] = str(data["message_id"])
            
        if "emergency_lockout" in data:
            command["emergency_lockout"] = bool(data["emergency_lockout"])
            
        if "smoke_detected" in data:
            command["smoke_detected"] = bool(data["smoke_detected"])

        if "signature" in data:
            command["signature"] = str(data["signature"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    return command or None


def _coerce_to_dict(payload):
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")

    if isinstance(payload, str):
        payload = payload.strip()
        if payload.startswith("{"):
            return json.loads(payload)
        return {"value": payload}

    if isinstance(payload, dict):
        return payload

    raise TypeError("Unsupported payload type")


def _validate_dimmer(value):
    dimmer = int(value)
    if dimmer < 0 or dimmer > 100:
        raise ValueError("lighting_dimmer must be between 0 and 100")
    return dimmer
