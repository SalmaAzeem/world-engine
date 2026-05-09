import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from models.room_state import RoomState
from services.ota_update import (
    apply_ota_update,
    matching_rooms,
    ota_topic_matches_room,
    parse_ota_payload,
)
from services.security_utils import calculate_fingerprint, verify_fingerprint


def make_room(floor=5, room_number=501):
    return RoomState(
        building_id="01",
        floor_id=floor,
        room_number=room_number,
        protocol="mqtt",
        temperature=24.0,
        humidity=45.0,
        hvac_mode="ON",
        target_temp=22.0,
        ota_parameters={"alpha": 0.01, "beta": 0.2},
    )


class OTAUpdateTests(unittest.TestCase):
    def test_topic_matching_supports_building_floor_and_room_targets(self):
        room = make_room()

        self.assertTrue(ota_topic_matches_room("campus/b01/ota/config", room))
        self.assertTrue(ota_topic_matches_room("campus/b01/f05/ota/config", room))
        self.assertTrue(ota_topic_matches_room("campus/b01/f05/r501/ota/config", room))

        self.assertFalse(ota_topic_matches_room("campus/b02/ota/config", room))
        self.assertFalse(ota_topic_matches_room("campus/b01/f04/ota/config", room))
        self.assertFalse(ota_topic_matches_room("campus/b01/f05/r502/ota/config", room))
        self.assertFalse(ota_topic_matches_room("campus/b01/f05/r501/cmd", room))

    def test_matching_rooms_filters_targeted_floor(self):
        rooms = [make_room(5, 501), make_room(5, 502), make_room(6, 601)]

        matches = matching_rooms("campus/b01/f05/ota/config", rooms)

        self.assertEqual([room.room_number for room in matches], [501, 502])

    def test_parse_ota_payload_accepts_version_and_physics_params(self):
        update = parse_ota_payload(
            {
                "version": "1.1",
                "params": {
                    "alpha": 0.015,
                    "beta": 0.25,
                },
            }
        )

        self.assertEqual(update.version, "1.1")
        self.assertEqual(update.params, {"alpha": 0.015, "beta": 0.25})

    def test_parse_ota_payload_rejects_invalid_payloads(self):
        invalid_payloads = [
            {},
            {"params": {"gamma": 1.0}},
            {"params": {"alpha": "fast"}},
            {"params": []},
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    parse_ota_payload(payload)

    def test_apply_ota_update_changes_version_and_room_physics(self):
        room = make_room()

        apply_ota_update(
            room,
            {
                "version": "1.1",
                "params": {
                    "alpha": 0.015,
                    "beta": 0.25,
                },
            },
        )

        self.assertEqual(room.current_version, "1.1")
        self.assertEqual(room.ota_parameters["alpha"], 0.015)
        self.assertEqual(room.ota_parameters["beta"], 0.25)
        self.assertEqual(room.telemetry_payload()["lifecycle"]["current_version"], "1.1")

    def test_signature_verification_catches_tampering(self):
        payload = {
            "version": "1.1",
            "params": {
                "alpha": 0.015,
            },
        }
        signed_payload = dict(payload)
        signed_payload["signature"] = calculate_fingerprint(payload)

        self.assertTrue(verify_fingerprint(signed_payload))

        signed_payload["params"]["alpha"] = 0.02
        self.assertFalse(verify_fingerprint(signed_payload))


if __name__ == "__main__":
    unittest.main()
