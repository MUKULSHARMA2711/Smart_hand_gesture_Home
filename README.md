# IntelliHome

**IntelliHome** is an AI-powered smart home automation system, built so it can later run on an
**ESP32 + sensors + relays + MQTT**.

**Phase 1 (this release)** is software only. A FastAPI backend simulates the devices
and sensors in memory, and a React dashboard controls them. The device layer is built
so that real ESP32 hardware can later take the simulator's place without changes to the
business logic or the (future) AI layer.

```
smart-ai-home/
├── backend/      FastAPI service: devices, home state, commands, events   ← Day 1
├── frontend/     React + Vite + Tailwind dashboard                         ← Day 1
├── ai/           LLM agent (later)
├── vision/       Gesture recognition / MediaPipe (later)
├── ml/           Models: occupancy prediction, energy forecasting (later)
├── simulation/   Scenario scripts & richer environment simulation (later)
└── docs/         Design notes
```

---

## Architecture

```
            React dashboard        (later) AI agent · automations · gestures · MQTT bridge
                   │                                 │
                   ▼  HTTP /api/v1                   │  in-process call
┌──────────────────────────────────────────────────────────────────────────────┐
│ API layer        app/api/       routing, request/response schemas, error mapping │
├──────────────────────────────────────────────────────────────────────────────┤
│ Domain layer     app/domain/    CommandService  ◄── the ONE way to change a device │
│                                 HomeState (devices + sensors + energy)        │
├───────────────────────────┬──────────────────────────┬───────────────────────┤
│ Device abstraction        │ Sensors                  │ Events                │
│ app/devices/              │ app/sensors/             │ app/events/           │
│  Device (ABC)             │  SensorProvider (ABC)    │  DeviceEvent          │
│  DeviceSpec per type      │                          │  CommandSource enum   │
│  DeviceRegistry, factory  │                          │  EventStore (ABC)     │
├───────────────────────────┼──────────────────────────┼───────────────────────┤
│ Implementations           │                          │                       │
│  virtual/  VirtualLight…  │  SimulatedSensorProvider │  InMemoryEventStore   │
│  (later) ESP32MQTTDevice  │  (later) MQTT sensors    │  (later) PostgreSQL   │
└───────────────────────────┴──────────────────────────┴───────────────────────┘
        Wiring: app/container.py (composition root) · Config: app/config.py
```

| Layer | Responsibility | Knows about |
|---|---|---|
| `api/` | HTTP only: parse requests, call domain services, map errors to status codes | domain, device snapshots |
| `domain/` | Business rules: execute commands, record events, aggregate home state, meter energy | the `Device`, `SensorProvider` and `EventStore` **abstractions** only |
| `devices/` | The `Device` contract, the per-type `DeviceSpec`s, the registry, and the factory that picks an implementation | — |
| `devices/virtual/` | In-memory simulation of each device's firmware | specs |
| `sensors/` | Environmental readings (temperature, humidity, occupancy, light) | — |
| `events/` | Event model, the `CommandSource` enum, and event storage | — |
| `config.py` / `container.py` | Settings and wiring; the only place concrete classes are chosen | everything |

### The key design decision: spec vs implementation

Each device type has a **`DeviceSpec`** (`app/devices/specs/`). It defines the state
shape and the commands the type accepts, each command being a Pydantic model with its
own value limits. A spec does **not** depend on how the device is connected.

```
Device (ABC)  ── execute_command(): validate via spec → _perform() → return previous/new state
├── VirtualDevice      _perform() = apply a pure state transition in memory
└── ESP32MQTTDevice    _perform() = publish to MQTT, await the device's state report   (later)
```

This means:

* A virtual light and an ESP32 light accept **exactly** the same commands and return
  the same errors, because validation is shared.
* An implementation only answers *how* to carry out an already-validated command.
* `execute_command` is `async` today, so waiting for an MQTT acknowledgement later
  will not change the interface.
* Clients discover what each device accepts from `supported_commands` in the device
  payload (action plus min/max). The dashboard reads its slider limits from there, and
  the AI agent will be able to do the same.

### Command flow

```
POST /devices/light_living_room/command {"action":"set_brightness","value":70}
  → CommandService.execute(device_id, DeviceCommand, source=frontend)
      → DeviceRegistry.get()                    404 device_not_found
      → Device.execute_command()
          → DeviceSpec.parse_command()          400 unsupported_command / 422 invalid_command
          → VirtualLight._perform()             state: brightness 100 → 70
      → DeviceEvent(previous_state, new_state, source) → EventStore
  ← { event, device }
```

---

## Setup

Requirements: **Python 3.12+** and **Node.js 20.19+ / 22.12+**.

### Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run it:

```bash
uvicorn app.main:app --reload --port 8000
```

* API: <http://localhost:8000/api/v1>
* Interactive docs (Swagger): <http://localhost:8000/docs>

Run the tests:

```bash
pytest -v
```

Optional configuration: copy `backend/.env.example` to `backend/.env`. All variables use
the `SMARTHOME_` prefix. Examples are CORS origins, the event log size, a simulated
device latency (`SMARTHOME_VIRTUAL_DEVICE_LATENCY_MS=150` is useful for seeing loading
states), and a fixed sensor seed.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The frontend calls `http://localhost:8000/api/v1` by default. To change it, copy
`frontend/.env.example` to `frontend/.env` and set `VITE_API_BASE_URL`.

The dashboard polls the home state every 5 s, which keeps sensor values moving. After
every command it re-fetches state and events immediately.

---

## API

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service info: name, status, and links to the docs and the API |
| GET | `/api/v1/home/state` | Environment readings, energy, and all devices |
| GET | `/api/v1/devices` | All devices |
| GET | `/api/v1/devices/{device_id}` | One device |
| POST | `/api/v1/devices/{device_id}/command` | Execute a structured command |
| GET | `/api/v1/events?limit=50&device_id=…` | Recent events, newest first |
| GET | `/api/v1/health` | Liveness check |

### Devices and commands

| Device id | Type | Actions | State |
|---|---|---|---|
| `light_living_room` | `light` | `turn_on`, `turn_off`, `set_brightness` (0–100) | `is_on`, `brightness` |
| `fan_living_room` | `fan` | `turn_on`, `turn_off`, `set_speed` (0–100) | `is_on`, `speed` |
| `ac_bedroom` | `ac` | `turn_on`, `turn_off`, `set_temperature` (16–30 °C, integer) | `is_on`, `target_temperature_c` |
| `door_main` | `door_lock` | `lock`, `unlock` | `is_locked` |

Values must be integers: `70.5`, `"70"` and `true` are all rejected. Sending a `value`
with a command that takes none is also rejected.

### Examples

```bash
# Full home snapshot
curl http://localhost:8000/api/v1/home/state

# Turn the light on
curl -X POST http://localhost:8000/api/v1/devices/light_living_room/command \
     -H "Content-Type: application/json" -d '{"action": "turn_on"}'

# Dim it to 70 %
curl -X POST http://localhost:8000/api/v1/devices/light_living_room/command \
     -H "Content-Type: application/json" -d '{"action": "set_brightness", "value": 70}'

# Set the AC to 22 °C
curl -X POST http://localhost:8000/api/v1/devices/ac_bedroom/command \
     -H "Content-Type: application/json" -d '{"action": "set_temperature", "value": 22}'

# Unlock the door (source is optional, defaults to "frontend")
curl -X POST http://localhost:8000/api/v1/devices/door_main/command \
     -H "Content-Type: application/json" -d '{"action": "unlock", "source": "frontend"}'

# Last 10 events for the light
curl "http://localhost:8000/api/v1/events?limit=10&device_id=light_living_room"
```

Successful command response (`200`):

```json
{
  "event": {
    "event_id": "a5f266a2-295d-452a-8344-59c1dec54135",
    "timestamp": "2026-10-02T22:40:45.111980Z",
    "device_id": "light_living_room",
    "action": "set_brightness",
    "value": 70,
    "previous_state": { "is_on": true, "brightness": 100 },
    "new_state": { "is_on": true, "brightness": 70 },
    "source": "frontend"
  },
  "device": { "id": "light_living_room", "state": { "is_on": true, "brightness": 70 }, "power_w": 6.6, "...": "..." }
}
```

Errors always use the same envelope:

| Case | Status | `error.code` |
|---|---|---|
| Unknown device | 404 | `device_not_found` |
| Action not supported by the device (e.g. `turn_on` on the door) | 400 | `unsupported_command` |
| Invalid value (brightness 150, AC 35 °C, missing value…) | 422 | `invalid_command` |
| Malformed body (missing `action`, unknown field, bad `source`) | 422 | `invalid_request` |

```json
{
  "error": {
    "code": "invalid_command",
    "message": "Invalid 'set_brightness' command for device 'light_living_room': value: Input should be less than or equal to 100",
    "details": { "device_id": "light_living_room", "action": "set_brightness",
                 "errors": [{ "field": "value", "message": "Input should be less than or equal to 100" }] }
  }
}
```

Only successful commands produce events. Event `source` is one of `frontend`,
`automation`, `gesture`, `ai_agent` or `mqtt`.

---

## How the virtual devices work

* Each virtual device (`app/devices/virtual/`) holds its state as a Pydantic model and
  implements `apply(state, command) -> new_state`. This is a pure function that mimics
  how the firmware would respond:
  * **Light / fan:** `set_brightness`/`set_speed` with `0` turns the device off, and any
    value above 0 turns it on. `turn_on` resumes the previous level.
  * **AC:** `set_temperature` changes the set point even while the AC is off, as a
    real remote does.
  * **Door:** `lock` / `unlock`. The door starts locked.
* **Power** is estimated from state: an LED bulb draws up to ~9 W, a ceiling fan
  12–60 W, and an inverter AC ~700 W plus 70 W per degree below 30 °C. Standby draw is
  modelled for all devices. `EnergyMeter` integrates this into kWh. Because power only
  changes on commands, the meter is sampled before every command and on every read.
* **Sensors** (`SimulatedSensorProvider`) follow a daily cycle: temperature is
  ~22 °C before dawn and ~30 °C mid-afternoon, humidity moves inversely, and ambient
  light follows daylight hours. Mean-reverting noise is added, and occupancy
  occasionally changes by one person.
* **Optional latency** (`SMARTHOME_VIRTUAL_DEVICE_LATENCY_MS`) simulates the network
  round trip.
* Which class backs each device is declared in `app/config.py`:

  ```python
  DeviceConfig(id="light_living_room", name="Living Room Light",
               type=DeviceType.LIGHT, room="living_room", driver=DeviceDriver.VIRTUAL)
  ```

---

## Path to ESP32 + MQTT

Nothing in `domain/`, `api/` or the future `ai/` layer imports a virtual device. Moving
to hardware takes four additive steps:

1. **Add a driver.** Add `ESP32_MQTT = "esp32_mqtt"` to `DeviceDriver`, and write
   `app/devices/mqtt/esp32_device.py`. It reuses the existing spec, so validation is
   unchanged:

   ```python
   class ESP32MQTTDevice(Device):
       def __init__(self, device_id, name, room, spec, mqtt, ack_timeout_s=3.0):
           super().__init__(device_id, name, room, spec)
           self._mqtt, self._state, self._online = mqtt, spec.state_model(), False
           mqtt.subscribe(f"home/{device_id}/state", self._on_state_report)
           mqtt.subscribe(f"home/{device_id}/availability", self._on_availability)

       @property
       def status(self):        # driven by the ESP32's LWT / availability topic
           return DeviceStatus.ONLINE if self._online else DeviceStatus.OFFLINE

       def get_state(self):     # last state the firmware reported (retained message)
           return self._state.model_dump()

       async def _perform(self, command):
           await self._mqtt.publish(f"home/{self.id}/set", command.model_dump_json(), qos=1)
           await self._wait_for_state_report(timeout=self._ack_timeout_s)
   ```

2. **Register it in the factory** (`app/devices/factory.py`), then switch one device's
   config to `driver=DeviceDriver.ESP32_MQTT`. Virtual and real devices can run side by
   side, which is useful for bringing up hardware one relay at a time.
3. **Sensors.** Implement `MqttSensorProvider(SensorProvider)` to cache the latest
   DHT22, PIR and LDR readings from `home/sensors/#`, and swap it in
   `app/container.py`.
4. **Physical changes.** When someone presses a wall switch, the ESP32 publishes a new
   state. The MQTT bridge records it as a `DeviceEvent` with `source=mqtt`. That source
   value already exists.

Proposed topic contract (JSON payloads use the same field names as the API):

| Topic | Direction | Payload |
|---|---|---|
| `home/{device_id}/set` | backend → ESP32 | `{"action": "set_brightness", "value": 70}` |
| `home/{device_id}/state` (retained) | ESP32 → backend | `{"is_on": true, "brightness": 70, "power_w": 6.6}` |
| `home/{device_id}/availability` (LWT) | ESP32 → backend | `online` / `offline` |
| `home/sensors/{room}` | ESP32 → backend | `{"temperature_c": 26.1, "humidity_pct": 58, ...}` |

The AI agent, automations and gesture control will all call
`CommandService.execute(device_id, command, source=...)`, the same path the dashboard
uses today. They are therefore validated and logged the same way, whether the device is
virtual or real.

---

## Out of scope for Day 1

LLM / AI agent, gesture recognition (MediaPipe), machine learning, authentication,
PostgreSQL, and real MQTT hardware communication.
