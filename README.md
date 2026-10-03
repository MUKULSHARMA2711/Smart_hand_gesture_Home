# IntelliHome

**IntelliHome** is an AI-powered smart home automation system, built so it can later run on an
**ESP32 + sensors + relays + MQTT**.

**Phase 1 (this release)** is software only. A FastAPI backend simulates the devices
and sensors in memory, and a React dashboard controls them. The device layer is built
so that real ESP32 hardware can later take the simulator's place without changes to the
business logic or the (future) AI layer.

* **Day 1:** virtual devices, home state, structured commands, event log and dashboard.
* **Day 2:** real-time **hand gesture control**. MediaPipe runs in the browser, and
  recognised gestures become device-agnostic intents that go through the same
  `CommandService`. See [Gesture control](#gesture-control-day-2).
* **Day 3:** an **AI home agent** for natural-language control. It plans structured
  actions over explicit device capabilities, and the backend validates them before they
  run through `CommandService`. See [AI home agent](#ai-home-agent-day-3).

```
smart-ai-home/
├── backend/      FastAPI service: devices, home state, commands, events, gestures, AI agent
├── frontend/     React + Vite + Tailwind: dashboard, gesture control (MediaPipe), AI assistant
├── ai/           Reserved for offline AI work (evals, prompt experiments); the agent lives in backend/app/ai
├── vision/       Server-side / offline vision work, e.g. training a gesture model (later)
├── ml/           Models: occupancy prediction, energy forecasting (later)
├── simulation/   Scenario scripts & richer environment simulation (later)
└── docs/         Design notes
```

---

## Architecture

```
     React dashboard · gesture control      (later) AI agent · automations · MQTT bridge
                   │                                 │
                   ▼  HTTP /api/v1                   │  in-process call
┌──────────────────────────────────────────────────────────────────────────────┐
│ API layer        app/api/       routing, request/response schemas, error mapping │
├──────────────────────────────────────────────────────────────────────────────┤
│ Gestures         app/gestures/  GestureService: validate, confidence gate, history │
│                                   │ intent                                     │
│ Domain layer     app/domain/    IntentResolver: intent → device command        │
│                                 CommandService  ◄── the ONE way to change a device │
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
| `gestures/` | Gesture vocabulary and gesture → intent mapping, confidence threshold, gesture policy, gesture history | domain intents, `CommandService` |
| `domain/` | Business rules: execute commands, resolve intents, record events, aggregate home state, meter energy | the `Device`, `SensorProvider` and `EventStore` **abstractions** only |
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
npm run dev        # http://localhost:5173  (gesture control: http://localhost:5173/#/gestures)
npm test           # gesture classifier + stabilizer unit tests (Vitest)
npm run build      # production build in dist/
```

Gesture control needs a webcam and camera permission. Browsers only allow camera access
on `localhost` or HTTPS. The first start downloads the ~7.8 MB hand model from Google's
model storage. The WebAssembly runtime is bundled with the app.

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
| GET | `/api/v1/gestures/config` | Gesture → intent mapping, confidence threshold, blocked actions |
| POST | `/api/v1/gestures/commands` | Execute a recognised gesture on a target device |
| GET | `/api/v1/gestures/events?limit=50` | Gesture history (every attempt, any outcome), newest first |
| POST | `/api/v1/ai/command` | Natural-language request → validated plan → execution |
| GET | `/api/v1/ai/status` | AI provider, allowed intents, per-device capabilities, security policy |
| GET | `/api/v1/ai/history?limit=20` | Recent assistant interactions, newest first |
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

Gesture control already calls, and the AI agent and automations will call,
`CommandService.execute(device_id, command, source=...)`, the same path the dashboard
uses today. They are therefore validated and logged the same way, whether the device is
virtual or real.

---

## Gesture control (Day 2)

```
Browser                                                     Backend
───────                                                     ───────
webcam ─► MediaPipe HandLandmarker ─► 21 hand landmarks
          (WASM + WebGL, local)              │
                                             ▼
                              rule classifier → gesture + confidence
                                             │
                              stabilizer (hold ~0.6 s, ≥ threshold,
                              fire once until released)
                                             │  {gesture, intent, confidence, target_device_id}
                                             └──────► POST /api/v1/gestures/commands
                                                        GestureService
                                                          validate gesture ↔ intent
                                                          confidence ≥ threshold
                                                          IntentResolver: intent + device → command
                                                          gesture policy (blocked actions)
                                                        CommandService (source = "gesture")
                                                        VirtualDevice → DeviceEvent + GestureEvent
```

**Only the recognition result is sent to the server. Video frames never leave the
browser.**

### Gestures and intents

Gestures map to **device-agnostic intents**. The gesture layer never names a device or a
device action. The `IntentResolver` (`app/domain/intents.py`) maps each intent to exactly
one [explicit capability](#capability-model), so voice control and the AI agent reuse the
same rules.

| Gesture | Intent | Light / fan / AC | Door lock |
|---|---|---|---|
| 👍 `THUMBS_UP` | `TURN_ON` | `turn_on` | not applicable (rejected) |
| ✊ `FIST` | `TURN_OFF` | `turn_off` | not applicable (rejected) |
| ✋ `OPEN_PALM` | `STOP` | `turn_off` | not applicable (rejected) |
| ☝️ `ONE_FINGER` | `SELECT` | selects the next device; no device command | same |
| ✌️ `TWO_FINGERS` | `TOGGLE` | `turn_on` ⇄ `turn_off` | not applicable (rejected) |
| `NEUTRAL` / `UNKNOWN` | `NONE` | not actionable | — |

> **Changed in Day 3:** in Day 2, gestures on the door mapped to lock/unlock (for example
> THUMBS_UP locked it). Door locks now only have the `LOCK` and `UNLOCK` capabilities, so
> power intents return `400 intent_not_applicable` for the door.

`NEUTRAL` means no hand is in view. `UNKNOWN` means a hand is visible but no gesture
matched.

**Targeting** is explicit for now: the device selected in the UI, or cycled with
`ONE_FINGER`, is sent as `target_device_id`. AI context reasoning can replace this later
without touching the gesture layer.

**Safety:** no gesture maps to a door intent. `SMARTHOME_GESTURE_BLOCKED_ACTIONS` (default
`["unlock"]`) adds a configurable block list on top, as defence in depth.

### Confidence

* Every result carries `gesture`, `confidence` (0–1) and `intent`.
* Below the threshold (`SMARTHOME_GESTURE_CONFIDENCE_THRESHOLD`, default **0.75**), the
  dashboard still shows the gesture and confidence, marked "below threshold", but
  nothing is sent.
* The backend enforces the same threshold independently and rejects low-confidence
  commands with `422 confidence_below_threshold`. The browser reads the threshold from
  `GET /gestures/config`, so it is defined in one place.

### How MediaPipe runs in the browser

* `frontend/src/gestures/mediapipeRecognizer.js` creates a `HandLandmarker` from
  `@mediapipe/tasks-vision` in `VIDEO` mode for one hand. It uses the GPU (WebGL)
  delegate and falls back to CPU if WebGL is unavailable.
* Vite bundles the WebAssembly runtime (`vision_wasm_internal.{js,wasm}`) and serves it
  from the app itself, so it always matches the installed package version.
* `useGestureRecognition` opens the camera with `getUserMedia` and runs a
  `requestAnimationFrame` loop. Each new video frame goes through `detectForVideo`, the
  classifier and the stabilizer. Landmarks are drawn on a canvas over the mirrored
  preview, and React state updates about 10 times per second.
* The gesture page is lazy-loaded, so the main dashboard never downloads MediaPipe.

### Replacing the classifier

Recognition sits behind a small interface (`frontend/src/gestures/types.js`):

```js
recognize(video, timestampMs) → { gesture, confidence, landmarks }
draw(canvas, result)
```

`ruleClassifier.js` is pure code with no MediaPipe dependency. It scores each finger's
extension from joint angles in MediaPipe's metric 3D *world* landmarks, which makes it
rotation-invariant, then combines those scores per gesture. A trained model (for
example a TF.js classifier on landmarks, or MediaPipe's `GestureRecognizer`) can replace
it, or the whole recognizer, without changes to the hooks, UI or backend.

### Verified

* Unit tests use synthetic 3D hand poses, including rotated hands (`npm test`).
* End to end, MediaPipe's public test photos were fed to a headless browser as a fake
  webcam: `thumb_up`, `fist`, `pointing_up`, `victory`, and an open palm cropped from
  `right_hands`. Each was recognised at 96–98% confidence, executed through
  `CommandService`, and logged with `source=gesture`.
* Live webcam conditions such as lighting, distance and partial hands may need the
  thresholds in `ruleClassifier.js` tuned. The "Finger extension" panel on the gesture
  page shows per-finger scores to help with that.

### Example

```bash
curl -X POST http://localhost:8000/api/v1/gestures/commands \
     -H "Content-Type: application/json" \
     -d '{"gesture":"THUMBS_UP","intent":"TURN_ON","confidence":0.96,"target_device_id":"light_living_room"}'
```

| Case | Status | `error.code` |
|---|---|---|
| Unknown gesture or intent value, confidence outside 0–1, extra fields | 422 | `invalid_request` |
| Intent does not match the gesture (e.g. `THUMBS_UP` + `TURN_OFF`) | 422 | `gesture_intent_mismatch` |
| `NEUTRAL` / `UNKNOWN` | 422 | `gesture_not_actionable` |
| Confidence below threshold | 422 | `confidence_below_threshold` |
| Intent not applicable to the target (e.g. `THUMBS_UP` on the door) | 400 | `intent_not_applicable` |
| Action on the gesture block list (`SMARTHOME_GESTURE_BLOCKED_ACTIONS`) | 403 | `action_blocked` |
| Unknown target device | 404 | `device_not_found` |

Every attempt, including rejections and failures, is stored in the gesture history with
its outcome (`executed`, `acknowledged`, `rejected` or `failed`). Successful device
changes also appear in `/api/v1/events` with `source: "gesture"`.

---

## AI home agent (Day 3)

```
"Turn on the fan and set it to 70"
        │
        ▼
HomeContext ── devices (capabilities + state), sensors, energy, recent events
        │
        ▼
AIProvider.plan()                MockAIProvider (default) or AnthropicProvider (Claude)
  Claude may call read-only tools: get_home_state · get_device_status ·
                                   get_recent_events · get_energy_usage
        │  untrusted JSON: {"message": "...", "actions": [{device_id, intent, parameters}]}
        ▼
ActionPlan / PlannedAction       strict Pydantic models; each action parsed separately
        ▼
PlanValidator                    allowed intent → parameter schema → device exists →
                                 device has the capability → value range (device spec) →
                                 SecurityPolicy → duplicates
        ▼   all actions validated before any executes; rejected ones never run
AgentTools.control_device ──► CommandService (source = "ai_agent") ──► Device
        ▼
AgentResponse: reply · per-action results · device events · changed devices · outcome
```

### How the LLM is kept away from device code

* The model only ever returns **data**: a JSON plan constrained by a schema. It has no
  tool that changes a device. Its only tools are the four read-only ones above, and
  `call_read_only()` refuses any other tool name, `control_device` included.
* The backend re-validates every action with Pydantic. Unknown fields such as
  `"code": "rm -rf /"` are rejected, so are unknown intents and non-object actions.
* Only `HomeAgent`, after validation, calls `AgentTools.control_device`, which is the
  existing `CommandService.execute(..., source=ai_agent)`. There is no second
  device-control path and no second event system.
* The provider SDK is isolated in `app/ai/providers/anthropic_provider.py` and imported
  lazily.

### Capability model

| Device | Capabilities |
|---|---|
| Light | `TURN_ON`, `TURN_OFF`, `SET_BRIGHTNESS` |
| Fan | `TURN_ON`, `TURN_OFF`, `SET_SPEED` |
| AC | `TURN_ON`, `TURN_OFF`, `SET_TEMPERATURE` |
| Door | `LOCK`, `UNLOCK` |

Each device command class declares exactly one capability, and a device's capabilities
are those of the commands its spec lists. Capabilities are returned in every device
payload (`capabilities`) and by `GET /api/v1/ai/status`.

| Intent | Required capability | Parameters |
|---|---|---|
| `TURN_ON` / `TURN_OFF` | `TURN_ON` / `TURN_OFF` | none |
| `SET_BRIGHTNESS` / `SET_SPEED` / `SET_TEMPERATURE` | same name | `{"value": int}`, range checked by the device spec |
| `LOCK_DOOR` / `UNLOCK_DOOR` | `LOCK` / `UNLOCK` | none |
| `GET_STATUS` / `GET_ENERGY` / `GET_HISTORY` | none (read-only) | optional `device_id`; `GET_HISTORY` takes `{"limit": 1-50}` |
| `TOGGLE`, `STOP`, `SELECT` (gesture only) | power capabilities / targeting | not available to the AI agent |

### Why "turn on everything" can never touch the door

There are three independent layers:

1. **Capabilities:** `TURN_ON` requires the `TURN_ON` capability, and the door only has
   `LOCK` and `UNLOCK`. Even if a model emits `{"device_id": "door_main", "intent": "TURN_ON"}`,
   the validator rejects it as `unsupported_capability`.
2. **Separate door intents:** the only way to change a lock is `LOCK_DOOR` or
   `UNLOCK_DOOR`. A broad request can only reach the door if the planner explicitly
   emits one of those intents.
3. **Security policy** (`app/domain/policy.py`): an AI `LOCK_DOOR` or `UNLOCK_DOOR` is
   only allowed when the *user's own message* contains "lock" or "unlock" respectively.
   This is checked in code, not by the LLM. "I'm leaving home" can therefore never lock
   the door, even if the model proposes it; the action is rejected as
   `not_explicitly_requested`. `SMARTHOME_AI_ALLOW_UNLOCK=false` disables AI unlocking
   entirely. The `PolicyDecision` type has room for confirmation or authentication later.

The wording check is **negation-aware**. A "lock"/"unlock" mention only counts if no
negation ("don't", "do not", "never", "not", "won't", …) appears before it in the same
clause. So "don't unlock the door", "never unlock the door" and "I don't want the door
unlocked" are rejected even if the model proposes `UNLOCK_DOOR`. "Don't turn on the
lights and unlock the door" still unlocks, because the negation belongs to the other
clause.

This is a rule-based check, not language understanding: a negation that comes *after*
the verb ("unlock the door… not!") is not detected. A later phase should add explicit
confirmation for door actions.

### Example commands (mock provider)

| You say | Plan | Result |
|---|---|---|
| Turn on the living room light | `TURN_ON light_living_room` | ✓ executed |
| Turn off everything | `TURN_OFF` light, fan, AC | ✓ executed; door untouched, the reply says why |
| I'm leaving home | `TURN_OFF` for devices that are on | door untouched; suggests "lock the front door" |
| Lock the front door / Unlock the front door | `LOCK_DOOR` / `UNLOCK_DOOR door_main` | ✓ executed |
| Turn on the fan and set it to 70 | `TURN_ON` + `SET_SPEED {"value": 70}` | ✓ executed |
| What's happening in my house? | `GET_STATUS` | answered; nothing changes |
| How much energy are we using? | `GET_ENERGY` | answered; nothing changes |
| Turn on the front door | `TURN_ON door_main` | ✗ rejected: `unsupported_capability` |

```bash
curl -X POST http://localhost:8000/api/v1/ai/command \
     -H "Content-Type: application/json" -d '{"message": "Turn on the fan and set it to 70"}'
```

```json
{
  "request": "Turn on the fan and set it to 70",
  "reply": "The Living Room Fan is currently off. I'll turn it on and set its speed to 70%.",
  "outcome": "2 executed.",
  "provider": "mock:rule-based",
  "plan_valid": true,
  "actions": [
    {"index": 0, "device_id": "fan_living_room", "intent": "TURN_ON", "parameters": {}, "status": "executed",
     "device_action": "turn_on", "previous_state": {"is_on": false, "speed": 50}, "new_state": {"is_on": true, "speed": 50}},
    {"index": 1, "device_id": "fan_living_room", "intent": "SET_SPEED", "parameters": {"value": 70}, "status": "executed",
     "device_action": "set_speed", "previous_state": {"is_on": true, "speed": 50}, "new_state": {"is_on": true, "speed": 70}}
  ],
  "device_events": [{"device_id": "fan_living_room", "action": "turn_on", "source": "ai_agent", "...": "..."}, "..."],
  "changed_devices": ["fan_living_room"],
  "any_rejected": false,
  "errors": []
}
```

`reply` is the planner's explanation and is untrusted text. `outcome` and each action's
`status` (`executed`, `answered`, `rejected` or `failed`, plus `code`/`reason`) are
generated by the backend and describe what actually happened.

### Provider configuration

| Setting | Default | Notes |
|---|---|---|
| `SMARTHOME_AI_PROVIDER` / `AI_PROVIDER` | `mock` | `mock` or `anthropic` |
| `SMARTHOME_AI_MODEL` / `AI_MODEL` | `claude-opus-5-5` | Any Claude model id |
| `SMARTHOME_AI_API_KEY` / `AI_API_KEY` | unset | Optional. If unset, the SDK uses `ANTHROPIC_API_KEY` or an `ant auth login` profile |
| `SMARTHOME_AI_EFFORT` | `medium` | `low` … `max` |
| `SMARTHOME_AI_ALLOW_UNLOCK` | `true` | Allow explicit "unlock the front door" through the AI |

**Mock mode** is the default: a deterministic, rule-based planner (`MockAIProvider`) that
needs no key and no network. It receives the same `HomeContext` and returns the same
plan shape as the LLM, so it goes through identical validation. All automated tests use
it or scripted fake providers. No test calls a real LLM.

**Real provider (Claude).** `AnthropicProvider` uses the official `anthropic` SDK with a
manual tool loop. It enables structured outputs (`output_config.format`) so the final
answer is schema-valid JSON, strict read-only tools, and the server-side refusal
fallback (`fallbacks: "default"`). Set it up without committing secrets:

```bash
cd backend
# Either keep the key in your shell…
export ANTHROPIC_API_KEY=...            # PowerShell: $env:ANTHROPIC_API_KEY="..."
# …or in backend/.env, which is git-ignored:  SMARTHOME_AI_API_KEY=...
AI_PROVIDER=anthropic uvicorn app.main:app --port 8000
```

Manual test once a real provider is configured (this calls the paid API):

```bash
curl -s -X POST http://localhost:8000/api/v1/ai/command -H "Content-Type: application/json" \
     -d '{"message": "I am leaving home, lock the front door"}' | python -m json.tool
curl -s http://localhost:8000/api/v1/ai/status      # "provider": "anthropic", "mock": false
```

If the provider is misconfigured (no credentials, a bad profile, network errors), the
dashboard, devices and gestures keep working. The assistant replies "The AI planner is
unavailable, so nothing was changed." and puts the reason in `errors`.

### Frontend

The **AI assistant** tab (`#/assistant`) shows:

* a chat with suggestion chips
* the planner's reply
* the action plan, each action marked ✓ done, ✓ answered or ✗ rejected/failed with the reason
* which devices changed and their new state
* the backend's outcome line
* the active provider, with a mock-mode notice and the safety policy
* recent AI actions, taken from the event log

The dashboard's event log labels every event's source: Dashboard, Gesture, AI agent or
Automation.

---

## Out of scope so far

Voice control, predictive ML, anomaly detection, multi-agent architecture, facial recognition,
authentication, PostgreSQL, and real MQTT/ESP32 hardware communication.
