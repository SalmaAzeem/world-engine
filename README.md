# World Engine

Phase 2 hybrid campus simulator for the course project.

The repo now contains:

- a Python `asyncio` world engine
- 100 MQTT nodes using `gmqtt`
- 100 CoAP nodes using `aiocoap`
- Docker orchestration for HiveMQ, ThingsBoard, the engine, and 10 floor gateways

## Local Python Run

```bash
pip install -r requirements.txt
cd code
python engine.py
```

This uses the defaults in `code/config.yaml`, which target a local broker on `127.0.0.1:1883`.

## Phase 2 Docker Stack

The compose stack is designed to be the integration base for all four teammates:

- `hivemq`: campus MQTT backbone
- `postgres` + `thingsboard-ce`: cloud layer / dashboard backend
- `engine`: hybrid MQTT and CoAP world engine
- `gateway-f01` to `gateway-f10`: floor-level Node-RED gateways
- `subscriber`: optional debug-only MQTT consumer

## First Run

1. Start PostgreSQL first:

```bash
docker compose up -d postgres
```

2. Initialize ThingsBoard database and built-in assets:

```bash
docker compose run --rm -e INSTALL_TB=true -e LOAD_DEMO=false thingsboard-ce
```

3. Start the full stack:

```bash
docker compose up -d --build
```

4. Optional debug subscriber:

```bash
docker compose --profile debug up -d subscriber
```

## Main Endpoints

- HiveMQ MQTT: `localhost:1883`
- ThingsBoard UI: `http://localhost:9090`
- Node-RED Floor 01 UI: `http://localhost:1891`
- Node-RED Floor 10 UI: `http://localhost:1900`

## Integration Notes by Role

### Member 1

- engine logic lives under `code/`
- MQTT/CoAP split is handled in `code/fleet.py`
- shared room physics is in `code/models/room_state.py`
- config can now be driven by YAML or Docker environment variables

### Member 2

- floor gateway data folders live under `infra/nodered/`
- CoAP room-to-port mapping is documented in `infra/coap_port_map.md`

### Member 3

- ThingsBoard bootstrap notes are in `infra/thingsboard/README.md`

### Member 4

- HiveMQ / security handoff notes are in `infra/hivemq/README.md` and `infra/security/README.md`
- benchmark helper is `benchmark.sh`

## Notes

- The compose stack is integration-ready, not final-production-complete.
- TLS, DTLS, HiveMQ ACL enforcement, Node-RED flows, and ThingsBoard device provisioning are intentionally left as teammate-owned follow-up work.
