import requests, time

TB_URL = "http://localhost:9090"
USERNAME = "tenant@thingsboard.org"
PASSWORD = "tenant"

def get_token():
    r = requests.post(f"{TB_URL}/api/auth/login",
                      json={"username": USERNAME, "password": PASSWORD})
    return r.json()["token"]

def make_headers(token):
    return {"X-Authorization": f"Bearer {token}",
            "Content-Type": "application/json"}

def get_entity_id(name, entity_type, headers):
    if entity_type == "DEVICE":
        r = requests.get(f"{TB_URL}/api/tenant/devices?deviceName={name}", headers=headers)
    else:
        r = requests.get(f"{TB_URL}/api/tenant/assets?assetName={name}", headers=headers)
    data = r.json()
    if "id" not in data:
        return None
    return data["id"]["id"]

def get_latest_temperature(device_id, headers):
    r = requests.get(
        f"{TB_URL}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries?keys=temperature",
        headers=headers
    )

    data = r.json()

    if "temperature" not in data or not data["temperature"]:
        return None

    value = data["temperature"][0].get("value")

    if value is None:
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        print(f"Invalid temperature value for device {device_id}: {value}")
        return None

def post_asset_telemetry(asset_id, payload, headers):
    requests.post(
        f"{TB_URL}/api/plugins/telemetry/ASSET/{asset_id}/timeseries/SERVER_SCOPE",
        headers=headers,
        json=payload
    )

# --- NEW: Sync functions ---

def get_device_attributes(device_id, scope, headers):
    r = requests.get(
        f"{TB_URL}/api/plugins/telemetry/DEVICE/{device_id}/values/attributes/{scope}",
        headers=headers
    )
    if r.status_code != 200:
        return {}
    return {item["key"]: item["value"] for item in r.json()}

def set_device_server_attributes(device_id, attrs, headers):
    requests.post(
        f"{TB_URL}/api/plugins/telemetry/DEVICE/{device_id}/attributes/SERVER_SCOPE",
        headers=headers,
        json=attrs
    )

def check_and_update_sync(device_id, headers):
    shared = get_device_attributes(device_id, "SHARED_SCOPE", headers)
    client = get_device_attributes(device_id, "CLIENT_SCOPE", headers)

    desired_hvac    = shared.get("desired_hvac")
    reported_hvac   = client.get("reported_hvac")
    desired_dimmer  = shared.get("desired_dimmer")
    reported_dimmer = client.get("reported_dimmer")

    hvac_in_sync   = (desired_hvac == reported_hvac)
    dimmer_in_sync = (desired_dimmer == reported_dimmer)
    overall_in_sync = hvac_in_sync and dimmer_in_sync

    set_device_server_attributes(device_id, {
        "sync_status":      "IN_SYNC" if overall_in_sync else "OUT_OF_SYNC",
        "desired_hvac":     desired_hvac,
        "reported_hvac":    reported_hvac,
        "desired_dimmer":   desired_dimmer,
        "reported_dimmer":  reported_dimmer
    }, headers)

    return overall_in_sync

# --- Cache ---

def build_cache(headers):
    cache = {}
    # flat list of all device IDs for sync checking
    all_devices = []

    for f in range(1, 11):
        floor_name = f"B01-F{f:02d}"
        floor_id = get_entity_id(floor_name, "ASSET", headers)
        cache[floor_name] = {"floor_id": floor_id, "devices": []}

        for offset in range(10):
            mqtt_room_num = f * 100 + offset + 1
            coap_room_num = f * 100 + offset + 101

            for dev_name in [f"MQTT-F{f:02d}-R{mqtt_room_num}",
                             f"CoAP-F{f:02d}-R{coap_room_num}"]:
                dev_id = get_entity_id(dev_name, "DEVICE", headers)
                if dev_id:
                    cache[floor_name]["devices"].append(dev_id)
                    all_devices.append(dev_id)

        print(f"Cached {floor_name}: {len(cache[floor_name]['devices'])} devices")

    return cache, all_devices

# --- Main loop ---

def run():
    print("Waiting for ThingsBoard...")
    while True:
        try:
            token = get_token()
            break
        except Exception as e:
            print(f"TB not ready: {e}, retrying in 10s...")
            time.sleep(10)

    headers = make_headers(token)
    print("Building ID cache...")
    cache, all_devices = build_cache(headers)
    print(f"Cache ready. {len(all_devices)} devices total. Starting loop.")

    while True:
        try:
            token = get_token()
            headers = make_headers(token)

            # 1. Floor average temperature
            for floor_name, data in cache.items():
                if not data["floor_id"]:
                    continue
                temps = []
                for dev_id in data["devices"]:
                    t = get_latest_temperature(dev_id, headers)
                    if t is not None:
                        temps.append(t)

                if temps:
                    avg = round(sum(temps) / len(temps), 2)
                    post_asset_telemetry(data["floor_id"], {"avg_temperature": avg}, headers)
                    print(f"{floor_name}: avg_temperature = {avg} ({len(temps)}/20 rooms)")

            # 2. Sync status check for all 200 devices
            out_of_sync_count = 0
            for dev_id in all_devices:
                in_sync = check_and_update_sync(dev_id, headers)
                if not in_sync:
                    out_of_sync_count += 1

            print(f"Sync check done: {out_of_sync_count}/{len(all_devices)} devices OUT_OF_SYNC")

        except Exception as e:
            print(f"Error in loop: {e}")

        time.sleep(60)

if __name__ == "__main__":
    run()