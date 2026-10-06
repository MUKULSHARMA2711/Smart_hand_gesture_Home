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
* **Day 4:** a **3D command center**: a live digital twin of the house (React Three
  Fiber) with an AI core, command beams, energy analytics and an activity console, all
  driven by real backend state. See [3D command center](#3d-command-center-day-4).
* **Phase 5:** **machine learning**: Random Forest fan-usage prediction and Isolation Forest
  energy anomaly detection, explained by the AI agent and shown in the 3D UI. See
  [Machine Learning Intelligence](#machine-learning-intelligence).
* **Day 6:** **hardening**: one error format everywhere, failure isolation between the AI,
  ML, sensors and device control, and a tested failure matrix. See
  [Reliability and Failure Handling](#reliability-and-failure-handling).
* **Phase 7:** **hardware readiness**: an MQTT driver for ESP32 devices with command
  acknowledgements, timeouts, availability (Last Will) and fresh-only sensor data, tested
  end to end against a Fake ESP32. No physical hardware is required. See
  [MQTT Hardware Architecture](#mqtt-hardware-architecture).

```
smart-ai-home/
├── backend/      FastAPI service: devices, home state, commands, events, gestures, AI agent
├── frontend/     React + Vite + Tailwind + R3F: 3D command center, gestures (MediaPipe), AI assistant
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
| GET | `/api/v1/ml/status` · POST `/api/v1/ml/predict` | ML models and fan-usage prediction |
| GET | `/api/v1/ml/anomalies` · POST `/api/v1/ml/anomalies/check` | Energy anomaly detection |
| GET | `/api/v1/iot/status` | MQTT connection, device availability, sensor freshness |
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

# Unlock the door (source is optional; this endpoint only accepts "frontend")
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
| Malformed body (missing `action`, unknown field, `source` other than `frontend`) | 422 | `invalid_request` |

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
`automation`, `gesture`, `ai_agent`, `mqtt` or `ml` (observations only). The direct device
endpoint always records `frontend`: gesture and AI commands must go through
`/gestures/commands` and `/ai/command`, so a client cannot bypass their checks or forge the
audit trail.

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

Implemented in Phase 7: see [MQTT Hardware Architecture](#mqtt-hardware-architecture).
Gesture control, the AI agent and the dashboard all call
`CommandService.execute(device_id, command, source=...)`, so they are validated and logged
the same way whether a device is virtual or an ESP32.

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
the verb ("unlock the door… not!") is not detected. That is why unlocking also needs an
explicit confirmation.

### Voice: "Hey IntelliHome"

On the AI assistant page, **Enable voice** turns on hands-free control in browsers with
the Web Speech API (Chrome, Edge).

1. Say "Hey IntelliHome, turn on the living room fan", or say "Hey IntelliHome" and then
   the request within 8 s.
2. The recognised text goes to the same `POST /ai/command` pipeline as typed requests, so
   it gets the same validation, door policy and CommandService path. There is no separate
   execution path.
3. The reply is spoken with `speechSynthesis`, built from the backend's actual results
   ("Done. Living Room Fan is now on."), never from the planner's own text.
4. A held door unlock is answered without the wake phrase ("yes, unlock it" or "cancel").

The microphone pauses while a request is processed and while the reply is spoken, so the
assistant never hears itself. Voice stops when it is turned off, when you leave the page,
when the microphone is denied, on recognition errors, and if the browser keeps ending the
session. A command window that gets no request returns to waiting for the wake phrase. In
unsupported browsers the panel says so; typing and gestures still work.

**Privacy:** IntelliHome receives only the recognised text. The browser does the
recognition; in Chrome and Edge that uses the browser vendor's online speech service, which
the panel states. The gesture camera is not touched: voice runs on the assistant page, the
camera on the gesture page.

The logic is in `frontend/src/voice/voiceSession.js`; its tests cover the wake flow,
timeouts, denial, failures, restart limits and cleanup.

### Unlocking needs an explicit confirmation

An explicit, non-negated AI request to unlock ("unlock the main door") is **held**, not
executed:

1. The policy marks the action `requires_confirmation`, and the agent replies "Are you sure
   you want to unlock the Main Door? Say 'yes, unlock it' to confirm, or 'cancel'." The
   action has status `awaiting_confirmation`, and the response carries a `confirmation`
   (id, prompt, `expires_at`).
2. **Confirm:** reply "yes, unlock it" (or "confirm"), or press **Confirm unlock**, which
   calls `POST /api/v1/ai/confirmations/{id}` with `{"decision": "confirm"}`. The action is
   re-validated (device, capability, policy) and executed once, through the normal
   CommandService path (`source=ai_agent`).
3. **Cancel:** say any negation or cancel word ("no", "cancel", "don't unlock it"), or
   press **Cancel**. A bare "yes" is not enough: the assistant repeats the exact phrase and
   keeps waiting.
4. **Expiry:** after `SMARTHOME_AI_CONFIRMATION_TIMEOUT_S` (default 30 s) the unlock is
   cancelled. A late "yes, unlock it" is answered with "expired", and the button returns
   `410 confirmation_expired`.
5. **Other requests:** any other request drops the pending unlock.

Locking needs no confirmation. Gestures still cannot unlock. The direct dashboard control
is the user's own action and is unchanged.
`SMARTHOME_AI_UNLOCK_REQUIRES_CONFIRMATION=false` restores immediate execution of explicit
requests; `SMARTHOME_AI_ALLOW_UNLOCK=false` still forbids AI unlocking entirely.

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

## 3D command center (Day 4)

Day 4 changes only the frontend. The backend, `CommandService`, the AI agent and the
gesture stabilizer are untouched.

| Page | What it shows |
|---|---|
| **Home** (`#/`) | Live 3D digital twin, AI core, sensor readout, "Ask IntelliHome" bar, device inspector, home status checks, live event stream, device controls |
| **Gesture** (`#/gestures`) | The Day 2 camera/MediaPipe UI, plus a 3D preview with the selected target and gesture → device beams |
| **AI assistant** (`#/assistant`) | Chat, a 3D view with command beams, and the request lifecycle (request → understanding → context → plan → validation → execution → result) |
| **Energy** (`#/energy`) | Current, peak and average power, a power-over-time chart, per-device bars, and the anomaly status |
| **Activity** (`#/activity`) | One stream of device events, gesture events and AI interactions, with filters, plus the device event table |

### Real state drives the scene

```
FastAPI ──poll every 5 s / refresh after each command──► HomeDataProvider (useHomeDashboard)
                                                              │ devices, sensors, energy, events
                                                              ▼
                       AssistantProvider ─► useDisplayDevices() ─► SmartHomeScene (props only)
                                                                    Light3D · Fan3D · AC3D · Door3D
```

The scene keeps **no device state of its own**. Each device component receives the
backend snapshot as a prop and derives its visuals through pure functions in
`components/3d/visualState.js`, which are unit-tested:

| Backend state | Visual |
|---|---|
| light `is_on`, `brightness` 0–100 | bulb glow, point-light intensity and floor glow; `level = 0.12 + 0.88 × brightness/100`, 0 when off |
| fan `is_on`, `speed` 0–100 | blade angular velocity 2–24 rad/s (multiplier `speed/100`), smooth spin-up and spin-down; stopped when off |
| AC `is_on`, `target_temperature_c` | cool-air particles only while on (colder set points blow harder and bluer); the real set point is shown on the unit |
| door `is_locked` | closed with a green indicator when locked; ajar with amber when unlocked |

Animations only *smooth toward* the backend value. They never decide it.

### Commands from the 3D UI

```
click device in 3D ──► DeviceInspector (capabilities + controls)
                              │ sendCommand(id, action, value)    (existing API client)
                              ▼
            POST /api/v1/devices/{id}/command ─► CommandService ─► device
                              │ success response
                              ▼
            refresh() ─► new backend state ─► scene re-renders, plus a confirmation pulse
```

Nothing changes visually until the backend confirms. Effects (`CommandFxContext`) are
only emitted from real API responses:

* AI action results: executed → beam, rejected → red fizzle
* gesture results: beam from the gesture input
* dashboard commands: device pulse

### AI core and command beams

`<AIOrb state=…/>` supports `idle`, `listening`, `thinking`, `planning`, `executing`,
`success` and `error`. The state comes from `state/aiLifecycle.js`, a tested reducer
driven by real events:

* **idle**: nothing in progress.
* **listening**: the assistant input is focused, or the gesture camera is running.
* **thinking**: the HTTP request is in flight. This is the only real wait.
* **planning** (~0.7 s): the backend response has arrived and its plan is shown.
* **executing**: one beam per device-targeting result, about 0.55 s apart, in plan order.
* **success** or **error**: derived from the real results, for example error if
  everything was rejected or failed.

While beams are in flight, each targeted device is drawn with the backend's own
`previous_state` for that action. It switches to `new_state` when its beam lands, so in
"turn on the light and turn off the fan" the light visibly changes first, then the fan.
Both states come from the response. Live polled state takes over once every beam has
landed.

The door is only touched if the backend plan contains a valid explicit `LOCK_DOOR` or
`UNLOCK_DOOR`. "I'm leaving home" turns off appliances and leaves the door alone,
because that is what the backend returns.

### Honest data

* **Home status** shows verifiable checks only: devices online, door security, sensor
  freshness, plus power information. There is no invented "intelligence score".
  Anomaly detection is labelled "Not available yet".
* **Energy history** is sampled by the browser from the same 5 s polls; the backend
  stores no history. The page says so, and the chart starts when the page is opened.
* **Home context** in the lifecycle view is built server-side and is not returned by the
  API. The UI labels what it shows as the dashboard's snapshot at send time.

### Performance and accessibility

* three.js, R3F and drei load lazily, only when a page shows the house: a ~262 kB gzip
  chunk. MediaPipe still loads only on the gesture page.
* The geometry is procedural, with no model or texture downloads. Glow uses additive
  sprites from a code-generated texture instead of a postprocessing pass. Instanced
  meshes draw the particles.
* Particles and orb effects are only mounted in the states that use them. The render
  loop pauses when the canvas scrolls out of view. DPR is capped at 1.75.
* `prefers-reduced-motion` disables spinning, particles and beams and renders on demand.
  Device state is still shown through labels and lighting.
* Without WebGL (or if the scene fails), a clickable 2D floor plan with the same live
  state replaces the 3D view.

### Tests

`npm test` covers the backend → visual mappings, the AI lifecycle reducer, home status
checks, energy history, the activity feed merge and the pipeline stages. The Day 2
classifier and stabilizer tests are unchanged.

---

## Machine Learning Intelligence

> **Current training data is simulated, because physical hardware is not yet available.**
> Both models are trained at startup on deterministic data generated from IntelliHome's own
> sensor and device models. The metrics below describe that simulation, not real-world
> accuracy. With real sensor history, the same pipeline retrains on real data.

```
PREDICTION   HomeState ─► features.py ─► Random Forest ─► Prediction ─► AI explains (recommendation only)
ANOMALY      device power + setting ─► Isolation Forest ─► AnomalyResult ─► event (source=ml) ─► AI explains
EXECUTION    only explicit user requests ─► AI action plan ─► validation ─► CommandService ─► device
```

The ML layer lives in `backend/app/ml/` (`features`, `dataset`, `prediction`, `anomaly`,
`service`, `models`). It does not depend on FastAPI, React, device implementations or
`CommandService`. **ML recommends and detects; the AI or the user decides; `CommandService`
executes.** The API also refuses device commands that claim `source: "ml"`.

### Predictive automation: `random_forest_v1`

| | |
|---|---|
| Target | `FAN_ON_SOON`: will the living-room fan be on within the next 30 minutes? |
| Model | `RandomForestClassifier`, 120 trees, max depth 8 |
| Features | hour, day of week, temperature, humidity, occupied, occupant count, ambient light, fan on now, fan used in the last 30 minutes |
| Data | 60 simulated days at 15-minute steps (5,757 samples, 28.8% positive), seed 7 |
| Simulation | Same daily temperature, humidity and daylight cycle as the sensor simulator, with hotter and cooler days; weekday/weekend occupancy schedule; comfort-driven fan use (hot, humid, occupied → fan more likely; less use at night) |

Evaluation on a stratified 25% held-out split (1,440 samples):

| Accuracy | Majority baseline | Precision | Recall | F1 | Confusion matrix [[TN, FP], [FN, TP]] |
|---|---|---|---|---|---|
| 87.4% | 71.3% | 82.1% | 72.0% | 0.767 | [[961, 65], [116, 298]] |

Most important features: fan on now (0.31), temperature (0.22), fan used recently (0.15),
humidity (0.10).

**Explainability.** Each prediction lists its inputs and how much each one moved the
probability: the model is re-run with that input set to its typical (median) value. The
response says, for example: *"Random Forest predicted a 83% probability that the Living Room
Fan will be needed within 30 minutes. Main factors: Temperature 30.0 °C (typical 25.6 °C);
…"*. Missing inputs are imputed with the training median and listed in `missing_features`.

### Energy anomaly detection: `isolation_forest_v1`

One `IsolationForest` per device type, trained on **(setting level, watts)**. The setting
level is 0 when the device is off and 10–100 when it is on (brightness, speed, or how cold
the AC set point is). Normal readings come from the existing virtual-device power models
plus about 3% meter noise. About 2% of the training data is injected faults: surges
(×2.2–4), stalls (power near zero while running) and phantom draw (power while off).

* The alarm threshold is learned so that 99.8% of normal training readings pass. A reading
  is anomalous when its score falls below it; `score < 0` means anomalous.
* The **normal range** reported with each result is the 0.5–99.5th percentile of normal
  readings at that setting. For example, the fan at speed 60 is normal at 34.6–42.5 W.
* All 168 legitimate virtual-device states are classified as normal (tested), so live
  devices never raise false alarms.

Held-out evaluation (30% split, 750 readings and 15 injected faults per device):

| Device | Precision | Recall | F1 | False-alarm rate |
|---|---|---|---|---|
| Light | 92.3% | 80.0% | 0.857 | 0.14% |
| Fan | 100% | 80.0% | 0.889 | 0.00% |
| AC | 86.7% | 86.7% | 0.867 | 0.27% |
| Door lock | 93.8% | 100% | 0.968 | 0.14% |

Virtual devices always report their modelled power, so in the simulation real anomalies
only arrive as **reported readings** (`POST /api/v1/ml/anomalies/check`), which is how a
future hardware power meter will feed the system. The Energy page has a small form for
submitting one. Every anomaly is recorded in the existing event log as
`event_type: "energy_anomaly"`, `source: "ml"`, with the score and normal range in `details`.

### API

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/ml/status` | Model versions, evaluation metrics, feature importances, data note |
| POST | `/api/v1/ml/predict` | `{}` derives features from live HomeState; optional `{"features": {...}}` overrides (`null` = missing) |
| GET | `/api/v1/ml/anomalies` | Live per-device assessment plus recent and active anomalous readings |
| POST | `/api/v1/ml/anomalies/check` | Assess `{"device_id", "power_w"}`; anomalies are logged as events |

```bash
curl -s -X POST localhost:8000/api/v1/ml/predict -H "Content-Type: application/json" -d '{}'
curl -s -X POST localhost:8000/api/v1/ml/anomalies/check -H "Content-Type: application/json" \
     -d '{"device_id": "fan_living_room", "power_w": 170}'
```

### AI integration

* The agent has two read-only tools, `get_predictions()` and `get_anomalies()`, and two
  query intents, `GET_PREDICTIONS` and `GET_ANOMALIES`.
* ML results are computed **once per request** and placed in the planner's context. The
  tools return those same values, and the response's `data` carries them. Whatever the
  planner writes, the structured answer contains the real model output (tested with a
  planner that invents "99.9%").
* The Claude prompt requires ML numbers to be quoted from the context or tools and the
  model to be named. The mock planner builds its sentences from the ML result.
* Examples:
  * "Should I turn on the fan?" → *"Random Forest estimates a 86% probability … Main
    factors: … This is only a recommendation; say 'turn it on' if you want me to switch it on."*
  * "turn it on" → resolved to the fan from the previous turn → `TURN_ON` → validation →
    `CommandService` (`source=ai_agent`).
  * "Is anything unusual?" → *"Isolation Forest flagged an unusual energy reading for the
    Living Room Fan: 170.0 W while on at speed 60%, against a learned normal range of
    34.6–42.5 W."*

### In the UI

* **Home**: an AI prediction card (probability, main factors, "Recommendation only",
  **Ask AI why**), plus an energy-anomaly check in Home status.
* **3D scene**: anomalous devices get a pulsing red ring and an "⚠ Anomaly" tag. A
  predicted device gets a subtle "AI 91%" badge.
* **Energy**: an anomaly panel (live table, active anomalies with observed vs. normal),
  red markers on the power chart, a reading tester, and a model card with all metrics.
* **Assistant**: the prediction card and ML suggestion chips.
* **Activity**: an "ML anomalies" filter.

---

## Reliability and Failure Handling

The backend is the single source of truth, and each optional subsystem (AI provider, ML,
sensors, camera, WebGL) can fail without taking device control down with it.

**One error format.** Every failure, including unknown routes, wrong methods, malformed
JSON and unexpected exceptions, returns
`{"error": {"code": "...", "message": "...", "details": ...}}`. Unexpected errors return
`500 internal_error` without internal details; the traceback is only logged.

| Failure | What the user sees | What keeps working |
|---|---|---|
| Backend unavailable | Header shows **Offline**; banner "Connection to the backend lost", labelled as the last known state; failed commands show an error toast | The UI keeps polling (never overlapping) and recovers by itself when the backend returns. Requests time out after 15 s instead of hanging |
| AI provider unavailable (no or invalid key, outage, rate limit, timeout, bad output) | `503 ai_unavailable`: "AI service is currently unavailable." Nothing is executed; the attempt is kept in AI history | Dashboard, direct control, gestures, events, ML. The whole plan is capped at `SMARTHOME_AI_REQUEST_TIMEOUT_S` (120 s) |
| Camera unavailable or denied, MediaPipe fails to load or crashes | Clear message in the camera panel ("Camera permission was denied", "No camera was found", "Could not load the hand-tracking model") and a Try again button | Everything else. The camera stream, frame loop and MediaPipe work are released on every exit path, including leaving the page |
| WebGL unavailable or context lost | The 2D floor plan, with the same live state, selection and anomaly rings | All controls |
| ML unavailable (training failed, disabled, model error) | `503 ml_unavailable`; cards show "No prediction available" / "Anomaly detection unavailable" | The AI agent still handles normal commands (without ML context); dashboard, gestures and control are unaffected |
| Invalid or missing sensor data | `environment: null` plus `sensor_error`; the UI shows "Sensors unavailable" and never estimates values | Predictions still run but are marked `reliable: false` ("Low confidence"), and the AI says sensors are unavailable instead of quoting numbers |

**Sensor validation.** Readings must be physically plausible (temperature −40 to 85 °C,
humidity 0–100 %, light 0–200 000 lux, finite numbers, occupancy consistent with the
occupant count). Anything else is treated as a sensor fault, not as data. ML feature
overrides (`POST /ml/predict`) use the same bounds and return `422 invalid_features`.

**Gesture confidence.** Frames below the threshold (default 0.75,
`SMARTHOME_GESTURE_CONFIDENCE_THRESHOLD`) are shown as "Gesture ignored — confidence too
low" and never sent. A gesture must also be held for 0.6 s and released before it can fire
again. The backend re-checks the threshold (`422 confidence_below_threshold`).

**AI validation and policy.** LLM output → strict Pydantic plan → per-action capability and
range checks → door policy (explicit, non-negated "lock"/"unlock" only) → `CommandService`.
Malicious or partial plans are handled per action: invalid actions are rejected and never
executed, and an unexpected failure in one action is reported as `failed` without hiding
the others. Repeated or concurrent requests are serialised per device, so every event's
`previous_state` is the previous event's `new_state`.

**Backend as source of truth.** All device changes go through `CommandService`. The UI
shows a new device state only after the backend confirms it, and the 3D scene renders backend
state (AI beams briefly show the backend's own `previous_state` → `new_state`). A failed or
rejected command never mutates state and never creates a success event.

Regression tests: `backend/tests/test_reliability.py` and the frontend's
`cameraSession`, `polling`, `client` and `unavailableStates` tests.

---

## MQTT Hardware Architecture

**Physical hardware is not required for this phase. Fake ESP32 provides a software
simulation of the future firmware.** It speaks exactly the MQTT contract below, so the
backend already runs the real hardware protocol end to end.

```
                 USER
                   │
          ┌────────┴────────┬────────────────────┐
          ▼                 ▼                    ▼
      MediaPipe          AI agent            dashboard
          │                 │                    │
          └────────┬────────┴────────────────────┘
                   ▼
             CommandService          (validation, per-device ordering, events)
                   │
            Device interface          same spec, capabilities, state models
          ┌────────┴─────────┐
          ▼                  ▼
    VirtualDevice      ESP32MQTTDevice     ← chosen per device in config
                             │
                    MQTTManager (one shared connection, app/mqtt)
                             │
                        MQTT broker
                             │
              Fake ESP32 today · real ESP32 later
                             │  state acknowledgement
                             ▼
                         HomeState ──► 3D twin · AI context · ML
```

Nothing above the Device interface knows how a device is connected. The AI agent and
gesture control never publish MQTT; they call `CommandService` exactly as before, and the
factory decides per device whether that reaches a `VirtualDevice` or an `ESP32MQTTDevice`.
All MQTT code lives in `backend/app/mqtt/` (`topics.py`, `messages.py`, `client.py`,
`manager.py`), plus the device driver in `backend/app/devices/esp32.py` and the sensor
provider in `backend/app/sensors/mqtt.py`.

### Topic contract

All topics are built in `app/mqtt/topics.py` and nowhere else.

| Topic | Direction | Payload | Retained |
|---|---|---|---|
| `home/{device_id}/set` | backend → device | command (JSON) | no |
| `home/{device_id}/state` | device → backend | confirmed state / acknowledgement (JSON) | yes |
| `home/{device_id}/availability` | device → backend | `online` / `offline` (also the device's Last Will) | yes |
| `home/sensors/{temperature,humidity,occupancy,ambient_light}` | sensor board → backend | reading (JSON) | no |
| `home/sensors/availability` | sensor board → backend | `online` / `offline` (Last Will) | yes |
| `home/energy/{device_id}` | device → backend | measured power (JSON) | no |
| `home/backend/availability` | backend | `online` / `offline` (the backend's Last Will) | yes |

### Command message

Published with QoS 1, not retained, on `home/{device_id}/set`:

```json
{
  "command_id": "6f1c3a52-0d5e-4b2f-9b8a-1f0e2d3c4b5a",
  "device_id": "fan_living_room",
  "action": "set_speed",
  "parameters": {"value": 70},
  "issued_at": "2026-10-06T12:00:00Z",
  "expires_at": "2026-10-06T12:00:03Z"
}
```

`command_id` is a fresh UUID for every command. Firmware must drop a command whose
`expires_at` has passed: by then the backend has already reported it as timed out, and a
late execution (for example after a reconnect) must never surprise the user. The backend
also connects with a clean session, so the broker never queues commands for later.

### State acknowledgement

The device publishes its resulting state, retained, on `home/{device_id}/state`:

```json
{
  "device_id": "fan_living_room",
  "command_id": "6f1c3a52-0d5e-4b2f-9b8a-1f0e2d3c4b5a",
  "timestamp": "2026-10-06T12:00:00.012Z",
  "state": {"is_on": true, "speed": 70}
}
```

**Publishing a command is not success.** A command succeeds only when the backend
receives an acknowledgement on the device's topic where:

* `device_id` and `command_id` match;
* `state` passes the device spec (types and ranges, strictly);
* the state reflects the command (`set_speed 70` → `speed == 70`).

Only then is the state committed as confirmed and the event recorded. Everything else is
ignored and logged, and the command keeps waiting until it times out:

| Received | Result |
|---|---|
| matching ack, matching state | success: confirmed state + event (`source` = who acted, `details.transport = "mqtt"`, `command_id`, `ack_latency_ms`) |
| wrong / unknown `command_id`, another device, malformed JSON, impossible state | ignored; the command still times out |
| matching ack, valid but different state | `502 device_state_mismatch`; the reported state is shown (it is the device's truth) as a `state_report` event |
| the same ack again | ignored (one event only) |
| ack after the timeout | recorded as a `state_report` (`late_acknowledgement`), since the device did act |
| `command_id: null` | a report the device made itself (boot, wall switch): `state_report` event, `source=mqtt` |

### Availability

Each device connects with a Last Will of `offline` on its availability topic, and publishes
`online` (retained) after connecting. The backend shows three states:

* **ONLINE**: the device said so, or any message from it arrived.
* **OFFLINE**: `offline` was published, or the broker published the Last Will.
  * Commands fail at once with `503 device_unavailable` ("Living Room Fan is offline.").
  * Nothing is published.
  * The last confirmed state stays on screen, including 3D, with an OFFLINE badge.
* **UNKNOWN**: nothing reported yet, the backend lost the broker, or the device stopped
  answering (a timeout). A command may still be attempted; the timeout bounds it.

If a device goes offline mid-command, that command fails immediately; so does a lost
broker connection. When the broker returns, the backend reconnects by itself, resubscribes,
and gets every device's retained availability and state back.

### Timeouts

The limit is `SMARTHOME_MQTT_COMMAND_TIMEOUT_S` (default 3 s, capped at 30 s). Without a
matching acknowledgement in time:

* The command fails with `504 device_timeout` ("Living Room Fan did not confirm the command
  within 3 s. Its last confirmed state is unchanged.").
* The pending command is cleared and no event is recorded.
* The 3D view does not move, and the device shows UNKNOWN until it is heard from again.

CommandService still serialises commands per device: commands to one device are sent one
at a time, in order, and different devices run in parallel.

### Sensor messages

```json
{"sensor_id": "dht22_1", "timestamp": "2026-10-06T12:00:00Z", "value": 29.4}
```

One message per reading on `home/sensors/{kind}`. For occupancy, `value` is the occupant
count; a plain PIR publishes 0 or 1. Readings are validated with the same bounds as Day 6:

* temperature −40 to 85 °C, humidity 0–100 %, light 0–200 000 lux;
* whole occupant counts and finite numbers;
* timezone-aware timestamps that are not in the future.

A rejected reading marks that sensor faulty until a valid one arrives; its old value is not
reused.

**Freshness.** Each reading keeps its value, timestamp and sensor id. A reading older than
`SMARTHOME_SENSOR_MAX_AGE_S` (default 30 s) is stale. If any sensor is stale, missing or
rejected, or the sensor board is offline:

* `environment` is `null`, with a `sensor_error` naming the problem;
* the UI shows "Sensors unavailable";
* ML marks its prediction `reliable: false`;
* the AI says readings are unavailable.

Values are never invented. Firmware should publish every sensor at least every
`max_age / 2` seconds.

Energy readings on `home/energy/{device_id}` (`{"timestamp": "...", "power_w": 41.2}`)
replace the estimated draw while fresh, but only if measured after the device's last
confirmed state change. That way a reading from before a switch-on can't trigger a false
energy anomaly.

### Fake ESP32

`backend/simulation/mqtt_esp32.py` runs one simulated board per device, each with its own
MQTT connection and Last Will, like real hardware. Each board:

* publishes its availability and its retained state;
* validates every command (shape, device id, expiry, action, parameters);
* drives the same physics as the virtual device, then acknowledges.

A sensor board publishes DHT22, PIR and LDR readings every 5 s with the same daily cycle as
the simulated sensors, and each device board publishes its power readings.

Failure scenarios (`simulation/scenarios.py`), switchable at runtime:

| Scenario | Behaviour |
|---|---|
| `normal` | immediate acknowledgement |
| `delay` | acknowledgement after `--delay` seconds |
| `no_ack` | no response |
| `offline` | publishes `offline`, ignores commands |
| `wrong_command_id` | executes, acknowledges with another id |
| `wrong_state` | acknowledges with an impossible state |
| `malformed_ack` | acknowledges with invalid JSON |
| `duplicate_ack` | acknowledges three times |
| `reconnect` | goes offline, comes back after `--reconnect-after` seconds |
| sensors: `normal`, `stale`, `invalid`, `offline` | readings stop / turn implausible / board offline |

```bash
python -m simulation.scenarios fan_living_room no_ack
python -m simulation.scenarios fan_living_room delay --delay 2
python -m simulation.scenarios sensors stale
python -m simulation.scenarios fan_living_room normal
```

### Local MQTT setup (four terminals)

Run these from `backend/` with the virtual environment active. Mosquitto via Docker is
recommended; the pure-Python `amqtt` broker (in `requirements-dev.txt`) works without
Docker. Both listen on `127.0.0.1` only.

```bash
# 1. Broker (either one)
docker compose -f simulation/mosquitto/docker-compose.yml up
amqtt -c simulation/amqtt.yaml

# 2. Fake ESP32: fan and light boards + sensor board
python -m simulation.mqtt_esp32 --devices fan_living_room,light_living_room

# 3. Backend in hardware mode (PowerShell: $env:SMARTHOME_MQTT_ENABLED = "true", ...)
export SMARTHOME_MQTT_ENABLED=true
export SMARTHOME_MQTT_DEVICES='["fan_living_room","light_living_room"]'
export SMARTHOME_SENSOR_SOURCE=mqtt
uvicorn app.main:app --reload

# 4. Frontend
cd ../frontend && npm run dev
```

**Mixed and degraded modes:**

* Devices not listed in `SMARTHOME_MQTT_DEVICES` stay virtual, so virtual and hardware
  devices run side by side.
* With `SMARTHOME_MQTT_ENABLED=false` (the default), nothing about MQTT is loaded and no
  broker is needed.
* If the broker is down, the backend still starts. Virtual devices, gestures, AI and the
  dashboard keep working, and ESP32 devices show UNKNOWN.

`GET /api/v1/iot/status` reports the live connection, per-device availability and
per-sensor freshness.

Real-broker tests: `SMARTHOME_TEST_MQTT_HOST=127.0.0.1 pytest tests/test_mqtt_broker.py`.
They publish on the real topics, so use a broker that no running system is using.

### Moving to a real ESP32

Nothing in the backend changes. The firmware has to implement the contract above:

1. **Firmware** (Arduino / ESP-IDF with PubSubClient or esp-mqtt; ArduinoJson for parsing):
   * connect Wi-Fi and sync the clock over NTP, because timestamps must be real;
   * connect to the broker with **clean session** and the Last Will
     `home/{id}/availability = offline` (QoS 1, retained);
   * publish `online` (retained) and the current state (retained, `command_id: null`);
   * subscribe to `home/{id}/set`. For each command: check `device_id`, drop it if
     `expires_at` has passed, validate action and parameters, drive the relay or PWM, then
     publish the resulting state with the same `command_id` (retained);
   * publish a state report (`command_id: null`) whenever the state changes physically;
   * sensor board: publish each reading on `home/sensors/{kind}` at least every 15 s;
   * optional power meter: publish `home/energy/{id}`.
2. **Broker:** run Mosquitto on the home network (a Raspberry Pi or the backend host).
   * Use `allow_anonymous false` with a password file, and TLS if traffic leaves one machine.
   * Keep it on the LAN. Never expose an MQTT broker to the internet.
3. **Backend configuration only:**
   * set `SMARTHOME_MQTT_HOST`, `PORT`, `USERNAME` and `PASSWORD` in `backend/.env`, which
     is git-ignored;
   * list the devices in `SMARTHOME_MQTT_DEVICES`;
   * set `SMARTHOME_SENSOR_SOURCE=mqtt`;
   * stop the Fake ESP32 for those devices.
4. **Verify** with `GET /api/v1/iot/status`: connected, devices online, sensors `ok`. Then
   run the same commands as with the Fake ESP32. A partly finished board can be tested
   alongside the Fake ESP32 for the other devices.

Credentials are read from the environment, held as a secret value, and never logged.

---

## Out of scope so far

Voice control, multi-agent architecture, facial recognition, vector databases/RAG,
authentication, PostgreSQL, and physical ESP32 hardware (the MQTT protocol is implemented
and tested against the Fake ESP32; the firmware itself is not part of this repository).
