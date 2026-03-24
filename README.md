# World Engine 

High-concurrency IoT room simulator — 200 rooms, asyncio, MQTT, SQLite.

## Setup

```bash
pip install gmqtt pyyaml
```

## Run

```bash
cd code
python engine.py
```

**Expected output:**
```
DB initialized
Background sync started (30s interval)
[ENGINE] 200 rooms loaded
[MQTT] Connected to broker
# Every 30s:
Synced 200 rooms to DB
# If a room goes silent for >60s:
[WARNING] b01-f01-r101 is OFFLINE (last seen 65s ago)
```

## Verify MQTT (live stream)

Open a second terminal:
```bash
cd code
python subscriber.py
```
You will see continuous JSON telemetry from all 200 rooms on `campus/#`.

## Verify DB Persistence

```bash
python -c "import sqlite3; c=sqlite3.connect('state.db'); print(c.execute('SELECT COUNT(*) FROM room_states').fetchone()); c.close()"
# Expected: (200,)





To scale to **1000 rooms**, only change:
```yaml
floors: 10
rooms_per_floor: 100
```

