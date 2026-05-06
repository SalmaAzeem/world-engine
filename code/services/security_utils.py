import hashlib
import json

def calculate_fingerprint(data: dict) -> str:
    encoded_data = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded_data).hexdigest()

def verify_fingerprint(data: dict) -> bool:
    if not isinstance(data, dict) or "signature" not in data:
        return False
    
    data_copy = dict(data)
    received_sig = data_copy.pop("signature")
    expected_sig = calculate_fingerprint(data_copy)
    
    return received_sig == expected_sig
