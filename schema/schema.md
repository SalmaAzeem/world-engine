## Telemetry

#### Topic: campus/bldg_{building}/floor_{floor:02d}/room_{room}/telemetry

#### metadata
- sensor_id: string (format: b##-f##-r##)
- building: string (e.g., "b01")
- floor: int
- room: int
- timestamp: int (standard unix epoch)

#### sensors
- temperature: float (between 15 and 50)
- humidity: float (between 0 and 100)
- occupancy: boolean
- light_level: int (between 0 and 1000)

#### actuators
- hvac_mode: string (ON, OFF, ECO)
- lighting_dimmer: int (between 0 and 100)

## Command

#### Topic: campus/bldg_{building}/floor_{floor:02d}/room_{room}/command

- command_id: string (e.g., cmd-19828)
- target_device: string (equal to sensor_id - e.g., "b01-f05-r502")
- action: string (set_hvac, set_lighting)
- value: 
  - set_hvac: string (ON, OFF, ECO)
  - set_lighting: int (0-100)
- timestamp: ints