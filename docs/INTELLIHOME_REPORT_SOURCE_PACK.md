# IntelliHome: Master Report Source Pack

> **What this is:** a factual knowledge base for writing the final academic project report.
> It is **not** the report. Another writer (human or AI) can turn it into a formal report with a
> college template without re-reading the repository.
>
> **Evidence base:** the repository at commit **`84a0233`** (tag **`v0.10.0-secure-gesture-unlock`**,
> branch `main`, pushed to GitHub), inspected on **2026-10-07**. Test and build results were
> re-run on that commit while this pack was being written. Metrics were reproduced by retraining
> the models with the default settings.
>
> **Rule for using this pack:** if a fact is not in this pack, do not invent it. Say
> "Not established from repository."

---

## Status labels used throughout

| Label | Meaning |
|---|---|
| **[IMPLEMENTED]** | Present in the source code at `84a0233`. |
| **[TESTED-AUTO]** | Verified by the automated test suites (pytest / Vitest) at `84a0233`. |
| **[TESTED-MANUAL]** | Verified by hand in a real browser. The user reports a real-webcam/microphone test in Microsoft Edge on their local machine (2026-10-07). No test script for it is committed. |
| **[TESTED-DEV]** | Verified during development sessions with tools that are **not committed** to the repository (e.g. a headless-Edge driver, MediaPipe sample photos). It cannot be reproduced from the repo alone. |
| **[SIMULATED]** | Runs on simulated data or simulated hardware, not real-world data or devices. |
| **[DEPLOYED: not established]** | No deployment configuration or deployment evidence exists in the repository. |
| **[PENDING]** | Not yet physically or practically verified (e.g. real ESP32 hardware). |
| **[PLANNED]** | Mentioned as future work in repository docs; not implemented. |
| **[SUGGESTED]** | A reasonable extension proposed in this pack; **not** planned anywhere in the repository. |

---

## Table of contents

**Part A: Identity and framing**
1. [Project Title](#1-project-title) · 2. [Project Overview](#2-project-overview) · 3. [Abstract Material](#3-abstract-material) · 4. [Background](#4-background) · 5. [Problem Statement](#5-problem-statement) · 6. [Motivation](#6-motivation) · 7. [Objectives](#7-objectives) · 8. [Proposed Solution](#8-proposed-solution) · 9. [Key Features](#9-key-features)

**Part B: Architecture**
10. [System Architecture](#10-system-architecture) · 11. [High-Level Data Flow](#11-high-level-data-flow) · 12. [Frontend Architecture](#12-frontend-architecture) · 13. [Backend Architecture](#13-backend-architecture) · 14. [Device Abstraction](#14-device-abstraction) · 15. [CommandService](#15-commandservice)

**Part C: AI agent and safety**
16. [AI Home Agent](#16-ai-home-agent) · 17. [Intent System](#17-intent-system) · 18. [Capability System](#18-capability-system) · 19. [Validation and Security Policy](#19-validation-and-security-policy)

**Part D: Gestures**
20. [Gesture Recognition](#20-gesture-recognition) · 21. [Existing Gesture Mappings](#21-existing-gesture-mappings) · 22. [Gesture Stabilization](#22-gesture-stabilization) · 23. [Pinch-based Fan Adjustment](#23-pinch-based-fan-adjustment) · 24. [Pinch-based AC Adjustment](#24-pinch-based-ac-adjustment) · 25. [Secure Main Door Double-Pinch Workflow](#25-secure-main-door-double-pinch-workflow)

**Part E: Voice**
26. [Voice Assistant](#26-voice-assistant) · 27. ["Hey Nova" Wake-Word Behavior](#27-hey-nova-wake-word-behavior) · 28. [Speech Recognition Behavior](#28-speech-recognition-behavior) · 29. [Voice State Machine](#29-voice-state-machine)

**Part F: Machine learning**
30. [ML Prediction](#30-ml-prediction) · 31. [Random Forest Model](#31-random-forest-model) · 32. [Feature List](#32-feature-list) · 33. [ML Metrics](#33-ml-metrics) · 34. [Isolation Forest Anomaly Detection](#34-isolation-forest-anomaly-detection) · 35. [How ML Interacts with AI](#35-how-ml-interacts-with-ai)

**Part G: Digital twin and home data**
36. [3D Digital Twin / 3D Command Center](#36-3d-digital-twin--3d-command-center) · 37. [HomeState](#37-homestate) · 38. [Sensors / Environment Context](#38-sensors--environment-context) · 39. [Energy Information](#39-energy-information) · 40. [Event Stream](#40-event-stream)

**Part H: IoT / MQTT**
41. [MQTT Architecture](#41-mqtt-architecture) · 42. [ESP32 Readiness](#42-esp32-readiness) · 43. [Fake ESP32 / Simulator](#43-fake-esp32--simulator) · 44. [MQTT Topics and Message Flow](#44-mqtt-topics-and-message-flow) · 45. [Device Availability Behavior](#45-device-availability-behavior)

**Part I: Reliability and interfaces**
46. [Reliability and Failure Handling](#46-reliability-and-failure-handling) · 47. [Error Handling](#47-error-handling) · 48. [Browser Behavior](#48-browser-behavior) · 49. [API Endpoints](#49-api-endpoints) · 50. [Configuration / Environment Variables](#50-configuration--environment-variables)

**Part J: Testing and build**
51. [Testing Strategy](#51-testing-strategy) · 52. [Backend Test Results](#52-backend-test-results) · 53. [Frontend Test Results](#53-frontend-test-results) · 54. [Browser / Integration Testing](#54-browser--integration-testing) · 55. [Production Build](#55-production-build)

**Part K: Deployment, history and status**
56. [Deployment Architecture](#56-deployment-architecture) · 57. [Git Milestones and Commits](#57-git-milestones-and-commits) · 58. [Release Tags](#58-release-tags) · 59. [Known Limitations](#59-known-limitations) · 60. [Current Status](#60-current-status) · 61. [Future Scope](#61-future-scope)

**Part L: Report-writing support**
62. [Viva / Interview Talking Points](#62-viva--interview-talking-points) · 63. [Diagrams for the Final Report](#63-diagrams-for-the-final-report) (A–H) · 64. [Screenshots for the Final Report](#64-screenshots-for-the-final-report) · [Module Cards (academic writing support)](#module-cards-academic-writing-support)

**Appendices**
[A. Technology Stack and Versions](#appendix-a-technology-stack-and-versions) · [B. Files Inspected](#appendix-b-files-inspected) · [C. Ambiguities and Stale Documentation](#appendix-c-ambiguities-and-stale-documentation) · [D. Information That Could Not Be Verified](#appendix-d-information-that-could-not-be-verified) · [E. Glossary](#appendix-e-glossary)

---

# Part A: Identity and Framing

## 1. Project Title

| Item | Value | Source |
|---|---|---|
| Product name (user-facing) | **IntelliHome** | `README.md` title; browser `<title>IntelliHome</title>` (`frontend/index.html`); header `<h1>IntelliHome</h1>` (`frontend/src/App.jsx`); `Settings.app_name = "IntelliHome"` (`backend/app/config.py`) |
| One-line description | **AI-powered smart home automation system** | `README.md` line 3; `GET /` returns `"description": "AI-powered smart home automation system"` (`backend/app/main.py`) |
| Suggested report title | "IntelliHome: An AI-Powered Smart Home Automation System with Gesture, Voice and Natural-Language Control" | Suggested wording only. The project's own description is the line above. |

**Names used in different places (do not mix them up):**

| Context | Name |
|---|---|
| Product / UI / API title | `IntelliHome` |
| Local project folder | `smart-ai-home` (inside `mini_project/`) |
| GitHub repository | `MUKULSHARMA2711/Smart_hand_gesture_Home` (https://github.com/MUKULSHARMA2711/Smart_hand_gesture_Home) |
| Backend Python package name | `smart-ai-home-backend` (version string `0.1.0`, `backend/pyproject.toml`) |
| Frontend npm package name | `smart-ai-home-frontend` (version string `0.1.0`, `frontend/package.json`) |
| FastAPI app version string | `0.1.0` (`backend/app/main.py`). **Not** bumped with the release tags (latest tag is v0.10.0). |
| Environment-variable prefix | `SMARTHOME_` (e.g. `SMARTHOME_MQTT_ENABLED`) |
| MQTT client id (default) | `intellihome-backend` |
| MQTT topic root | `home/` |
| Voice wake phrase | **"Hey Nova"** ("Nova" is only the wake word; the product is still IntelliHome) |
| AI planner self-name in its system prompt | "IntelliHome, the planning component of a smart-home assistant" (`backend/app/ai/prompts.py`) |

## 2. Project Overview

IntelliHome is a **software-first smart home system**. A **FastAPI (Python) backend** simulates
four household devices and environmental sensors in memory. A **React web application** controls
them through four input channels:

1. a **dashboard / 3D digital twin** (click and control),
2. **hand gestures** recognised in the browser with **MediaPipe** (webcam),
3. **natural language**, typed or spoken, interpreted by an **AI home agent** (a deterministic mock planner by default, optionally Anthropic Claude),
4. **voice**, with the wake phrase **"Hey Nova"**, using the browser's speech recognition.

Every input channel converges on **one execution path, `CommandService`**. It validates each command
against the device's specification, serialises commands per device, and records an audit event with
the true source (`frontend`, `gesture`, `ai_agent`, `mqtt`, `ml`).

On top of this, the system adds:

- **machine learning**: a Random Forest predicts whether the fan will be needed soon, and Isolation Forests detect abnormal energy readings. Both are trained on **simulated** data.
- a **security-sensitive door workflow**: unlocking the Main Door by AI, voice or gesture always requires an explicit, expiring confirmation.
- an **MQTT hardware layer** that lets any device run on an ESP32 microcontroller. It is tested end to end against a **software "Fake ESP32"**. **No physical hardware has been tested.**

**Default home (from `backend/app/config.py`):**

| Device id | Name | Type | Room | Initial state |
|---|---|---|---|---|
| `light_living_room` | Living Room Light | `light` | living_room | off, brightness 100 |
| `fan_living_room` | Living Room Fan | `fan` | living_room | off, speed 50 |
| `ac_bedroom` | Bedroom AC | `ac` | bedroom | off, target 24 °C |
| `door_main` | Main Door | `door_lock` | entrance | locked |

## 3. Abstract Material

*Raw sentences and facts for an abstract. Every number below is verified.*

- IntelliHome is an AI-powered smart home automation system. It combines a virtual IoT backend, a browser-based 3D digital twin, real-time hand-gesture control, a natural-language AI agent, browser voice control and machine-learning analytics.
- All control channels share one validated execution path (`CommandService`). A gesture, a spoken sentence or an AI plan can therefore never bypass device validation or the audit log.
- Gesture recognition runs entirely in the browser: MediaPipe HandLandmarker extracts 21 landmarks, a rule-based classifier scores the gesture, and a 0.6 s stabilizer turns it into a deliberate command. Only the recognised gesture is sent to the server, never video.
- Five static gestures map to device-agnostic intents. A pinch-and-move gesture adjusts fan speed (0–100 %) and AC temperature (16–30 °C), sending exactly one command on release.
- The AI agent turns language into a structured JSON action plan. The backend validates every action: schema, capability, value range, and a negation-aware door security policy. Door unlocking always needs a separate, 30-second confirmation.
- The Main Door can be unlocked by gesture only through a two-step **double pinch**. The first pinch creates a pending confirmation. The second pinch confirms it through the same backend endpoint, which re-validates the request before executing once.
- A Random Forest classifier (120 trees, depth 8) predicts fan need within 30 minutes. On a held-out split of **simulated** data it scores 87.4 % accuracy against a 71.3 % majority baseline (F1 0.767). Isolation Forest detectors find injected energy faults with F1 between 0.857 and 0.968 per device type, also on simulated data.
- An MQTT driver (acknowledgements, timeouts, Last-Will availability, fresh-only sensor data) makes devices hardware-ready. It is verified against a software Fake ESP32. Physical ESP32 deployment is pending.
- The verification base is **524 automated backend tests** (2 more skipped because they need a real broker) and **212 frontend tests**, all passing, plus a successful production build.

## 4. Background

Facts for a background chapter. The literature itself is **not** in the repository; cite sources separately.

- Conventional smart homes usually use one interaction mode (a mobile app or a voice assistant). IntelliHome explores **multimodal interaction**: touch/dashboard, gesture, typed language and voice.
- **Hand-tracking technology used:** Google **MediaPipe Tasks Vision `HandLandmarker`** (npm `@mediapipe/tasks-vision ^1.0.1`), run in the browser with WebAssembly plus a WebGL (GPU) delegate and a CPU fallback.
- **LLM technology used (optional):** the Anthropic Claude API via the official `anthropic` Python SDK. Default model id `claude-opus-5-5`. It uses structured outputs and strict read-only tools. It is **off by default**; the deterministic `MockAIProvider` is used unless configured otherwise.
- **IoT messaging technology:** MQTT (paho-mqtt client) with QoS 1, retained state, Last Will and Testament, and clean sessions. It targets **ESP32** microcontrollers.
- **ML technology:** scikit-learn `RandomForestClassifier` and `IsolationForest`.
- **3D technology:** three.js through React Three Fiber (R3F) and drei.

## 5. Problem Statement

Points the repository's design addresses, each traceable to code:

1. **Fragmented control paths are unsafe.** Without a single path, a gesture or AI command could skip validation or logging. Addressed by `CommandService` as the only state-changing entry point (`backend/app/domain/command_service.py`).
2. **LLMs are untrusted.** A language model may hallucinate devices, values or actions, or be manipulated. Addressed by schema-constrained plans plus backend validation; the LLM never gets a device-changing tool (`backend/app/ai/validation.py`, `tools.py`).
3. **Security-sensitive actions need more than intent detection.** "I'm leaving home" must not lock or unlock the door, and "don't unlock the door" must not unlock it. Addressed by explicit capabilities, separate door intents, a negation-aware policy and mandatory unlock confirmation (`backend/app/domain/policy.py`, `backend/app/ai/confirmation.py`).
4. **Gesture recognition is noisy.** Frame-level classification flickers. Addressed by a hold-and-release stabilizer and a confidence threshold enforced on both the client and the server.
5. **Hardware arrives later than software.** Addressed by a device abstraction (`DeviceSpec` plus interchangeable `VirtualDevice` / `ESP32MQTTDevice`) and a Fake ESP32 that speaks the real protocol.
6. **ML without real data.** Addressed by honest, deterministic simulation that is labelled as simulated everywhere (API `data_note`, UI, README).

## 6. Motivation

- To show a **safe architecture** for AI-in-the-loop home control, where "AI proposes, backend validates, CommandService executes".
- To offer **touch-free control** (gestures, voice). Accessibility and convenience are reasonable framing; the repository makes no user-study claims.
- To build a system that can move from **simulation to real ESP32 hardware** by configuration only.
- To keep every displayed value **honest**: the UI never shows a device state the backend has not confirmed, and never shows invented scores (`frontend/src/state/homeHealth.js` comment: "There is deliberately no numeric 'intelligence score'").

## 7. Objectives

Objectives as achieved in code (status in brackets):

| # | Objective | Status |
|---|---|---|
| O1 | Virtual IoT backend with 4 device types, sensors, energy metering and an event log | [IMPLEMENTED] [TESTED-AUTO] [SIMULATED] |
| O2 | Real-time browser hand-gesture control mapped to device-agnostic intents | [IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL] |
| O3 | Natural-language AI agent with validated structured plans | [IMPLEMENTED] [TESTED-AUTO] (mock provider). Real Claude provider: unit-tested with a fake client only |
| O4 | Live 3D digital twin driven only by backend state | [IMPLEMENTED] [TESTED-AUTO] (pure mapping functions) |
| O5 | ML prediction and energy anomaly detection explained by the AI | [IMPLEMENTED] [TESTED-AUTO] [SIMULATED] |
| O6 | Failure isolation and a single error format | [IMPLEMENTED] [TESTED-AUTO] |
| O7 | MQTT/ESP32 hardware readiness | [IMPLEMENTED] [TESTED-AUTO] against the Fake ESP32 and an in-memory broker. Real hardware [PENDING] |
| O8 | "Hey Nova" voice control through the same AI pipeline | [IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL] (Edge) |
| O9 | Confirmation-gated door unlocking (AI, voice, gesture) | [IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL] (double pinch, Edge) |
| O10 | Pinch adjustment of fan speed and AC temperature | [IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL] |

## 8. Proposed Solution

A layered client–server system:

- **Browser (React):** gesture recognition (MediaPipe + rule classifier + stabilizer + pinch detector), voice capture (Web Speech API), the 3D digital twin, dashboards. It sends only **structured requests** (a command, a gesture result, or text) to the backend.
- **Backend (FastAPI):** the single source of truth.
  - `GestureService` checks gestures.
  - `HomeAgent` plans and validates language requests.
  - `IntentResolver` maps intents to device commands through explicit **capabilities**.
  - `SecurityPolicy` guards door actions.
  - `CommandService` executes and logs.
  - `HomeState` aggregates devices, sensors and energy.
  - `MLService` predicts and detects.
  - `MQTTManager` talks to hardware.
- **Device layer:** each device type has a `DeviceSpec` (state shape and commands with value limits). Implementations are `VirtualDevice` (in-memory simulation) or `ESP32MQTTDevice` (MQTT), chosen per device by configuration.

## 9. Key Features

| Feature | Short description | Status |
|---|---|---|
| Virtual devices | Light, fan, AC, door lock, simulated in memory with power models | [IMPLEMENTED] [TESTED-AUTO] [SIMULATED] |
| Dashboard and 5 pages | Home, Gesture, AI assistant, Energy, Activity (hash routes) | [IMPLEMENTED] [TESTED-MANUAL] |
| 3D digital twin | R3F scene; fan spin, AC airflow, light glow, door ajar/closed; 2D floor-plan fallback | [IMPLEMENTED] [TESTED-AUTO] (mappings) |
| Five gestures | 👍 TURN_ON, ✊ TURN_OFF, ✋ STOP, ☝️ SELECT, ✌️ TOGGLE | [IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL] |
| 0.6 s stabilizer | Hold ≥ 0.6 s above threshold; fires once; must release | [IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL] |
| Pinch adjustment | 👌 fan speed / AC temperature; one command on release | [IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL] |
| Double-pinch door unlock | 1st pinch = pending confirmation; 2nd pinch = confirm via backend | [IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL] |
| AI home agent | Natural-language → validated plan → CommandService | [IMPLEMENTED] [TESTED-AUTO] |
| Door security policy | Explicit, negation-aware lock/unlock wording; unlock confirmation, 30 s | [IMPLEMENTED] [TESTED-AUTO] |
| "Hey Nova" voice | Wake phrase, one-breath or two-step, spoken replies | [IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL] |
| Random Forest prediction | Fan needed within 30 min, with explanation | [IMPLEMENTED] [TESTED-AUTO] [SIMULATED] |
| Isolation Forest anomalies | Per-device-type energy anomaly detection | [IMPLEMENTED] [TESTED-AUTO] [SIMULATED] |
| Reliability hardening | One error envelope, failure isolation, timeouts, non-overlapping polling | [IMPLEMENTED] [TESTED-AUTO] |
| MQTT/ESP32 driver | Acks, timeouts, availability, sensor freshness | [IMPLEMENTED] [TESTED-AUTO] [SIMULATED] hardware; real ESP32 [PENDING] |
| Fake ESP32 | Software firmware stand-in with failure scenarios | [IMPLEMENTED] [TESTED-AUTO] |

---

# Part B: Architecture

## 10. System Architecture

**Layers and responsibilities (backend `backend/app/`):**

| Layer / package | Responsibility | Key classes |
|---|---|---|
| `api/` (`api/v1/*.py`) | HTTP only: routing, schemas, error mapping | routers `home`, `devices`, `events`, `gestures`, `ai`, `ml`, `iot`; `register_exception_handlers` |
| `gestures/` | Gesture vocabulary, gesture→intent mapping, confidence gate, block list, door-unlock request, history | `Gesture`, `GESTURE_INTENTS`, `GESTURE_ALTERNATE_INTENTS`, `GestureService`, `InMemoryGestureHistory` |
| `ai/` | Language → plan → validation → execution; confirmations; providers | `HomeAgent`, `PlanValidator`, `AgentTools`, `ConfirmationStore`, `MockAIProvider`, `AnthropicProvider` |
| `domain/` | Business rules | `CommandService`, `IntentResolver`, `SecurityPolicy`, `HomeState`, `EnergyMeter` |
| `devices/` | Device contract, per-type specs, registry, factory, virtual and ESP32 implementations | `Device`, `DeviceSpec`, `VirtualDevice`, `ESP32MQTTDevice`, `DeviceRegistry`, `build_device` |
| `sensors/` | Environment readings | `SensorProvider`, `SimulatedSensorProvider`, `MQTTSensorProvider` |
| `events/` | Event model, sources, storage | `DeviceEvent`, `CommandSource`, `InMemoryEventStore` |
| `ml/` | Features, simulated datasets, models, service | `FanUsagePredictor`, `EnergyAnomalyDetector`, `MLService` |
| `mqtt/` | Topic contract, messages, transport, manager, in-memory broker | `topics`, `PahoTransport`, `MQTTManager`, `InMemoryBroker` |
| `config.py` / `container.py` | Settings and composition root (the only place concrete classes are chosen) | `Settings`, `build_container` |

**Frontend (`frontend/src/`):** `pages/` (5 pages), `components/` (3d, house, gestures, assistant, ml, devices, charts, console, controls), `gestures/` (recognition pipeline), `voice/` (voice session), `hooks/`, `state/` (React contexts, polling, AI lifecycle reducer), `api/client.js`, `lib/` (presentation helpers).

See [Diagram A](#a-complete-system-architecture).

## 11. High-Level Data Flow

1. **Read path:** the browser polls `GET /api/v1/home/state` every **5 s**, without overlapping requests (`state/polling.js`), and re-fetches immediately after every command. The 3D scene and cards render only this backend state.
2. **Write path (all channels):** request → channel-specific checks → `CommandService.execute(device_id, command, source)` → `Device.execute_command()` (spec validation → `_perform`) → `DeviceEvent` stored → response with the new state.
3. **Channel-specific checks:**
   - **Dashboard:** `POST /devices/{id}/command`. The `source` must be `frontend`.
   - **Gesture:** `POST /gestures/commands`. Checks gesture↔intent match, confidence ≥ threshold, value rules, intent applicability, and the block list.
   - **AI / voice:** `POST /ai/command`. Steps: provider plan → Pydantic → `PlanValidator` (intent, parameters, device, capability, range, policy, duplicates).
   - **Door unlock confirmation:** `POST /ai/confirmations/{id}`. The request is re-validated with `confirmed=True`.
4. **ML path:** `HomeState` snapshot → feature extraction → model → result. Read-only; anomalies are logged as `source=ml` events, never commands.
5. **Hardware path (when enabled):** `ESP32MQTTDevice._perform` publishes on `home/{id}/set` and waits for a matching acknowledgement on `home/{id}/state` before committing state.

## 12. Frontend Architecture

| Aspect | Fact | Source |
|---|---|---|
| Framework | React 19 (`react ^19.3.0`), Vite 8 (`vite ^8.3.2`), Tailwind CSS 4, `motion` (animations) | `frontend/package.json` |
| Routing | Hash routes: `#/` Home, `#/gestures` Gesture, `#/assistant` AI assistant, `#/energy` Energy, `#/activity` Activity | `App.jsx` `ROUTES` |
| Code splitting | `GesturePage` is lazy-loaded, so MediaPipe is downloaded only on the Gesture page. The 3D scene is a separate lazy chunk. | `App.jsx`; build output (§55) |
| Global state | `HomeDataProvider` (home state, events, polling, command errors), `AssistantProvider` (AI requests, lifecycle, orb state), `CommandFxProvider` (beam/pulse effects from real responses) | `state/*.jsx` |
| API client | `fetch` wrapper. 15 s timeout for normal requests, **130 s** for AI requests. Parses the backend error envelope into `ApiError {status, code, details}`. | `api/client.js` |
| Connection UI | Header shows **Live / Offline**. A banner says "Connection to the backend lost" and labels the last-known state. Polling continues and the UI recovers automatically. | `App.jsx`, `state/polling.js` |
| Gesture modules | `mediapipeRecognizer.js`, `ruleClassifier.js`, `stabilizer.js`, `pinch.js`, `adjustment.js`, `doorUnlock.js`, `pinchRouting.js`, `cameraSession.js`, `types.js` | `gestures/` |
| Voice modules | `voice/voiceSession.js` (framework-independent), `hooks/useVoiceAssistant.js`, `components/assistant/VoicePanel.jsx` | |
| Tests | Vitest in a Node environment; React components rendered with `renderToStaticMarkup` (no jsdom) | `__tests__/` |

**Pages:**

| Page | Content |
|---|---|
| **Home** (`#/`) | Live 3D twin with the AI core orb, sensor readout, "Ask IntelliHome" quick-command bar, device inspector, home status checks, live event stream, device controls, AI prediction card |
| **Gesture** (`#/gestures`) | Camera panel with landmark overlay, detection panel (gesture, confidence, per-finger extension), target selector, Door unlock panel, Adjust panel, last action, gesture guide, gesture history, compact 3D preview with gesture beams |
| **AI assistant** (`#/assistant`) | Chat with suggestion chips, action plan with per-action status, request lifecycle pipeline, 3D view with command beams, provider and safety info, **Voice panel ("Hey Nova")**, door confirmation buttons |
| **Energy** (`#/energy`) | Current/peak/average power, power-over-time chart (sampled in the browser), per-device bars, anomaly panel, reading tester form, ML model card |
| **Activity** (`#/activity`) | Merged stream of device events, gesture events and AI interactions with filters (including "ML anomalies") |

## 13. Backend Architecture

- **Framework:** FastAPI (`fastapi>=0.115,<1.0`; 0.142.2 installed locally), Pydantic v2, pydantic-settings, uvicorn.
- **App factory:** `create_app()` in `backend/app/main.py`.
  - Builds the container and adds CORS middleware: explicit origins only, methods `GET` and `POST`, header `Content-Type`.
  - Registers the error handlers and mounts the router at `/api/v1`.
  - Its lifespan starts and stops MQTT if it is enabled. Startup never waits for the broker.
- **Composition root:** `build_container()` in `backend/app/container.py` wires these in order:
  1. Event store and MQTT manager (when enabled).
  2. Devices (from the factory) into the `DeviceRegistry`.
  3. The sensor provider, then `HomeState` and `CommandService`.
  4. `GestureService` and `MLService`. ML training failure leads to `None`; ML stays disabled and nothing else is affected.
  5. `HomeAgent` (provider, tools, validator with policy, history).
  6. Finally `gesture_service.enable_unlock_confirmation(agent.hold_gesture_unlock)` when `gesture_door_unlock` is true.
- **Persistence:** **none**. The event log (default max 1000), gesture history (500) and AI history (100) are in-memory ring buffers and are lost on restart. ML models are retrained at every startup. PostgreSQL is mentioned in the README as "later" [PLANNED].
- **Authentication:** **none** [Not implemented]. The README lists "authentication" as out of scope.

## 14. Device Abstraction

**[IMPLEMENTED] [TESTED-AUTO]**

- `Device` (ABC, `devices/base.py`): `execute_command(command)` validates through the shared spec, checks `accepts_commands`, captures `previous_state`, awaits `_perform(validated)`, and returns a `CommandResult(previous_state, new_state, metadata)`.
- `DeviceSpec` (`devices/specs/base.py`): the hardware-independent contract of a device type, made of a state model and a list of command models. **Each command declares exactly one `Capability`**; declaring a capability twice raises an error. `describe_commands()` publishes action, capability and value range (min/max) to clients as `supported_commands`.
- `VirtualDevice`: `_perform` applies a **pure** `apply(state, command)` transition after optional simulated latency (`SMARTHOME_VIRTUAL_DEVICE_LATENCY_MS`).
- `ESP32MQTTDevice`: `_perform` publishes over MQTT and awaits acknowledgement (§41).
- `build_device()` (`devices/factory.py`) is the only place that chooses the class, based on `DeviceConfig.driver` (`virtual` / `esp32_mqtt`).

**Device specifications:**

| Type | State | Commands (capability) | Value rules |
|---|---|---|---|
| light | `is_on`, `brightness` | `turn_on` (TURN_ON), `turn_off` (TURN_OFF), `set_brightness` (SET_BRIGHTNESS) | integer 0–100, strict |
| fan | `is_on`, `speed` | `turn_on`, `turn_off`, `set_speed` (SET_SPEED) | integer 0–100, strict |
| ac | `is_on`, `target_temperature_c` | `turn_on`, `turn_off`, `set_temperature` (SET_TEMPERATURE) | integer 16–30 °C, strict |
| door_lock | `is_locked` | `lock` (LOCK), `unlock` (UNLOCK) | no value |

"Strict" means `70.5`, `"70"` and `true` are rejected, and so is a `value` sent to a command that takes none.

**Virtual behaviour:**
- Light and fan: a value of 0 turns the device off; any value above 0 turns it on. `turn_on` resumes the previous level (the fan defaults to 50 if its speed was 0).
- AC: `set_temperature` changes the set point even while the unit is off.
- Door: starts locked.

**Power models (`devices/power.py`), used for virtual devices and for ESP32 devices without a fresh measurement:**

| Device | Off (standby) | On |
|---|---|---|
| Light | 0.3 W | 0.3 + 9 × brightness/100 W |
| Fan | 0.5 W | 12 + 48 × speed/100 W (12–60 W) |
| AC | 2.0 W | 700 + 70 × (30 − target °C) W |
| Door lock | 0.8 W | 0.8 W (standby only) |

## 15. CommandService

**[IMPLEMENTED] [TESTED-AUTO]**. File: `backend/app/domain/command_service.py` (46 lines).

- **The single entry point for changing device state.** The REST API, `GestureService`, the AI agent (`AgentTools.control_device`) and confirmations all call `CommandService.execute(device_id, command, source)`. ML never calls it.
- **Per-device `asyncio.Lock`:** commands to one device are serialised, so each event's `previous_state` equals the prior event's `new_state`. Different devices run in parallel. Tested in `test_reliability.py` ("concurrent commands on one device are serialised").
- The energy meter is sampled **before** every command (`record_energy()`), so energy integration stays correct.
- On success, it creates a `DeviceEvent(device_id, action, value, previous_state, new_state, source, details)` and appends it to the `EventStore`.
- On failure, no event is created and the state is unchanged. Tested: "failed commands never mutate state or log events".
- `source` records **who acted** (`frontend`, `gesture`, `ai_agent`). The transport (MQTT) goes into `details`.
- **Source integrity:** the direct device endpoint accepts only `source: "frontend"`. Requests with `gesture`, `ai_agent`, `ml` and so on get `422 invalid_request` (`api/schemas.py` `CommandRequest.only_direct_control`). A client therefore cannot forge the audit trail or bypass the gesture and AI checks.

---

# Part C: AI Agent and Safety

## 16. AI Home Agent

**[IMPLEMENTED] [TESTED-AUTO]**. Files: `backend/app/ai/agent.py`, `validation.py`, `tools.py`, `context.py`, `models.py`, `prompts.py`, `confirmation.py`, `providers/`.

**Pipeline** (`HomeAgent.handle(message)`):

1. If an unlock confirmation is pending, the message is first classified as a reply (§19). Otherwise it goes to planning.
2. **Context:** `build_home_context()` creates a `HomeContext` with devices (id, name, type, room, status, **capabilities**, state, power), environment, `sensor_error`, energy, the 5 most recent events, and ML insights (computed once per request).
3. **Plan:** `AIProvider.plan(PlanningRequest(message, context, tools, history=last 3 interactions))` returns **untrusted** JSON `{"message": str, "actions": [{device_id, intent, parameters}]}`. The call is wrapped in `asyncio.wait_for` with `SMARTHOME_AI_REQUEST_TIMEOUT_S` (default 120 s).
4. **Parse:** `ActionPlan` is strict, with `extra="forbid"`, `message` 1–2000 characters, and at most **12** actions. Each action is parsed separately (`PlannedAction`, `extra="forbid"`), so one bad action does not discard the others.
5. **Validate everything before executing anything:** `PlanValidator.validate_all()` (§19).
6. **Execute:** valid device actions go through `AgentTools.control_device` → `CommandService` (`source=ai_agent`). Query intents are answered from backend data. Rejected actions never run. An unexpected failure in one action is reported as `failed` without hiding the others.
7. **Respond:** `AgentResponse` contains:
   - `reply` (the planner's text, **untrusted**);
   - `outcome` (generated by the backend, e.g. "2 executed.");
   - per-action `status`: `executed`, `answered`, `rejected`, `failed`, `awaiting_confirmation` or `cancelled`;
   - `device_events`, `changed_devices`, `errors` and `confirmation`.

**Providers:**

| Provider | When | Behaviour |
|---|---|---|
| `MockAIProvider` (`providers/mock.py`, 413 lines) | **Default** (`SMARTHOME_AI_PROVIDER=mock`) | Deterministic, rule-based keyword planner; needs no key or network. Builds the same raw plan shape from the same `HomeContext`, so it passes through identical validation. Used by **all** automated tests (or scripted fakes). |
| `AnthropicProvider` (`providers/anthropic_provider.py`) | `SMARTHOME_AI_PROVIDER=anthropic` | Official `anthropic` SDK, imported lazily. Manual tool loop (max 4 rounds by default). Only the **6 read-only tools** are offered, marked `strict`. Uses structured output (`output_config.format`), `effort` (default `medium`), and the server-side refusal fallback (`fallbacks="default"`). Default model `claude-opus-5-5`; per-call timeout 60 s. |
| `UnavailableAIProvider` | The real provider failed to initialise | Every request returns `503 ai_unavailable`; the rest of the system keeps working. |

**Read-only tools the LLM may call** (`AgentTools.call_read_only`):
`get_home_state`, `get_device_status`, `get_recent_events`, `get_energy_usage`, `get_predictions`,
`get_anomalies`. Any other name, `control_device` included, raises `ToolError`: "Device changes must
go in the action plan." `control_device` is executor-only and is never exposed to the LLM.

**Real Claude provider status:** it is implemented and unit-tested with a **fake SDK client**
(`tests/test_anthropic_provider.py`, 13 tests). A live call against the paid API is **not
established from the repository**.

## 17. Intent System

**[IMPLEMENTED] [TESTED-AUTO]**. File: `backend/app/domain/intents.py`.

An **intent** says *what* the user wants without naming a device action. Gestures, the AI agent and
voice (through the AI agent) all produce intents.

| Group | Intents |
|---|---|
| Device control | `TURN_ON`, `TURN_OFF`, `SET_BRIGHTNESS`, `SET_SPEED`, `SET_TEMPERATURE`, `LOCK_DOOR`, `UNLOCK_DOOR`, `TOGGLE`, `STOP`, `ADJUST` |
| Queries (never change a device) | `GET_STATUS`, `GET_ENERGY`, `GET_HISTORY`, `GET_PREDICTIONS`, `GET_ANOMALIES` |
| Targeting / no-op | `SELECT`, `NONE` |

**Who may use which intents:**
- **AI agent** (`AI_INTENTS`):
  - device intents `TURN_ON`, `TURN_OFF`, `SET_BRIGHTNESS`, `SET_SPEED`, `SET_TEMPERATURE`, `LOCK_DOOR`, `UNLOCK_DOOR`;
  - all 5 query intents.
  - It may **not** use `TOGGLE`, `STOP`, `SELECT`, `ADJUST` or `NONE`.
- **Gestures:** `TURN_ON`, `TURN_OFF`, `STOP`, `SELECT`, `TOGGLE`, `ADJUST`, `NONE`, plus `UNLOCK_DOOR` **only** as the alternate intent of `PINCH`, which only *requests* an unlock (§25).

**Resolution (`IntentResolver.resolve(intent, device, value)`):**
- `SELECT` → no command (targeting only).
- Each other device intent requires **exactly one capability** (`INTENT_CAPABILITIES`): `STOP` → `TURN_OFF`, `LOCK_DOOR` → `LOCK`, `UNLOCK_DOOR` → `UNLOCK`, and each `SET_*` maps to the capability of the same name.
- `TOGGLE` requires both `TURN_ON` and `TURN_OFF`. It resolves to `turn_off` if `is_on`, otherwise `turn_on`.
- `ADJUST` resolves to the first of `SET_SPEED`, `SET_TEMPERATURE`, `SET_BRIGHTNESS` the device has. It is **never** a lock capability.
- If the device lacks the capability, `IntentNotApplicableError` is raised (HTTP 400 `intent_not_applicable`).
- Value ranges are left to the device spec.

## 18. Capability System

**[IMPLEMENTED] [TESTED-AUTO]** (`tests/test_capabilities.py`, 44 tests).

| Device | Capabilities |
|---|---|
| Light | `TURN_ON`, `TURN_OFF`, `SET_BRIGHTNESS` |
| Fan | `TURN_ON`, `TURN_OFF`, `SET_SPEED` |
| AC | `TURN_ON`, `TURN_OFF`, `SET_TEMPERATURE` |
| Door lock | `LOCK`, `UNLOCK` |

- Capabilities are **explicit and unambiguous** (`devices/types.py`). A door has only `LOCK`/`UNLOCK`, so `TURN_ON`/`TURN_OFF`/`STOP`/`TOGGLE`/`ADJUST` can **never** reach the door.
- Capabilities appear in every device payload (`capabilities`, `supported_commands`) and in `GET /api/v1/ai/status`.
- **Why "turn on everything" can never touch the door:** three independent layers.
  1. **Capability:** a `TURN_ON` on the door is rejected as `unsupported_capability`.
  2. **Separate door intents:** only `LOCK_DOOR` and `UNLOCK_DOOR` can change the lock.
  3. **Security policy:** the user's own words must explicitly and non-negatedly say "lock" or "unlock" (§19).

## 19. Validation and Security Policy

**[IMPLEMENTED] [TESTED-AUTO]**

**PlanValidator order** (`ai/validation.py`), applied to every AI action before anything executes:

| Step | Rejection code |
|---|---|
| 1. Schema (`PlannedAction`, no unknown fields) | `malformed_action` |
| 2. Intent allowed for the AI | `intent_not_allowed` |
| 3. Parameters schema (`{"value": int}` strict; `GET_HISTORY {"limit": 1-50}`; otherwise none) | `invalid_parameters` |
| 4. Device id present (device intents) / exists | `missing_device` / `unknown_device` |
| 5. Device has the capability | `unsupported_capability` |
| 6. Value range, checked by the device spec without side effects | `invalid_parameters` |
| 7. Security policy | `unlock_disabled` / `not_explicitly_requested` (or `requires_confirmation`) |
| 8. Duplicate action in the same plan | `duplicate_action` |

**SecurityPolicy** (`domain/policy.py`):
- **Scope:** applies to the `LOCK`/`UNLOCK` capabilities (`SECURITY_SENSITIVE_CAPABILITIES`) when the source is `ai_agent`. The gesture unlock request is validated through this same policy (§25).
- **`SMARTHOME_AI_ALLOW_UNLOCK=false`** → `unlock_disabled`.
- **Explicit wording:** the user's message must contain `lock`/`locked`/`locking`, or `unlock`/`unlocked`/`unlocking`. Otherwise the action is rejected with `not_explicitly_requested`. Example: "I'm leaving home" never locks the door.
- **Negation-aware:** a mention counts only if no negation appears **before it in the same clause**.
  - Negations: `don't, do not, does not, doesn't, did not, didn't, never, not, no, shouldn't, should not, mustn't, must not, won't, will not, can't, cannot, without, avoid, stop`.
  - Clause breaks: `. , ; : ! ?` and the words `and, but, then, so, also`.
  - Examples: "don't unlock the door" → rejected. "Don't turn on the lights and unlock the door" → the unlock counts, because the negation belongs to the other clause.
- **Confirmation:** an allowed `UNLOCK` with `SMARTHOME_AI_UNLOCK_REQUIRES_CONFIRMATION=true` (default) returns `requires_confirmation=True`. The action is **held**, not executed. Locking needs no confirmation.

**Confirmation mechanics** (`ai/agent.py`, `ai/confirmation.py`):
- **One pending confirmation** at a time (`ConfirmationStore`). A new hold replaces the old one.
- Each pending confirmation has a `confirmation_id` (UUID), `prompt`, the original `request`, its `source` (`ai_agent` or `gesture`) and `expires_at` = now + `SMARTHOME_AI_CONFIRMATION_TIMEOUT_S` (default **30 s**, maximum 300).
- **Reply classification** (`classify_reply`):
  - any negation or cancel word (`no, nope, cancel, abort, stop, never, don't, not, keep it locked, leave it`…) → **CANCEL**, and negation always wins;
  - an affirmation plus an explicit "unlock" or "confirm" ("yes, unlock it", "confirm") → **CONFIRM**;
  - a bare "yes" → **AFFIRM_ONLY**: the assistant repeats the exact phrase and keeps waiting;
  - anything else → **OTHER**, and the pending unlock is **dropped**.
- **Buttons / gesture:** `POST /api/v1/ai/confirmations/{id}` with `{"decision": "confirm"|"cancel"}`. Unknown id → `404 confirmation_not_found`; expired → `410 confirmation_expired`.
- **On confirm** (`_confirm`):
  1. The pending entry is cleared first, so a confirmation executes **at most once**.
  2. The action is **re-validated** (device, capability, and the policy on the original request, with `confirmed=True`).
  3. It executes through `CommandService` with the **original source**, so a gesture-requested unlock is logged with `source=gesture`.
- A late "yes, unlock it" after expiry gets an "expired" reply and nothing executes.

**Other security facts:**
- No gesture command can execute `unlock` directly: `SMARTHOME_GESTURE_BLOCKED_ACTIONS` defaults to `["unlock"]`.
- CORS: explicit origins only, and `*` is refused at startup. Defaults are `http://localhost:5173`, `http://localhost:5174`, `http://127.0.0.1:5173` and `http://127.0.0.1:5174`. Methods `GET` and `POST`; header `Content-Type`. Credentials are not enabled.
- Secrets (`SMARTHOME_AI_API_KEY`, `SMARTHOME_MQTT_PASSWORD`) are `SecretStr` values, never logged. `.env` is git-ignored.
- **Not implemented:** user authentication or authorization, rate limiting, HTTPS/TLS configuration.
- **Important limitation:** the **direct dashboard endpoint** `POST /devices/door_main/command {"action":"unlock"}` unlocks **immediately without confirmation**. The README treats this as "the user's own action". Combined with no authentication, anyone who can reach the API can unlock the virtual door. State this honestly in the report.

---

# Part D: Gestures

## 20. Gesture Recognition

**[IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL]**

| Stage | Implementation | Key parameters |
|---|---|---|
| Camera | `cameraSession.js` with `getUserMedia` | ideal 640×480, `facingMode: 'user'`, no audio; works only on `localhost` or HTTPS |
| Landmarks | `mediapipeRecognizer.js`: MediaPipe `HandLandmarker`, `runningMode: 'VIDEO'` | `numHands: 1`, `minHandDetectionConfidence 0.6`, `minHandPresenceConfidence 0.6`, `minTrackingConfidence 0.5`; GPU (WebGL) delegate with CPU fallback; WASM runtime bundled by Vite; model `hand_landmarker.task` (float16) downloaded from Google storage on first use (~7.8 MB per README) |
| Classifier | `ruleClassifier.js`: pure functions, no MediaPipe dependency | Per-finger extension score 0–1 from joint angles plus reach in **metric 3D world landmarks** (rotation-invariant). Each gesture is a fuzzy AND (0.6×min + 0.4×mean). Best score < 0.5 → `UNKNOWN`. Ambiguity penalty: confidence = best − 0.5 × max(0, runner-up − 0.25). THUMBS_UP also needs the thumb pointing up in the image. |
| Pinch detector | `pinch.js` (separate from the classifier) | See §23 |
| Stabilizer | `stabilizer.js` | See §22 |
| Loop | `useGestureRecognition.js`: `requestAnimationFrame` loop | React state updates about 10×/s (100 ms); landmarks drawn every frame on a canvas over the mirrored preview |
| Sending | `api.sendGesture` → `POST /api/v1/gestures/commands` | Sends `{gesture, intent, confidence, target_device_id, value?}` only. **Video frames never leave the browser.** |

**Backend gesture checks** (`GestureService.handle`, `gestures/service.py`):
1. The intent must equal the gesture's mapped intent, or an allowed alternate (`PINCH` → `UNLOCK_DOOR`). Otherwise `422 gesture_intent_mismatch`.
2. `NEUTRAL`/`UNKNOWN` → `422 gesture_not_actionable`.
3. confidence < threshold (default **0.75**) → `422 confidence_below_threshold`. This is enforced by the backend independently of the browser.
4. A value is allowed only for value intents (`ADJUST`); otherwise `422 invalid_gesture_value`.
5. Intent applicable to the target (capability) → else `400 intent_not_applicable`.
6. A resolved action on the block list (`unlock`) → `403 action_blocked`.
7. `CommandService.execute(..., source=gesture)`.

Every attempt is recorded in the gesture history with an outcome: `executed`, `acknowledged` (SELECT), `rejected`, `failed` or `awaiting_confirmation`.

**Targeting:** explicit. The device selected in the UI is used; it defaults to the first device (Living Room Light), and `ONE_FINGER` cycles through light → fan → AC → door.

**Verification:**
- **[TESTED-AUTO]** synthetic 3D hand poses, including rotated hands (`ruleClassifier.test.js`, 12 tests).
- **[TESTED-DEV]** per the README, MediaPipe sample photos (`thumb_up`, `fist`, `pointing_up`, `victory`, open palm) were fed to a headless browser as a fake webcam and recognised at 96–98 % confidence. The script is not committed.
- **[TESTED-MANUAL]** real webcam in Edge, reported by the user.

## 21. Existing Gesture Mappings

**[IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL]**. Canonical mapping `GESTURE_INTENTS` (`backend/app/gestures/models.py`), mirrored in `frontend/src/gestures/types.js`. The frontend loads it from `GET /api/v1/gestures/config`.

| Gesture | Intent | Light / Fan / AC | Main Door |
|---|---|---|---|
| 👍 `THUMBS_UP` | `TURN_ON` | `turn_on` | not applicable (400) |
| ✊ `FIST` | `TURN_OFF` | `turn_off` | not applicable (400) |
| ✋ `OPEN_PALM` | `STOP` | `turn_off` | not applicable (400). While a door unlock is pending, it **cancels** the unlock instead. |
| ☝️ `ONE_FINGER` | `SELECT` | selects the next device; no device command | can select the door |
| ✌️ `TWO_FINGERS` | `TOGGLE` | `turn_on` ⇄ `turn_off` | not applicable (400) |
| 👌 `PINCH` | `ADJUST` (alternate: `UNLOCK_DOOR`) | fan → `set_speed`, AC → `set_temperature` (light → `set_brightness`, see Appendix C) | first pinch → **requests** unlock (pending confirmation); second pinch → **confirms** (§25) |
| `NEUTRAL` (no hand) / `UNKNOWN` (unrecognised hand) | `NONE` | nothing | nothing |

**The door is not a generic gesture-controlled device.** The power gestures cannot affect it. Its only gesture interaction is the confirmation-gated double pinch.

*History:* in Day 2 (v0.2.0), gestures on the door mapped to lock/unlock (THUMBS_UP locked it). Day 3 (v0.3.0) removed this by introducing explicit capabilities. A `FOUR_FINGERS` door gesture was briefly added (`fd000cb`) and **removed** (`b9cbff0`), because a real webcam misread it as `OPEN_PALM`; the double pinch replaced it.

## 22. Gesture Stabilization

**[IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL]**. `GestureStabilizer` (`frontend/src/gestures/stabilizer.js`, 75 lines; 7 tests).

| Rule | Value |
|---|---|
| Confidence threshold to qualify | `threshold` = backend `confidence_threshold` (default **0.75**) |
| Hold time before commit | **`holdMs = 600` (0.6 s)** |
| Dropout tolerance during a hold | `graceMs = 200` |
| Minimum gap between any two commits | `cooldownMs = 1000` |
| Fire once | After a commit, the same gesture must be **released** before it can fire again |
| Committed confidence | mean confidence over the hold |
| Non-actionable | `NEUTRAL`/`UNKNOWN` never commit; low-confidence frames are shown ("below threshold") but never commit |
| During a pinch | the stabilizer is fed `UNKNOWN`, so no other gesture can fire while a pinch is forming or held |

The user explicitly required the 0.6 s stabilizer to be kept unchanged in every later phase.

## 23. Pinch-based Fan Adjustment

**[IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL]**

**Pinch detection** (`gestures/pinch.js`, 10 tests in `pinchAdjustment.test.js`):
- A pinch is the thumb tip touching the index tip **with the other fingers open** (an "OK" sign). This keeps it distinct from a fist.
- Ratio = thumb–index tip distance ÷ wrist–middle-knuckle distance (hand-size normalised).
- **Enter:** ratio < 0.30 **and** at least 2 of middle/ring/pinky with extension ≥ 0.55, for **4 consecutive frames**.
- **Exit:** ratio > 0.50 for **3 consecutive frames** (hysteresis).
- Hand position is smoothed with an EMA (weight 0.35) of the thumb/index midpoint `y`.
- Events: `start`, `move`, `end` (release), and `cancel` (hand lost; nothing is applied).
- Pinch "confidence" = 0.75 + 0.25 × average closure margin, so it is always in **0.75–1.0** (see the Appendix C note).

**Adjustment** (`gestures/adjustment.js`):
1. ☝️ select the **Living Room Fan**.
2. 👌 pinch: the adjustment starts from the fan's **backend-confirmed** speed.
3. Move the hand **up = faster**, **down = slower**. Moving half the frame height (`travel = 0.5`) covers the whole 0–100 range. Values are clamped to the range published by the backend (`supported_commands`).
4. Moving only **previews** the value (the Adjust panel shows "Fan Speed 80%, from 50% · faster"). Nothing is sent per frame.
5. **Release:** exactly **one** command `{gesture: "PINCH", intent: "ADJUST", value, target_device_id}` goes to `POST /gestures/commands`. The backend resolves it to `set_speed` and executes it with `source=gesture`.
6. Unchanged value → nothing is sent ("Value unchanged"). Hand lost → nothing is sent ("Hand lost"). Another gesture command in flight → refused ("Another gesture command is still running").

**Example** (from `pinchRouting.test.js`): start speed 50, hand moves from y 0.60 to 0.45 → value 80.

The fan device spec still validates `0–100`, strict integer. Fan speed 0 turns the fan off (virtual behaviour).

## 24. Pinch-based AC Adjustment

**[IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL]**

Same flow as §23 with the **Bedroom AC**:
- The range is **16–30 °C** (integers), published by the backend.
- Direction: **hand up = cooler** (lower set point), **hand down = warmer** (`direction: -1`).
- On release, one `PINCH/ADJUST` command resolves to `set_temperature` (`source=gesture`).
- Example (test): from 24 °C, hand moves from 0.60 to 0.40 → **18 °C**.
- The AC accepts set-point changes while off (virtual behaviour); the panel shows "AC Temperature".

**Routing rule** (`gestures/pinchRouting.js`, commit `84a0233`):

```js
export function routePinch(event, { device, unlock, adjuster }) {
  if (unlock.busy || device?.device_type === 'door_lock') { unlock.pinch(event); return 'door' }
  adjuster.handle(event); return 'adjust'
}
```

The selected device decides first. A pending or in-flight door unlock, or a selected door, sends the pinch to the door controller. Only other devices reach the adjustment. This fixed a real bug where a pinch on the Main Door showed "Main Door has no adjustable value".

## 25. Secure Main Door Double-Pinch Workflow

**[IMPLEMENTED] [TESTED-AUTO] (backend `test_gesture_unlock.py` 27 tests; frontend `doorUnlock.test.jsx` 22 and `pinchRouting.test.js` 7) [TESTED-MANUAL] (Edge, user-reported)**

**Principle:** a gesture never unlocks the door directly. The first pinch only *requests*. The second
pinch *confirms* through the **same confirmation endpoint** the AI uses, and the backend
**re-validates** before **one** execution through `CommandService`.

**Step by step:**

| # | User | Frontend | Backend | Door state |
|---|---|---|---|---|
| 0 | ☝️ selects **Main Door** | `selectedId = door_main` | (SELECT acknowledged) | locked |
| 1 | 👌 **first stable pinch** | `routePinch` → `DoorUnlockController.pinch(start)` → `requestUnlock(confidence)` = `POST /gestures/commands {gesture:"PINCH", intent:"UNLOCK_DOOR", confidence, target_device_id:"door_main"}`. The panel shows "Requesting unlock confirmation…" | `GestureService` validates (alternate intent allowed, confidence ≥ 0.75, door has `UNLOCK`) → `_request_door_unlock` → `HomeAgent.hold_gesture_unlock("door_main")`: validates `UNLOCK_DOOR` through `PlanValidator` + `SecurityPolicy` (request text "unlock the Main Door"); requires the confirmation step; stores a `PendingConfirmation(source="gesture", expires_at=now+30 s, prompt="Unlock the Main Door? Pinch again to confirm, open palm to cancel.")`. Gesture outcome `awaiting_confirmation`; response includes `confirmation`. **Nothing executes.** | locked |
| 2 | — | **Door unlock panel:** "🔐 Unlock Main Door?", "Waiting for confirmation · N s", "👌 Pinch again to confirm", "✋ Open palm to cancel", "The door stays locked until the backend confirms the unlock." | pending (single slot) | locked |
| 3 | 👌 **second stable pinch** | `DoorUnlockController` (pending) → `decide(id, "confirm")` = `POST /ai/confirmations/{id} {"decision":"confirm"}`. Panel: "Confirming with the door…" | `HomeAgent.decide` → `_confirm`: clears pending (at most once) → **re-validates** (`confirmed=True`) → `AgentTools.control_device` → **`CommandService.execute(door_main, unlock, source=gesture)`** → `DeviceEvent` | **unlocked** |
| 4 | — | Panel "✓ Unlocked: confirmed by the door"; refreshes devices and events; the 3D door swings ajar with an amber indicator | — | unlocked |

**Cancellation and fail-closed rules (any of these leaves the door locked):**

| Trigger | Mechanism |
|---|---|
| ✋ Open palm while pending | `unlock.gesture('OPEN_PALM')` → cancel via `POST /ai/confirmations/{id} {"decision":"cancel"}`. The palm is **consumed**, so no STOP command is sent. |
| Any other gesture (👍 ✊ ☝️ ✌️) | Cancels the pending unlock, then the gesture runs normally |
| Hand out of view | Cancel after **1.5 s** with no hand (`GesturePage.jsx`) |
| Camera stopped | Cancel ("Cancelled: the camera stopped.") |
| Another device selected | Cancel ("Cancelled: another device was selected.") |
| Leaving the Gesture page | Cancel on unmount ("Cancelled: left the gesture page.") |
| Expiry (30 s) | Frontend `tick()` every 1 s marks it expired. The backend refuses a late confirm with `410 confirmation_expired`. |
| Pinches while the request or confirmation is in flight | **Ignored** (`requesting` / `confirming` flags), so no duplicate requests or double confirmation |
| Any other `/ai/command` request | Drops the pending unlock (single shared slot) |

**Policy dependencies:**
- `SMARTHOME_GESTURE_DOOR_UNLOCK=false` turns the feature off: the first pinch returns `403 action_blocked`.
- `SMARTHOME_AI_ALLOW_UNLOCK=false` also refuses gesture unlock requests (tested).
- If `SMARTHOME_AI_UNLOCK_REQUIRES_CONFIRMATION=false`, the gesture request is refused, because a gesture unlock **must** have a confirmation step.
- `unlock` stays in `SMARTHOME_GESTURE_BLOCKED_ACTIONS`.

See [Diagram E](#e-secure-door-unlock-flow).

---

# Part E: Voice

## 26. Voice Assistant

**[IMPLEMENTED] [TESTED-AUTO] (47 tests in `voice/__tests__/voiceSession.test.js`) [TESTED-MANUAL] (Edge, user-reported)**

- **Location:** AI assistant page → **Voice panel** → "Enable voice" / "Turn off voice".
- **Technology:** the browser **Web Speech API** for recognition (`SpeechRecognition` / `webkitSpeechRecognition`) and **`speechSynthesis`** for spoken replies.
- **No separate execution path:** recognised **text** is sent through the same `POST /api/v1/ai/command` pipeline as typed requests, with the same validation, door policy and `CommandService`.
- **Spoken responses** are built by `spokenSummary()` (`lib/assistant.js`) from the backend's **actual results**, never from the planner's free text about actions.
  - Executed: "Done. Living Room Fan is now on."
  - Rejected or failed: "{device} was not changed: {reason}".
  - Held unlock: the confirmation prompt is spoken.
  - Queries: the reply text.
- **Door unlock by voice:** "Hey Nova, unlock the main door" → held → the assistant asks "Are you sure…? Say 'yes, unlock it' to confirm, or 'cancel'." The reply **does not need the wake phrase** (the session goes straight to command mode, `expectsReply`).
- **Audio cues:** a Web Audio chime, 880 Hz for wake and 220 Hz for error. No audio files.
- **Privacy statement (UI):** the browser recognises the speech (Chrome and Edge use the vendor's online speech service), and only the recognised text is sent to IntelliHome.
- **Unsupported browsers:** the panel says "Voice control needs a browser with speech recognition, such as Chrome or Edge. Typing and gestures still work."
- **Diagnostics:** opt-in console trace with `localStorage.setItem('voiceDebug','1')`.

## 27. "Hey Nova" Wake-Word Behavior

**[IMPLEMENTED] [TESTED-AUTO] [TESTED-MANUAL]**

| Rule | Detail |
|---|---|
| Wake phrase | **"Hey Nova"**. Accepted first word: `hey`, `hay`, `hi`; must be **directly followed** by `nova`. |
| Position | "hey" must be within the **first 3 words** of an utterance (`WAKE_WORD_OFFSET = 2`), so ordinary speech does not wake it |
| Normalisation | Case, punctuation, hyphens and spacing are ignored ("Hey, Nova!" = "hey nova") |
| One-breath command | "Hey Nova, turn on the living room fan" → wake plus command in one result; the command keeps the user's wording |
| Two-step command | "Hey Nova" → **command window of 8 s** (`commandWindowMs = 8000`) → "turn on the fan". No command in 8 s → back to waiting ("No command heard.") |
| Split results | A wake phrase the browser splits across two results ("hey" \| "nova, …") is joined if they arrive within **4 s** (`WAKE_JOIN_MS`) |
| Interim detection | The wake phrase is also detected on **interim** (not yet final) text, because Edge may not finalise a short "hey nova" before ending the session. This only opens the command window; **commands are still taken from final text**. |
| Never sent | The wake phrase alone, leftover fragments ("hey" / "nova"), and repeated wake phrases are never submitted as commands |
| History | v0.8.0 used "Hey IntelliHome". `49ca328` improved Edge matching. `b6c8d66` renamed it to **"Hey Nova"**, and "Hey IntelliHome" no longer wakes it. `7c97737` fixed the wake → command transition. |

## 28. Speech Recognition Behavior

| Setting / behaviour | Value |
|---|---|
| Language | `en-US` (recognition and synthesis) |
| Mode | `continuous = true`, `interimResults = true`, `maxAlternatives = 1` |
| Echo prevention | The microphone is **detached** while a request is processed and while the reply is spoken, so the assistant never hears itself |
| Session ends | Browsers end recognition after silence or time limits. The session restarts automatically, **but at most 5 restarts within 10 s**; beyond that voice turns off ("Speech recognition keeps stopping…") |
| Unfinalised text | Interim text left when the browser ends a session is processed, not dropped |
| One recogniser | A restart always detaches the old recogniser (`detach()`), so no duplicate sessions |
| Errors | `not-allowed` → "Microphone access was denied…"; `audio-capture` → "No microphone was found."; `network` → "The browser's speech service could not be reached…"; `service-not-allowed`, `language-not-supported` → specific messages. `no-speech` / `aborted` → silent restart |
| Cleanup | Turning voice off, leaving the page (unmount), mic denial and fatal errors all release the recogniser, handlers and timers, and cancel speech |
| Speech synthesis guard | Waits for `onend`, with a timeout of min(20 s, 2 s + 90 ms × characters), because some browsers never fire `onend` |
| Camera | Voice runs on the assistant page and gestures on the Gesture page; voice does not touch the camera |

**Browser limitations:**
- Needs the Web Speech API: Chrome and Edge, per the UI text.
- In those browsers recognition goes through the vendor's **online** service, so it needs internet.
- English (US) only.
- Microphone permission is required.
- Firefox support is not claimed.

## 29. Voice State Machine

States (`voiceSession.js`): **`off` · `wake` · `command` · `processing` · `speaking` · `error` · `unsupported`**.

| From | Event | To |
|---|---|---|
| off | Enable voice (API available) | wake |
| off | Enable voice (no API) | unsupported |
| wake | final/interim text with "hey nova" and **no** command | command (8 s window) |
| wake | final text "hey nova, <command>" | processing |
| wake | other speech | wake (ignored) |
| command | final text (a command) | processing |
| command | 8 s with nothing | wake ("No command heard.") |
| processing | backend response with text to say | speaking |
| processing / speaking | response **with a pending confirmation** | command (reply without the wake phrase) |
| speaking | done | wake |
| any listening state | fatal error / too many restarts / mic denied | error |
| any | Turn off voice / leave page | off |

The UI also maps `processing` to the real request lifecycle ("Executing…", "Done", "Something went wrong").

---

# Part F: Machine Learning

> **Read this first: all ML data is SIMULATED.** Both models are trained **at backend startup** on
> deterministic data generated from IntelliHome's own sensor and device models, because no physical
> sensor history exists. The API carries this note (`data_note` in `GET /ml/status`): *"Trained on
> simulated history generated from IntelliHome's sensor and device models, because no physical sensor
> history exists yet. Metrics describe the simulation, not real-world accuracy."* **Never present
> these metrics as real-world performance.**

## 30. ML Prediction

**[IMPLEMENTED] [TESTED-AUTO] [SIMULATED]**. Files: `backend/app/ml/` (`features.py`, `dataset.py`, `prediction.py`, `anomaly.py`, `service.py`, `models.py`).

- **Task:** binary classification `FAN_ON_SOON`: will the Living Room Fan be on within the **next 30 minutes**?
- **Live input:** features derived from the current `HomeState` snapshot plus recent events (§32).
- **Output (`Prediction`):**
  - `prediction` `"ON"`/`"OFF"` (threshold **0.5**, `SMARTHOME_ML_PREDICTION_THRESHOLD`), `probability`, `horizon_minutes=30`;
  - `features`, `missing_features`, `reliable`, `factors` (per feature: value, typical, importance, effect), `reason_features`;
  - a plain-English `explanation`, `model="random_forest_v1"`.
- **Explainability:** one-at-a-time sensitivity. The model is re-run with each input set to its **training median**; the change in probability is that factor's `effect`. The top 3 factors with |effect| ≥ 0.01 go into the explanation. Example format: *"Random Forest predicted a 83% probability that the Living Room Fan will be needed within 30 minutes. Main factors: Temperature 30.0 °C (typical 25.6 °C); …"*
- **Missing data:** missing inputs are imputed with training medians and listed. If any **sensor** feature is missing, `reliable=false` and the explanation adds "Low confidence…". The UI shows "Low confidence".
- **API:**
  - `POST /api/v1/ml/predict` with `{}` derives features from live state.
  - Optional `{"features": {...}}` overrides values (`null` = missing).
  - Out-of-range or unknown features → `422 invalid_features`.
  - Only `fan_living_room` is supported (other devices → `400`).
- **Recommendation only:** predictions **never** trigger actions. The AI says "This is only a recommendation; say 'turn it on'…".

## 31. Random Forest Model

| Item | Value (verified by retraining at `84a0233`) |
|---|---|
| Model name | `random_forest_v1` |
| Algorithm | scikit-learn `RandomForestClassifier(n_estimators=120, max_depth=8, min_samples_leaf=5, random_state=42)` |
| Target | `FAN_ON_SOON` (fan on in either of the next two 15-minute steps) |
| Dataset | **Simulated**, 60 days × 15-minute steps, seed **7** → **5,757 samples**, positive rate **28.8 %** |
| Split | Stratified 75/25 → **4,317 train / 1,440 test** |
| Simulation logic | Daily temperature/humidity/daylight cycle (same as the sensor simulator) with hotter and cooler days; weekday/weekend occupancy schedule (away during weekday working hours); comfort-driven fan use. Fan "pressure" = 1.15×(T−27.5) + 0.05×(H−60) + (1.3 if occupied, else −4.0), minus 1.0 between 01:00 and 06:00; fan on/off is sampled through a sigmoid with persistence. |
| Retraining | At every backend start (deterministic; `train_models()` in `ml/service.py`) |
| Disable | `SMARTHOME_ML_ENABLED=false`; training failure also disables ML without affecting device control |

## 32. Feature List

| # | Feature | Label | Source at runtime | Plausible bounds |
|---|---|---|---|---|
| 1 | `hour` | Hour of day | clock (hour + minute/60) | 0–24 |
| 2 | `day_of_week` | Day of week | clock (Mon=0) | 0–6 |
| 3 | `temperature_c` | Temperature | sensors | −40 to 85 °C |
| 4 | `humidity_pct` | Humidity | sensors | 0–100 % |
| 5 | `occupied` | Occupancy | sensors | 0/1 |
| 6 | `occupant_count` | People home | sensors | 0–100 |
| 7 | `ambient_light_lux` | Ambient light | sensors | 0–200,000 lux |
| 8 | `fan_on` | Fan currently on | device state | 0/1 |
| 9 | `fan_recently_on` | Fan used in last 30 min | state + events (30-min window) | 0/1 |

Sensor features (3–7) mark a prediction unreliable when missing.

**Anomaly model features:** `setting_level` and `power_w`.
- `setting_level` is 0 when the device is off and 10–100 when on:
  - light and fan: 10 + 0.9 × brightness/speed;
  - AC: 10 + 90 × (30 − T)/14, so 30 °C → 10 and 16 °C → 100;
  - door: always 0.

## 33. ML Metrics

**Random Forest (`random_forest_v1`), held-out test set of 1,440 simulated samples:**

| Accuracy | Majority baseline | Precision | Recall | F1 | Confusion matrix [[TN, FP], [FN, TP]] |
|---|---|---|---|---|---|
| **0.8743** (87.4 %) | **0.7125** (71.3 %) | **0.8209** | **0.7198** | **0.7671** | **[[961, 65], [116, 298]]** |

Feature importances: `fan_on` 0.3058, `temperature_c` 0.2222, `fan_recently_on` 0.1548, `humidity_pct` 0.1046, `hour` 0.0561, `occupant_count` 0.0513, `occupied` 0.0461, `ambient_light_lux` 0.0374, `day_of_week` 0.0216.

**Isolation Forest (`isolation_forest_v1`), per device type. Held-out 30 % split: 750 readings, 15 injected faults each; 1,750 training readings each:**

| Device type | Precision | Recall | F1 | False-alarm rate |
|---|---|---|---|---|
| Light | 0.9231 | 0.8000 | 0.8571 | 0.0014 (0.14 %) |
| Fan | 1.0000 | 0.8000 | 0.8889 | 0.0000 |
| AC | 0.8667 | 0.8667 | 0.8667 | 0.0027 (0.27 %) |
| Door lock | 0.9375 | 1.0000 | 0.9677 | 0.0014 (0.14 %) |

These numbers were reproduced exactly by retraining with the default settings (`ml_seed=7`, `ml_dataset_days=60`) on scikit-learn 1.9.1 / numpy 2.5.3. They match the README. They are exposed live at `GET /api/v1/ml/status`. **They describe the simulation only.**

## 34. Isolation Forest Anomaly Detection

**[IMPLEMENTED] [TESTED-AUTO] [SIMULATED]**

| Item | Value |
|---|---|
| Model | One `IsolationForest(n_estimators=100, contamination=0.02, random_state=13)` **per device type** (light, fan, ac, door_lock) |
| Training data | **Simulated**, 2,500 readings per type (seed 11 = `ml_seed + 4`). Normal power comes from the virtual power models with ~3 % multiplicative noise plus 0.05 W additive noise. About **2 %** are injected faults: **surge** (×2.2–4 + 5–40 W), **stall** (0–25 % of expected while running), **phantom draw** (power while off: 15–80 W, AC 150–600 W). |
| Alarm threshold | Learned so that **99.8 %** of normal training readings pass (0.2 % quantile of normal decision scores). `score = raw − threshold`; **score < 0 ⇒ anomalous**. |
| Normal range | 0.5–99.5th percentile of normal readings in the same setting bin (bins of 10 levels). Example from the README: fan at speed 60 → 34.6–42.5 W. |
| Live scan | `GET /ml/anomalies` assesses every device's current power. An event is logged only when a device **becomes** anomalous. Virtual devices always report modelled power, so they are normal. |
| Reported readings | `POST /ml/anomalies/check {"device_id", "power_w"}` assesses an external reading, as a future hardware power meter would send. The Energy page has a tester form. |
| Logging | Anomalies become `DeviceEvent`s with `event_type="energy_anomaly"`, `source="ml"`, unchanged state, and `details` = {score, expected_range, setting, origin, model} |
| Active window | Anomalies count as "active" for **15 minutes** (`SMARTHOME_ML_ANOMALY_ACTIVE_MINUTES`) |
| False-alarm guard (tested) | 168 sampled legitimate virtual states (light and fan levels in steps of 3, on/off; every AC set point, on/off; both door states) are **all** classified normal (`test_ml_models.py`) |
| MQTT energy | When hardware reports `home/energy/{id}`, a fresh measured reading replaces the estimate, but only if measured after the device's last confirmed state change, which avoids false anomalies |

## 35. How ML Interacts with AI

**[IMPLEMENTED] [TESTED-AUTO]**

```
ML recommends and detects → the AI or the user decides → CommandService executes.
```

- `MLService` does **not** depend on FastAPI, React, device implementations or `CommandService`. It never issues commands. The device endpoint refuses `source: "ml"` with a `422`, and the error says "The ML layer only recommends and detects; it cannot issue device commands."
- For each AI request, ML **insights are computed once** (`HomeContext.ml`). The read-only tools `get_predictions()` / `get_anomalies()` and the response `data` return **the same values**. A test with a planner that invents "99.9 %" shows the structured answer still carries the real model output.
- Query intents `GET_PREDICTIONS` and `GET_ANOMALIES` let the planner answer "Should I turn on the fan?" or "Is anything unusual?".
- The Claude system prompt requires ML numbers to be quoted from context or tools, the model to be named ("Random Forest estimates…", "Isolation Forest flagged…"), and predictions never to be acted on without an explicit request.
- Follow-ups: "turn it on" after a fan recommendation resolves to the fan from conversation history and goes through normal validation → `CommandService` (`source=ai_agent`).
- If ML fails, the agent continues without ML context (`_ml_insights` catches errors).

---

# Part G: Digital Twin and Home Data

## 36. 3D Digital Twin / 3D Command Center

**[IMPLEMENTED] [TESTED-AUTO] (pure mapping functions: `visualState.test.js` 16 tests) [TESTED-MANUAL]**

- **Technology:** three.js `^0.186.1`, `@react-three/fiber ^9.8.1`, `@react-three/drei ^10.7.9`.
  - Procedural geometry: no model or texture downloads.
  - Glow uses additive sprites from a code-generated texture; particles use instanced meshes.
- **Backend-confirmed state only:** the scene keeps **no device state of its own**. Each device component receives the backend snapshot as props and derives visuals through pure functions (`components/3d/visualState.js`). Animations only *smooth toward* the backend value. Nothing changes visually until the backend confirms.

| Backend state | Visual |
|---|---|
| Light `is_on`, `brightness` | Bulb glow, point-light intensity (max 40) and floor glow. `level = 0.12 + 0.88 × brightness/100`; 0 when off |
| Fan `is_on`, `speed` | Blade angular velocity **2–24 rad/s** (linear in speed); smooth spin-up and spin-down; stopped when off |
| AC `is_on`, `target_temperature_c` | Cool-air particles only while on; colder set points blow harder and bluer (`coolness = (30 − T)/14`, airflow 0.45–1); the real set point is shown on the unit |
| Door `is_locked` | Closed with a **green** indicator when locked; **ajar (0.6 rad)** with **amber** when unlocked |
| Device `status` offline/unknown | OFFLINE / UNKNOWN badge; the last confirmed state stays shown |
| ML anomaly | Pulsing **red ring** and "⚠ Anomaly" tag |
| ML prediction | Subtle "AI NN%" badge, **only when the prediction is ON** |

- **AI core orb** (`AIOrb`): states `idle`, `listening`, `thinking`, `planning`, `executing`, `success`, `error`, driven by the tested `state/aiLifecycle.js` reducer.
  - `listening`: the assistant input is focused, the gesture camera is running, or voice is listening.
  - `thinking`: the HTTP request is in flight.
  - `planning`: about 0.7 s once the response arrives.
  - `executing`: beams about 0.55 s apart.
- **Command beams:** one beam per device-targeting result, in plan order. While a beam is in flight, the device shows the backend's own `previous_state`, switching to `new_state` when the beam lands. Rejected results show a red fizzle. Gesture results beam from the gesture input; dashboard commands show a device pulse. Effects are only emitted from **real API responses** (`CommandFxContext`).
- **Click to control:** clicking a device opens the `DeviceInspector` (capabilities and controls) → `POST /devices/{id}/command` → refresh.
- **Performance and accessibility:**
  - Lazy-loaded scene chunk (982.85 kB, **262.43 kB gzip**).
  - Render loop pauses off-screen; DPR capped at 1.75.
  - `prefers-reduced-motion` disables spin, particles and beams.
  - **2D floor-plan fallback** without WebGL or on scene failure.

## 37. HomeState

**[IMPLEMENTED] [TESTED-AUTO]**. `backend/app/domain/home_state.py`.

- An in-memory aggregate of the device registry, the sensor provider and the `EnergyMeter`.
- `snapshot()` → `HomeStateSnapshot { timestamp, environment | null, sensor_error | null, energy {total_power_w, energy_kwh, per_device_w}, devices[] }`. Served by `GET /api/v1/home/state`.
- Each `DeviceSnapshot` has `id`, `name`, `device_type`, `room`, `status`, `state`, `power_w`, `capabilities`, `supported_commands`, `driver`, `last_confirmed_at`.
- Sensor failures never break the snapshot: they give `environment: null` and a `sensor_error` reason. State transitions are logged; values are **never guessed**.
- HomeState feeds the 3D twin, the AI context, ML features and the dashboards.

## 38. Sensors / Environment Context

**[IMPLEMENTED] [TESTED-AUTO] [SIMULATED]**

| Item | Detail |
|---|---|
| Readings | `temperature_c`, `humidity_pct`, `occupancy {occupied, occupant_count}`, `ambient_light_lux` |
| Default source | `SimulatedSensorProvider` (`SMARTHOME_SENSOR_SOURCE=simulated`). Daily cycle: temperature 26 ± 4 °C (peak about 15:00, low about 03:00), humidity 58 ∓ 12 % (inverse), light up to ~650 lux in daylight (06:00–18:00) and ~3 lux at night, mean-reverting noise; occupancy changes by ±1 person with probability 0.1 per read (0–4 people). Optional fixed seed `SMARTHOME_SENSOR_SEED`. |
| MQTT source | `MQTTSensorProvider` (`SMARTHOME_SENSOR_SOURCE=mqtt`): readings from `home/sensors/{temperature,humidity,occupancy,ambient_light}` |
| Plausibility bounds | Temperature −40 to 85 °C; humidity 0–100 %; light 0–200,000 lux; occupancy count 0–100 with `occupied == (count > 0)`; finite numbers only. Violations are sensor faults, not data. |
| Freshness (MQTT) | A reading older than `SMARTHOME_SENSOR_MAX_AGE_S` (default **30 s**) is stale. Any stale, missing or rejected sensor, or an offline sensor board, gives `environment = null` with a `sensor_error`. |
| Effect downstream | UI "Sensors unavailable"; ML `reliable: false`; the AI says readings are unavailable instead of quoting numbers |
| Physical sensors (DHT22, PIR, LDR) | **[PENDING]**: named only as the targets of the MQTT contract and of the Fake sensor board; **never physically tested** |

## 39. Energy Information

**[IMPLEMENTED] [TESTED-AUTO] [SIMULATED]**

- Power per device comes from the power models (§14), or from fresh measured MQTT readings for ESP32 devices.
- `EnergyMeter` integrates total power over time (W·s → kWh), sampled before every command and on every read. `energy_kwh` covers the period **since the backend started**, because nothing is persisted.
- `GET /home/state` → `energy.total_power_w`, `energy_kwh`, `per_device_w`.
- The AI tool `get_energy_usage` returns total, kWh, per-device share in % and the top consumer.
- The **Energy page** shows:
  - current, peak and average power and a power-over-time chart. The **history is sampled by the browser** from the 5 s polls (the backend stores no history; the chart starts when the page is opened, and the page says so);
  - per-device bars, the anomaly panel with red chart markers, and the reading tester.

## 40. Event Stream

**[IMPLEMENTED] [TESTED-AUTO]**

| Item | Detail |
|---|---|
| Model | `DeviceEvent { event_id (UUID), timestamp (UTC), device_id, action, value, previous_state, new_state, source, event_type, details }` |
| `source` (`CommandSource`) | `frontend`, `gesture`, `ai_agent`, `mqtt`, `ml`, `automation`. **`automation` is reserved; no automation engine exists.** |
| `event_type` | `device_command` (default), `energy_anomaly` (ML). MQTT device reports carry `details.reason` such as `state_report` / `late_acknowledgement`. |
| Store | `InMemoryEventStore`, a ring buffer, max `SMARTHOME_EVENT_LOG_MAX_SIZE` (default 1000) |
| API | `GET /api/v1/events?limit=1..500&device_id=…`, newest first |
| Other histories | Gesture history (`GET /gestures/events`, every attempt with outcome; max 500). AI history (`GET /ai/history`, every interaction including failures; max 100). |
| UI | Home "live event stream"; the **Activity** page merges device events, gesture events and AI interactions with source labels (Dashboard, Gesture, AI agent, Automation, ML) and filters (including "ML anomalies") |

---

# Part H: IoT / MQTT

> **Physical hardware status: [PENDING].** No ESP32, relay, sensor or power meter has been
> connected or tested. Everything below was verified against a **software Fake ESP32** and an
> **in-process broker**. The firmware itself is **not** part of the repository.

## 41. MQTT Architecture

**[IMPLEMENTED] [TESTED-AUTO] [SIMULATED]**

- **Off by default** (`SMARTHOME_MQTT_ENABLED=false`): nothing about MQTT is loaded and no broker is needed.
- **Per-device opt-in:** `SMARTHOME_MQTT_DEVICES='["fan_living_room","light_living_room"]'` switches those devices to `ESP32MQTTDevice`; the others stay virtual (mixed mode). The config refuses unknown ids, and refuses ESP32 devices or MQTT sensors when MQTT is disabled.
- **Modules:** `app/mqtt/topics.py` (the only place topics are built and parsed), `messages.py` (JSON models), `client.py` (`PahoTransport`, paho-mqtt v2 API, `clean_session=True`, backend Last Will), `manager.py` (`MQTTManager`: one shared connection, routing, sensors, availability), `memory.py` (`InMemoryBroker` for tests and demos), `devices/esp32.py` (driver), `sensors/mqtt.py` (sensor provider).
- **The AI agent and gestures never publish MQTT.** They call `CommandService` as before, and the factory decides per device whether a command reaches a virtual device or an ESP32.
- **Broker independence:** if the broker is down, the backend still starts. Virtual devices, AI, gestures and the dashboard keep working, and ESP32 devices show UNKNOWN. The client reconnects and resubscribes automatically, and recovers retained state and availability.
- **Development brokers:** Mosquitto via Docker (`simulation/mosquitto/docker-compose.yml`, `eclipse-mosquitto:2`, bound to `127.0.0.1:1883`, anonymous for local development only) or the pure-Python `amqtt` (`simulation/amqtt.yaml`, `127.0.0.1:1883`).

## 42. ESP32 Readiness

**[IMPLEMENTED] driver and contract; [PENDING] real hardware**

`ESP32MQTTDevice` (`devices/esp32.py`, 300 lines) reuses the device spec for command **and** state validation. **Publishing is never treated as success.** A command succeeds only on an acknowledgement on `home/{id}/state` where:
- `device_id` and `command_id` match,
- `state` passes the spec strictly (types and ranges),
- the state **reflects** the command (e.g. `set_speed 70` → `speed == 70`).

| Received | Result |
|---|---|
| Matching ack, matching state | Success: confirmed state + event (`details.transport="mqtt"`, `command_id`, `ack_latency_ms`) |
| Wrong/unknown `command_id`, other device, malformed JSON, impossible state | Ignored; the command still times out |
| Matching ack, valid but different state | `502 device_state_mismatch`; the reported state is shown as the device's truth (`state_report` event) |
| Same ack again | Ignored (one event only) |
| Ack after the timeout | Recorded as `late_acknowledgement` |
| `command_id: null` | Spontaneous device report (boot, wall switch) → `state_report` event, `source=mqtt` |
| No ack in time | `504 device_timeout` (default **3 s**, `SMARTHOME_MQTT_COMMAND_TIMEOUT_S`, capped at 30 s); no event; state unchanged; device shows UNKNOWN |
| Device offline | `503 device_unavailable` immediately; nothing published |

**Firmware requirements** (from the README "Moving to a real ESP32"; firmware **not implemented** in this repository):
- Wi-Fi plus NTP time; a clean session with Last Will `home/{id}/availability=offline` (QoS 1, retained).
- Publish `online` and the current state (retained, `command_id: null`).
- Subscribe to `home/{id}/set`; for each command: validate, drop it if expired, drive the relay or PWM, then publish the resulting state with the same `command_id`.
- Sensor board publishes at least every 15 s; optional power meter.
- Suggested libraries: Arduino / ESP-IDF, PubSubClient or esp-mqtt, ArduinoJson.

## 43. Fake ESP32 / Simulator

**[IMPLEMENTED] [TESTED-AUTO] (`test_fake_esp32.py`, 16 tests)**. File: `backend/simulation/mqtt_esp32.py` (419 lines), `backend/simulation/scenarios.py`.

- One simulated board per device, each with its **own MQTT connection and Last Will**, like real hardware.
- Each board publishes availability and retained state, validates commands (shape, device id, expiry, action, parameters), applies the same physics as the virtual device, and acknowledges.
- `FakeSensorBoard` publishes DHT22 / PIR / LDR-style readings every 5 s using the simulated daily cycle. Device boards publish power readings.
- **Failure scenarios** (switchable at runtime: `python -m simulation.scenarios <device|sensors> <scenario>`):

| Scenario | Behaviour |
|---|---|
| `normal` | Immediate acknowledgement |
| `delay` | Acknowledgement after `--delay` s |
| `no_ack` | No response |
| `offline` | Publishes `offline`, ignores commands |
| `wrong_command_id` | Executes, acknowledges with another id |
| `wrong_state` | Acknowledges with an impossible state |
| `malformed_ack` | Invalid JSON |
| `duplicate_ack` | Acknowledges three times |
| `reconnect` | Goes offline, returns after `--reconnect-after` s |
| Sensors: `normal`, `stale`, `invalid`, `offline` | Readings stop / become implausible / board offline |

## 44. MQTT Topics and Message Flow

| Topic | Direction | Payload | Retained |
|---|---|---|---|
| `home/{device_id}/set` | backend → device | command JSON | no |
| `home/{device_id}/state` | device → backend | confirmed state / acknowledgement JSON | yes |
| `home/{device_id}/availability` | device → backend | `online` / `offline` (device's Last Will) | yes |
| `home/sensors/{temperature,humidity,occupancy,ambient_light}` | sensor board → backend | reading JSON | no |
| `home/sensors/availability` | sensor board → backend | `online` / `offline` (Last Will) | yes |
| `home/energy/{device_id}` | device → backend | measured power JSON | no |
| `home/backend/availability` | backend | `online` / `offline` (backend's Last Will) | yes |

The backend subscribes to `home/+/state`, `home/+/availability`, `home/sensors/+` and `home/energy/+` (QoS 1). Device ids must match `^[a-z0-9_]+$` and must not be `sensors`, `energy` or `backend`.

**Command** (QoS 1, not retained):
```json
{"command_id": "<uuid4>", "device_id": "fan_living_room", "action": "set_speed",
 "parameters": {"value": 70}, "issued_at": "…Z", "expires_at": "…Z"}
```
**Acknowledgement** (retained): `{"device_id", "command_id", "timestamp", "state": {"is_on": true, "speed": 70}}`
**Sensor reading:** `{"sensor_id": "dht22_1", "timestamp": "…Z", "value": 29.4}`
**Energy:** `{"timestamp": "…Z", "power_w": 41.2}`

See [Diagram F](#f-mqttesp32-architecture).

## 45. Device Availability Behavior

| State | When | Behaviour |
|---|---|---|
| **ONLINE** | The device published `online`, or any message from it arrived | Commands accepted |
| **OFFLINE** | `offline` published, or the broker published the Last Will | Commands fail at once with `503 device_unavailable` ("Living Room Fan is offline."). Nothing is published. The last confirmed state stays visible (including 3D) with an OFFLINE badge. |
| **UNKNOWN** | Nothing reported yet, the backend lost the broker, or the device timed out | A command may be attempted; the timeout bounds it |

- A device going offline mid-command, or a lost broker connection, fails the pending command immediately.
- Availability changes are shown as warnings in the UI (`connectivity.test.jsx`).
- **Virtual devices** are always `online`.
- `GET /api/v1/iot/status` reports the live connection (enabled, connected, broker, client id, connected since, messages received/ignored), per-device driver, status and last seen, and per-sensor freshness.

---

# Part I: Reliability and Interfaces

## 46. Reliability and Failure Handling

**[IMPLEMENTED] [TESTED-AUTO] (`test_reliability.py` 35 tests; frontend `cameraSession`, `polling`, `client`, `unavailableStates`)**

| Failure | What the user sees | What keeps working |
|---|---|---|
| Backend unavailable | Header **Offline**; banner "Connection to the backend lost", last known state labelled as not live; command error toast | Polling continues (never overlapping) and recovers automatically; requests time out after 15 s |
| AI provider unavailable (no or invalid key, outage, timeout, bad output) | `503 ai_unavailable`, "AI service is currently unavailable."; nothing executed; attempt kept in AI history | Dashboard, direct control, gestures, events, ML. Whole plan capped at 120 s. |
| Camera denied or missing, MediaPipe load or crash | Clear messages ("Camera permission was denied…", "No camera was found…", "Could not load the hand-tracking model…") and a **Try again** button | Everything else. Camera stream, frame loop and MediaPipe are released on every exit path. |
| WebGL unavailable or context lost | 2D floor plan with the same live state | All controls |
| ML unavailable | `503 ml_unavailable`; cards "No prediction available" / "Anomaly detection unavailable" | AI (without ML context), dashboard, gestures |
| Invalid or missing sensor data | `environment: null` plus `sensor_error`; UI "Sensors unavailable" | Predictions run but are `reliable: false`; the AI says sensors are unavailable |
| Hardware timeout / offline / mismatch | 504 / 503 / 502 with a clear message; last confirmed state kept | Other devices |
| Partial AI plan failure | That action `failed`; others reported accurately | — |

Further guarantees: failed or rejected commands never mutate state or create success events, and repeated or concurrent commands are serialised per device.

## 47. Error Handling

**One error envelope everywhere** (`backend/app/api/errors.py`):
```json
{"error": {"code": "...", "message": "...", "details": ...}}
```

| Code | HTTP | Meaning |
|---|---|---|
| `device_not_found` | 404 | Unknown device |
| `unsupported_command` | 400 | Action not supported (e.g. `turn_on` on the door) |
| `invalid_command` | 422 | Value invalid (brightness 150, AC 35 °C, missing value…) |
| `invalid_request` | 422 | Malformed body, unknown field, `source` ≠ `frontend` on the direct endpoint |
| `intent_not_applicable` | 400 | Intent lacks a capability on the target (e.g. THUMBS_UP on the door) |
| `gesture_intent_mismatch` / `gesture_not_actionable` / `confidence_below_threshold` / `invalid_gesture_value` | 422 | Gesture checks |
| `action_blocked` | 403 | Gesture block list / gesture unlock disabled |
| `device_unavailable` | 503 | Device offline / broker unreachable |
| `device_timeout` | 504 | No hardware acknowledgement in time |
| `device_state_mismatch` | 502 | Hardware acknowledged a different state |
| `ai_unavailable` | 503 | AI provider failed; nothing executed |
| `confirmation_not_found` | 404 | No pending confirmation with that id |
| `confirmation_expired` | 410 | Confirmation window passed |
| `ml_unavailable` | 503 | ML failed or disabled |
| `invalid_features` | 422 | Bad ML feature overrides |
| `not_found` / `method_not_allowed` | 404 / 405 | Unknown route / wrong method |
| `internal_error` | 500 | Unexpected exception; no internals leaked (the traceback is logged server-side only) |

AI per-action rejection codes are listed in §19. The frontend parses the envelope into `ApiError`.

## 48. Browser Behavior

| Topic | Fact |
|---|---|
| Browsers verified | **Microsoft Edge** (user's manual real-device test, 2026-10-07). Headless Edge was also used during development [TESTED-DEV]. Chrome is named in UI text for voice; **testing in Chrome is not established from the repository**. |
| Camera | Requires `localhost` or HTTPS (browser rule); permission prompt; one hand |
| Microphone | Permission prompt; Web Speech API needed (Chrome/Edge); online speech service |
| Hand model | Downloaded on first Gesture-page visit (~7.8 MB per README); WASM runtime self-hosted |
| WebGL | Used for the 3D twin and the MediaPipe GPU delegate; fallbacks: 2D floor plan / CPU delegate |
| Reduced motion | Honoured (`prefers-reduced-motion`): no spin, particles or beams |
| Tabs / navigation | Leaving the Gesture page stops the camera and cancels a pending door unlock. Leaving the assistant page stops voice. |
| Polling | Every 5 s, non-overlapping, after-command refresh |

## 49. API Endpoints

Base: `http://localhost:8000` (dev). Prefix `/api/v1`. Interactive docs: **Swagger UI at `/docs`** (FastAPI default; ReDoc at `/redoc`, schema at `/openapi.json`).

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Service info (name, description, status, docs link, API prefix) |
| GET | `/api/v1/health` | Liveness (`{"status":"ok"}`) |
| GET | `/api/v1/home/state` | Full home snapshot |
| GET | `/api/v1/devices` | All devices |
| GET | `/api/v1/devices/{device_id}` | One device |
| POST | `/api/v1/devices/{device_id}/command` | Direct command `{action, value?, source?="frontend"}` |
| GET | `/api/v1/events?limit&device_id` | Device events, newest first |
| GET | `/api/v1/gestures/config` | Gesture→intent mapping, threshold, blocked actions |
| POST | `/api/v1/gestures/commands` | Execute a recognised gesture `{gesture, intent, confidence, target_device_id, value?}` (may return a `confirmation` for a door unlock request) |
| GET | `/api/v1/gestures/events?limit` | Gesture history |
| POST | `/api/v1/ai/command` | Natural-language request `{message}` (1–1000 chars) |
| POST | `/api/v1/ai/confirmations/{confirmation_id}` | Confirm or cancel a held unlock `{decision: "confirm"|"cancel"}` |
| GET | `/api/v1/ai/status` | Provider, model, mock flag, AI intents, per-device capabilities, security policy |
| GET | `/api/v1/ai/history?limit` | Recent AI interactions |
| GET | `/api/v1/ml/status` | Model versions, metrics, feature importances, simulated-data note |
| POST | `/api/v1/ml/predict` | Fan-usage prediction (optional overrides) |
| GET | `/api/v1/ml/anomalies` | Live per-device assessment plus recent and active anomalies |
| POST | `/api/v1/ml/anomalies/check` | Assess `{device_id, power_w, timestamp?}` |
| GET | `/api/v1/iot/status` | MQTT connection, device availability, sensor freshness |

Total: 18 routes under `/api/v1` plus `/`. CORS allows only `GET` and `POST`.

## 50. Configuration / Environment Variables

**Backend** (`backend/app/config.py`; prefix `SMARTHOME_`; `.env` supported and git-ignored; template `backend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `SMARTHOME_LOG_LEVEL` | `INFO` | Logging |
| `SMARTHOME_CORS_ORIGINS` | localhost/127.0.0.1 on 5173 and 5174 | Allowed browser origins (JSON list; `*` refused) |
| `SMARTHOME_EVENT_LOG_MAX_SIZE` | 1000 | Event ring buffer |
| `SMARTHOME_VIRTUAL_DEVICE_LATENCY_MS` | 0 | Simulated device delay |
| `SMARTHOME_SENSOR_SEED` | unset | Reproducible sensor simulation |
| `SMARTHOME_GESTURE_CONFIDENCE_THRESHOLD` | 0.75 | Gesture gate (client and server) |
| `SMARTHOME_GESTURE_BLOCKED_ACTIONS` | `["unlock"]` | Actions gestures may not trigger directly |
| `SMARTHOME_GESTURE_HISTORY_MAX_SIZE` | 500 | Gesture history size |
| `SMARTHOME_GESTURE_DOOR_UNLOCK` | `true` | Allow the pinch-requested (confirmation-gated) door unlock |
| `SMARTHOME_AI_PROVIDER` / `AI_PROVIDER` | `mock` | `mock` or `anthropic` |
| `SMARTHOME_AI_MODEL` / `AI_MODEL` | `claude-opus-5-5` | Claude model id |
| `SMARTHOME_AI_API_KEY` / `AI_API_KEY` | unset | Optional; otherwise `ANTHROPIC_API_KEY` or an `ant auth login` profile |
| `SMARTHOME_AI_EFFORT` | `medium` | `low`…`max` |
| `SMARTHOME_AI_MAX_TOOL_ROUNDS` | 4 | Read-only tool rounds |
| `SMARTHOME_AI_TIMEOUT_S` | 60 | Per provider call |
| `SMARTHOME_AI_REQUEST_TIMEOUT_S` | 120 | Whole plan |
| `SMARTHOME_AI_ALLOW_UNLOCK` | `true` | Allow explicit AI (and gesture) unlock requests |
| `SMARTHOME_AI_UNLOCK_REQUIRES_CONFIRMATION` | `true` | Hold unlocks for confirmation |
| `SMARTHOME_AI_CONFIRMATION_TIMEOUT_S` | 30 (max 300) | Confirmation window |
| `SMARTHOME_AI_HISTORY_MAX_SIZE` | 100 | AI history size |
| `SMARTHOME_ML_ENABLED` | `true` | Train and serve ML |
| `SMARTHOME_ML_SEED` | 7 | Simulation seed |
| `SMARTHOME_ML_DATASET_DAYS` | 60 (7–365) | Simulated history length |
| `SMARTHOME_ML_PREDICTION_THRESHOLD` | 0.5 | ON/OFF threshold |
| `SMARTHOME_ML_ANOMALY_ACTIVE_MINUTES` | 15 | "Active" anomaly window |
| `SMARTHOME_MQTT_ENABLED` | `false` | Enable the MQTT layer |
| `SMARTHOME_MQTT_HOST` / `_PORT` | `127.0.0.1` / 1883 | Broker |
| `SMARTHOME_MQTT_USERNAME` / `_PASSWORD` | unset | Credentials (password is a SecretStr, never logged) |
| `SMARTHOME_MQTT_CLIENT_ID` | `intellihome-backend` | Client id |
| `SMARTHOME_MQTT_KEEPALIVE_S` | 30 | Keepalive |
| `SMARTHOME_MQTT_COMMAND_TIMEOUT_S` | 3 (max 30) | Acknowledgement timeout |
| `SMARTHOME_MQTT_DEVICES` | `[]` | Devices on ESP32 |
| `SMARTHOME_SENSOR_SOURCE` | `simulated` | `simulated` or `mqtt` |
| `SMARTHOME_SENSOR_MAX_AGE_S` | 30 | Sensor freshness |
| `SMARTHOME_TEST_MQTT_HOST` | unset | Enables the 2 real-broker tests |

**Frontend** (`frontend/.env.example`):

| Variable | Default |
|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` |
| `VITE_HAND_LANDMARKER_MODEL_URL` | `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task` |

---

# Part J: Testing and Build

## 51. Testing Strategy

- **Backend:** pytest (`backend/tests/`, 22 test files + helpers). It uses FastAPI `TestClient` and **httpx** for API-level tests, and direct unit tests for domain, ML and MQTT logic.
  - **No test calls a real LLM.** Tests use `MockAIProvider` or scripted fake providers; the Anthropic provider is tested with a fake SDK client.
  - **MQTT** is tested end to end with the **in-process `InMemoryBroker`** (retained messages, wildcards, Last Will) and the **Fake ESP32** firmware.
  - **Real-broker tests** (`test_mqtt_broker.py`, 2 tests) are **skipped** unless `SMARTHOME_TEST_MQTT_HOST` is set.
- **Frontend:** Vitest 5 in a Node environment (no jsdom). Pure modules are unit-tested (classifier, stabilizer, pinch detector, adjustment, door-unlock controller, pinch routing, voice session, camera session lifecycle, polling, API client, lifecycle reducer, visual mappings, ML helpers). Components are rendered to static markup.
  - Gestures use **synthetic 3D hand poses** (`syntheticHand.js`), including rotated hands.
  - The voice session uses a **fake `SpeechRecognition`** with fake timers.
- **Regression-driven:** several tests are named after real bugs. Examples: "setInterval stacked requests", "camera stream arrives after the model failed", "pinch during confirmation", "Main Door pinch went to adjustment".
- **Manual verification:** real browser and devices (§54).

## 52. Backend Test Results

**Run on `84a0233`, 2026-10-07, Python 3.12.4:** **524 passed, 2 skipped** in ~38 s (526 collected).
The skips are `tests/test_mqtt_broker.py:42` and `:58`: "set SMARTHOME_TEST_MQTT_HOST to run against a real broker".

| Test file | Tests | Scope |
|---|---|---|
| `test_capabilities.py` | 44 | Explicit capabilities per device; capability API; door never accepts power intents; door intents invalid for appliances |
| `test_mqtt_contract.py` | 40 | MQTT off by default; config from env; unsafe config refused; reserved ids; topic build/parse; command serialisation; unique command ids |
| `test_ai_agent.py` | 38 | Execution via CommandService with `ai_agent` source; parameter intents; invalid/duplicate/malformed actions never run; provider failure; door policy for indirect vs explicit requests |
| `test_door_confirmation.py` | 35 | Unlock held; spoken confirmation; bare "yes" insufficient; cancel; other request drops it; buttons; input validation; expiry; 410 |
| `test_reliability.py` | 35 | Error envelope; safe 500; failed commands never mutate; serialisation under concurrency; hung/buggy providers → ai_unavailable; AI outage isolation; partial plans |
| `test_domain.py` | 34 | Virtual device transitions; previous/new state; validation leaves state untouched; AC set point while off; power models; event store ring buffer; energy integration |
| `test_ai_api.py` | 31 | README examples end to end ("turn off everything" leaves the door unchanged, "leaving home", lock/unlock, status/energy queries, fan on + speed 70) |
| `test_device_commands.py` | 30 | Direct commands, ranges, strict integers, fan speed 0 = off |
| `test_gesture_unlock.py` | 27 | First pinch only creates a pending confirmation; second confirms once through CommandService; repeats never unlock; cancel; expiry; only PINCH may request; low confidence refused; generic gestures never unlock; OPEN_PALM still stops the fan; pinch still adjusts fan/AC; disable switches |
| `test_gestures_api.py` | 27 | Each gesture's effect; OPEN_PALM does not touch the door; SELECT changes nothing; THUMBS_UP cannot lock the door; input validation |
| `test_esp32_device.py` | 24 | Success only after a matching ack; delay; duplicates; timeout; wrong id / other device / impossible / malformed ignored; mismatched state → 502 |
| `test_ml_integration.py` | 22 | ML status with simulated-data note; prediction from live state; overrides and missing values; bad requests; live devices normal; anomalies logged as ML events; ML cannot issue commands |
| `test_adjustment_prep.py` | 21 | ADJUST resolves to each device's value capability (fan, AC, light); never the door; mapping unchanged; ranges published; invalid values; pinch sets speed/temperature; out-of-range refused; low confidence refused |
| `test_mqtt_sensors.py` | 21 | Valid readings; stale readings unavailable; implausible rejected; malformed messages; offline board; sensor data reaches HomeState and ML; stale data not used by AI/ML |
| `test_gesture_service.py` | 17 | Resolver by capability; power intents never resolve for the door; low confidence and SELECT never reach CommandService |
| `test_fake_esp32.py` | 16 | Firmware boot and ack; delay; bad acks time out without faking state; duplicate ack → one event; offline fails fast; power cut → Last Will; reconnect; scenario switching; expired/foreign commands dropped |
| `test_ml_models.py` | 15 | Deterministic datasets; realistic correlations; ~2 % injected faults; predictions valid and explained; imputation; metrics beat the baseline; 168 sampled legitimate states normal; fault patterns flagged |
| `test_cors.py` | 14 | Preflight for 5173/5174 on every polled endpoint; unapproved origin rejected; config-driven; wildcard refused |
| `test_anthropic_provider.py` | 13 | Structured plan; read-only tool loop; model cannot call a control tool; unusable responses and SDK failures → provider errors; bounded tool loop |
| `test_events_and_home_state.py` | 13 | Events logged; direct commands cannot claim another source; failed commands not logged; ordering/filtering; home state contents; health and root |
| `test_mqtt_api.py` | 7 | Dashboard, gesture and AI commands reach hardware via CommandService and wait for the ack; offline and timeout behaviour; IoT status; unreachable broker never blocks virtual devices, AI or gestures |
| `test_mqtt_broker.py` | 2 (skipped) | Real-broker connect/reconnect and full round trip with Last Will |
| **Total** | **526 collected → 524 passed, 2 skipped** | |

## 53. Frontend Test Results

**Run on `84a0233`, 2026-10-07, Node 22.16.0, Vitest 5.0.3:** **19 files, 212 passed, 0 failed.**

| Test file | Tests | Scope |
|---|---|---|
| `voice/__tests__/voiceSession.test.js` | 47 | Wake phrase in one breath and split; normalisation; joining limits; interim wake; repeated wake phrase not sent; command window; denial, errors, restart limits, cleanup |
| `gestures/__tests__/doorUnlock.test.jsx` | 22 | OPEN_PALM → STOP unchanged and FOUR_FINGERS removed; first pinch only requests; second confirms once; quick repeats ignored; backend refusal and blocked request shown honestly; fan/AC still adjust; OPEN_PALM / other gestures / hand loss / expiry cancel; Door unlock panel texts |
| `state/__tests__/state.test.js` | 18 | AI lifecycle reducer (listening → thinking → planning → executing → success); query-only; transport errors; home status checks; energy history; activity feed |
| `components/3d/__tests__/visualState.test.js` | 16 | Backend state → light, fan, AC, door visuals; clamping; orb states |
| `lib/__tests__/assistant.test.js` | 13 | Action descriptions, changed states, AI outage messaging, spoken summaries |
| `gestures/__tests__/ruleClassifier.test.js` | 12 | Each gesture from synthetic and rotated poses above threshold; thumb-up rule; ambiguous hand below threshold; finger scores |
| `lib/__tests__/ml.test.js` | 12 | Prediction headline and reasons; anomaly highlighting; badges only for ON predictions; anomaly check in home status; ML events in activity |
| `gestures/__tests__/pinchAdjustment.test.js` | 10 | Pinch ratio; stable start/clear release (no single-frame trigger); fist is not a pinch; hand loss cancels; fan up/down; AC cooler/warmer within 16–30 |
| `components/__tests__/connectivity.test.jsx` | 9 | OFFLINE/UNKNOWN labels keep the last confirmed state; ESP32 driver shown; availability warnings; attribution over MQTT |
| `gestures/__tests__/cameraSession.test.js` | 9 | Camera/loop/video released on stop; late streams released; crash mid-stream; unsupported browser messages |
| `gestures/__tests__/pinchRouting.test.js` | 7 | Door first pinch → pending, never adjustment; second pinch confirms once; in-flight pinches ignored; fan/AC adjust; open palm cancels; OPEN_PALM → STOP unchanged |
| `gestures/__tests__/stabilizer.test.js` | 7 | Hold to commit; threshold; NEUTRAL/UNKNOWN never commit; fire once until release; dropouts tolerated; cooldown; progress |
| `components/ml/__tests__/mlCards.test.jsx` | 7 | Prediction card shows real probability and is never presented as an action; anomaly panel |
| `api/__tests__/client.test.js` | 5 | Network error; 15 s timeout; longer AI timeout; error envelope parsing; non-JSON body |
| `components/__tests__/unavailableStates.test.jsx` | 5 | Sensor strip, 3D overlay, low-confidence prediction, AI outage without a fake reply |
| `gestures/__tests__/adjustment.test.js` | 4 | Ranges and directions; clamping; one command on release; nothing if unchanged or lost |
| `components/__tests__/doorConfirmation.test.jsx` | 4 | Assistant confirmation UI: time left, both choices, outcomes, no beam for held/cancelled |
| `state/__tests__/polling.test.js` | 3 | Never overlaps; survives failures; stops cleanly |
| `components/assistant/__tests__/LifecyclePipeline.test.js` | 2 | Pipeline stage reveal |
| **Total** | **212** | |

## 54. Browser / Integration Testing

| Kind | What | Status / evidence |
|---|---|---|
| Real-device manual test | User reports (2026-10-07) verifying, **locally in Microsoft Edge** with a real webcam and microphone: "Hey Nova" wake word ✅, voice command flow ✅, fan speed pinch ✅, AC temperature pinch ✅, double-pinch Main Door unlock ✅, Open Palm → STOP ✅, existing gesture mappings ✅, 0.6 s stabilizer ✅, existing security/validation ✅ | [TESTED-MANUAL]; no recordings or scripts in the repository |
| Real-webcam finding | A `FOUR_FINGERS` door gesture was misclassified as `OPEN_PALM` on a real webcam, so it was replaced by the double pinch (`b9cbff0`) | [TESTED-MANUAL] (user feedback) |
| Real-browser bug found | A pinch with the Main Door selected showed "Main Door has no adjustable value…"; fixed in `84a0233` with explicit routing | [TESTED-MANUAL] + regression tests |
| Real-browser voice bug | The Edge wake → command transition failed on short phrases; fixed in `7c97737` | [TESTED-MANUAL] + regression tests |
| Headless Edge driving | During development, a headless Edge (Chrome DevTools Protocol) driver ran the app with injected or fake camera input on separate ports (backend 8100 / frontend 5190) | [TESTED-DEV]; scripts were in a scratch directory and are **not committed** |
| MediaPipe sample photos | README: Google's test photos fed as a fake webcam, recognised at 96–98 % and executed with `source=gesture` | [TESTED-DEV] (README-reported) |
| API integration | FastAPI `TestClient` end to end across all routers (backend suite) | [TESTED-AUTO] |
| MQTT integration | Backend ↔ in-memory broker ↔ Fake ESP32 end to end | [TESTED-AUTO] |
| Real broker | 2 tests exist; skipped by default | Whether they were run against a real broker is **not established from repository** |
| Real ESP32 / sensors | — | **[PENDING]** |

## 55. Production Build

**Run on `84a0233`, 2026-10-07:** `npm run build` (Vite 8) → **✓ built in ~1.5 s**. Output (then deleted; `dist/` is git-ignored):

| Asset | Size | Gzip |
|---|---|---|
| `index.html` | 0.40 kB | 0.27 kB |
| `index-*.css` | 64.11 kB | 10.49 kB |
| `index-*.js` (main app) | 451.64 kB | 141.44 kB |
| `GesturePage-*.js` (lazy) | 187.40 kB | 56.53 kB |
| `SmartHomeScene-*.js` (lazy 3D) | 982.85 kB | 262.43 kB |
| `vision_wasm_internal-*.js` | 323.37 kB | — |
| `vision_wasm_internal-*.wasm` (MediaPipe runtime) | 11,756.95 kB | 3,478.91 kB |

Vite prints a **warning** that some chunks exceed 500 kB after minification. This is a warning, not a failure.

---

# Part K: Deployment, History and Status

## 56. Deployment Architecture

**[DEPLOYED: not established]**

- **Development topology (established):**
  - Backend: `uvicorn app.main:app --reload --port 8000` (Swagger at `/docs`).
  - Frontend: `npm run dev` on Vite port **5173** (moves to **5174** if busy).
  - The browser calls `http://localhost:8000/api/v1`.
  - Optional: MQTT broker on `127.0.0.1:1883` plus the Fake ESP32 process (the README "four terminals" setup).
- **Source distribution (established):** the code is on GitHub at `MUKULSHARMA2711/Smart_hand_gesture_Home`, `main` = `84a0233`, with all release tags pushed. This is source publication, not a running deployment.
- **Production hosting:** the repository contains **no** deployment configuration (no `vercel.json`, Netlify config, Dockerfile for the app, Procfile or CI workflow).
  - In an earlier working session the user asked which frontend environment variable a Vercel deployment needs. The answer is `VITE_API_BASE_URL`. Whether a Vercel deployment exists, which commit it serves, and where the backend would be hosted is **not established from repository**.
  - A hosted frontend would also need: a reachable HTTPS backend; `SMARTHOME_CORS_ORIGINS` set to the hosted origin (the defaults allow only localhost); and HTTPS for camera and microphone access.
- **Do not claim** a public live deployment in the report unless the user supplies evidence such as a URL and screenshot.

## 57. Git Milestones and Commits

17 commits on `main` (all by the project author; recent commits co-authored with Claude). Dates are commit dates.

| # | Commit | Date (2026) | Message | Size | Milestone |
|---|---|---|---|---|---|
| 1 | `79e4af8` | 10-03 | feat: IntelliHome Day 1 virtual IoT backend and dashboard | 80 files, +4347 | **Virtual IoT foundation** (no tag) |
| 2 | `fb47e2e` | 10-04 | feat: add hand gesture control | 44 files, +2742/−52 | **Gesture control**, v0.2.0 |
| 3 | `4629709` | 10-04 | feat: add AI home agent | 50 files, +3084/−101 | **AI Home Agent**, v0.3.0 |
| 4 | `f3bd579` | 10-06 | feat: add 3d command center | 58 files, +4195/−179 | **3D Command Center**, v0.4.0 |
| 5 | `d74e21d` | 10-06 | feat: add predictive and anomaly intelligence | 56 files, +2538/−76 | **ML intelligence**, v0.5.0 |
| 6 | `6a5415e` | 10-06 | feat: harden IntelliHome reliability | 62 files, +1631/−201 | **Reliability/hardening**, v0.6.0 |
| 7 | `6087934` | 10-06 | feat: add MQTT hardware readiness | 58 files, +3826/−113 | **MQTT/ESP32 readiness**, v0.7.0 |
| 8 | `d0ab10b` | 10-07 | feat: add secure door unlock confirmation | 24 files, +721/−27 | Voice + secure unlock (part 1) |
| 9 | `a54ea80` | 10-07 | feat: add browser voice interaction | 8 files, +689/−2 | Voice ("Hey IntelliHome" at the time) |
| 10 | `4440864` | 10-07 | chore: prepare gesture adjustment interfaces | 9 files, +259/−8 | ADJUST prep, **v0.8.0** |
| 11 | `8595c34` | 10-07 | feat: add gesture adjustment for fan and ac | 13 files, +545/−18 | **Gesture adjustment**, v0.9.0 |
| 12 | `49ca328` | 10-07 | fix: improve edge voice wake word detection | 2 files, +152/−11 | Voice wake-word fixes |
| 13 | `b6c8d66` | 10-07 | fix: simplify voice wake phrase | 5 files, +71/−77 | Wake phrase → "Hey Nova" |
| 14 | `7c97737` | 10-07 | fix: fix voice wake state transition | 3 files, +181/−21 | Wake → command transition (Edge) |
| 15 | `fd000cb` | 10-07 | feat: add secure gesture unlock for door | 22 files, +662/−15 | FOUR_FINGERS door request (later replaced) |
| 16 | `b9cbff0` | 10-07 | fix: use double pinch for secure door unlock | 18 files, +257/−177 | **Secure double-pinch door unlock** |
| 17 | `84a0233` | 10-07 | fix: route door pinch before adjustment | 4 files, +149/−2 | Pinch routing fix, **v0.10.0** |

**Concise timeline:**
- 2026-10-03: Virtual IoT foundation.
- 10-04: Gesture control; AI Home Agent.
- 10-06: 3D Command Center; ML intelligence; reliability hardening; MQTT/ESP32 readiness.
- 10-07: Secure unlock confirmation; voice; adjustment prep; pinch adjustment for fan and AC; voice wake fixes ("Hey Nova"); secure double-pinch door unlock; pinch routing fix.

## 58. Release Tags

All tags are **lightweight** (no annotation message) and **pushed** to GitHub. No other tags exist.

| Tag | Commit | Contains (new since previous tag) |
|---|---|---|
| `v0.2.0-gesture-control` | `fb47e2e` | Day 1 foundation + gesture control |
| `v0.3.0-ai-home-agent` | `4629709` | AI home agent, capabilities, door policy |
| `v0.4.0-3d-command-center` | `f3bd579` | 3D digital twin, pages, AI lifecycle |
| `v0.5.0-ml-intelligence` | `d74e21d` | Random Forest + Isolation Forest |
| `v0.6.0-reliability` | `6a5415e` | Error envelope, failure isolation |
| `v0.7.0-mqtt-hardware-readiness` | `6087934` | MQTT driver, Fake ESP32 |
| `v0.8.0-voice-secure-unlock` | `4440864` | `d0ab10b` secure unlock confirmation, `a54ea80` voice, `4440864` ADJUST prep |
| `v0.9.0-gesture-adjustment` | `8595c34` | Pinch adjustment for fan and AC |
| `v0.10.0-secure-gesture-unlock` | `84a0233` | Voice wake fixes ("Hey Nova"), secure double-pinch door unlock, pinch routing fix |

## 59. Known Limitations

**Hardware and data**
1. **No physical hardware tested:** ESP32, relays, DHT22/PIR/LDR sensors and power meters are **[PENDING]**. The firmware is not in the repository.
2. **ML is trained on simulated data only.** Metrics describe the simulation. There is only one prediction target (living-room fan). Models retrain at every startup; no model persistence, no real-data retraining yet.
3. **Sensors are simulated by default.**

**Security**
4. **No authentication or authorization**, no rate limiting, no HTTPS configuration. Anyone who can reach the API can control devices.
5. **The direct dashboard endpoint unlocks the door immediately** (no confirmation). Only AI, voice and gesture unlocks are confirmation-gated.
6. **The door policy's negation check is rule-based**, not language understanding. A negation after the verb ("unlock the door… not!") is not detected. This is mitigated by the mandatory confirmation.
7. **The AI mock provider is keyword-based.** The real Claude provider is unit-tested only with a fake client; live-API behaviour is not verified in the repository.
8. **Single household, single pending confirmation slot.** A new unlock request or any other AI request replaces or drops the pending one.

**Persistence**
9. **No persistence:** events, gesture and AI histories are in-memory ring buffers. Energy kWh resets at restart. The Energy page's power history exists only in the browser tab.

**Gestures and voice**
10. **Gesture classifier is rule-based** and may need threshold tuning for lighting, distance or partial hands. One hand only. Targeting is explicit (selected device). Pinch "confidence" is a geometric margin that is always ≥ 0.75 for a detected pinch, not a learned probability.
11. **Voice depends on the browser speech service** (Chrome/Edge; online; en-US only).

**Delivery and documentation**
12. **Bundle size:** the 3D chunk is 983 kB (262 kB gzip) and the MediaPipe WASM is 11.8 MB (3.5 MB gzip). Vite warns about chunks over 500 kB.
13. **Development MQTT brokers allow anonymous access** (localhost only). Production broker auth/TLS is documented but not configured.
14. **No automation engine** (`automation` is a reserved event source only).
15. **Deployment:** none established from the repository.
16. **Some README passages and code comments are stale** (Appendix C).

## 60. Current Status

As of **2026-10-07**, commit **`84a0233`**, tag **`v0.10.0-secure-gesture-unlock`**:

| Area | Status |
|---|---|
| Software features (virtual home, gestures, pinch adjustment, double-pinch unlock, AI agent, voice, 3D twin, ML, reliability, MQTT driver) | Complete for the current scope. [IMPLEMENTED] [TESTED-AUTO]; core flows [TESTED-MANUAL] in Edge |
| Automated tests | Backend 524 passed / 2 skipped; frontend 212 passed |
| Production build | Successful (chunk-size warning only) |
| Git | `main` == `origin/main` == `84a0233`; working tree clean; 9 release tags pushed |
| Physical ESP32 and sensors | **[PENDING]** |
| Real-world ML data | **[PENDING]** |
| Public deployment | **Not established from repository** |
| Documentation | README is detailed but partly stale (Appendix C); this source pack is current |

## 61. Future Scope

**[PLANNED]: mentioned in the repository as future work:**
- **Physical ESP32 firmware and hardware** following the documented MQTT contract (README "Moving to a real ESP32"): relays/PWM, DHT22/PIR/LDR, optional power meter, a Mosquitto broker on the LAN with password auth and TLS.
- **Retraining ML on real sensor history** ("With real sensor history, the same pipeline retrains on real data", README).
- **PostgreSQL** event store ("(later) PostgreSQL" in the architecture diagram).
- **A trained gesture model** replacing `ruleClassifier.js` (`vision/README.md`; the README names a TF.js classifier or MediaPipe `GestureRecognizer`).
- **Occupancy prediction and energy forecasting** models (`ml/README.md`).
- **Richer environment simulation**, e.g. AC cooling that affects room temperature (`simulation/README.md`).
- **AI context-based targeting** for gestures instead of explicit selection (README "Targeting").
- **Authentication / stronger confirmation** (`PolicyDecision` "has room for confirmation or authentication later").

**[SUGGESTED]: reasonable extensions not planned in the repository:**
- Automation rules engine (the `automation` source already exists).
- Two-factor door unlock (e.g. PIN, face) and per-user accounts.
- Persistent model storage and model monitoring.
- Multi-language voice and an offline speech engine.
- Mobile/PWA packaging, a hosted deployment with HTTPS.
- Code-splitting to reduce chunk sizes.

---

# Part L: Report-Writing Support

## 62. Viva / Interview Talking Points

1. **"How do you stop the AI from doing something dangerous?"**
   - The LLM only returns *data* (a JSON plan constrained by a schema) and has only read-only tools. The backend re-validates every action: schema, allowed intent, parameters, device, capability, range, policy, duplicates.
   - Only `HomeAgent` executes, through `CommandService`. `call_read_only()` refuses `control_device`.
2. **"Why can't 'turn on everything' unlock the door?"** Three layers: door capabilities are only LOCK/UNLOCK; door changes need dedicated intents; and the policy requires the user's own explicit, non-negated "lock"/"unlock".
3. **"Why a confirmation for unlocking, even when the request is explicit?"** Rule-based negation detection can miss post-verb negation, and unlocking is high-impact. The 30 s single-use confirmation re-validates before executing once.
4. **"Why a double pinch for the door?"** No single gesture should unlock a door. The first pinch only creates a server-side pending confirmation; the second confirms through the same endpoint as the AI, with re-validation. A `FOUR_FINGERS` design was rejected after real-webcam testing because it was misread as an open palm.
5. **"How do you handle noisy gesture recognition?"** Hand-size-normalised geometry in metric world landmarks (rotation-invariant), fuzzy scoring with an ambiguity penalty, a confidence gate on both client and server, a 0.6 s hold with 200 ms grace, fire-once-until-release, and a 1 s cooldown. The pinch uses 4-frame entry and 3-frame exit hysteresis.
6. **"Why send one command on pinch release instead of streaming values?"** It avoids flooding the device and the audit log, gives a preview without side effects, and with real hardware avoids dozens of MQTT round trips. Nothing is sent if the value is unchanged or the hand is lost.
7. **"Is the 3D twin real?"** It is a renderer of backend state only. Pure, unit-tested mappings; animations only smooth toward confirmed values; nothing changes until the backend confirms.
8. **"How good is your ML?"** Be explicit that it is simulated: 87.4 % accuracy vs a 71.3 % baseline, F1 0.767. Isolation Forest F1 0.857–0.968 with ≤ 0.27 % false alarms, all on simulated data. ML only recommends and never executes.
9. **"How would you move to real hardware?"** Configuration only: set `SMARTHOME_MQTT_ENABLED`, `SMARTHOME_MQTT_DEVICES` and `SMARTHOME_SENSOR_SOURCE=mqtt`, then flash firmware implementing the contract. The backend logic is unchanged because `ESP32MQTTDevice` implements the same `Device` interface and reuses the same `DeviceSpec`.
10. **"Why is publishing not success in MQTT?"** A command is confirmed only by a matching `command_id` acknowledgement with a state that passes the spec and reflects the command. Commands have expiry and the client uses a clean session, so late commands never surprise the user.
11. **"What happens when things fail?"** One error envelope; AI, ML, sensors, camera and WebGL are isolated; 503/504/502 for hardware; failed commands never change state or create success events.
12. **"How is voice kept safe?"** Voice is just text into the same AI pipeline. Spoken replies come from backend results, not the LLM's text. The microphone pauses while the assistant speaks. A door unlock still needs "yes, unlock it".
13. **"What are the limitations?"** No auth; the direct unlock endpoint; simulated ML and sensors; no hardware; in-memory storage; rule-based NLP for the mock provider; browser-dependent voice.
14. **"What is your testing evidence?"** 524 backend + 212 frontend automated tests, regression tests for real bugs, end-to-end MQTT with the Fake ESP32, and manual real-device testing in Edge.

## 63. Diagrams for the Final Report

### A. Complete system architecture

```
                                   USER
        ┌───────────────┬───────────────┼────────────────┬───────────────┐
        ▼               ▼               ▼                ▼               ▼
   Dashboard /     Webcam hand      Typed chat      "Hey Nova" voice   (future)
   3D twin click    gestures        (Assistant)     (Web Speech API)   hardware buttons
        │               │               │                │
        │     MediaPipe HandLandmarker  │                │ recognised text
        │     → rule classifier         │                │
        │     → 0.6 s stabilizer        │                │
        │     → pinch detector          │                │
 ───────┼───────────────┼───────────────┼────────────────┼──────── BROWSER (React 19 + Vite)
        │ HTTP /api/v1  │               │                │
        ▼               ▼               ▼                ▼
 POST /devices/   POST /gestures/   POST /ai/command  ◄──┘     POST /ai/confirmations/{id}
   {id}/command     commands              │                         ▲
        │               │                 ▼                         │
        │          GestureService     HomeAgent ── AIProvider (Mock | Claude, read-only tools)
        │          (confidence,           │        PlanValidator → SecurityPolicy
        │           intent, block list)   │        ConfirmationStore (door unlock, 30 s)
        │               │  IntentResolver (intent → capability → device command)
        └───────────────┴─────────┬───────┘
                                  ▼
                           CommandService  ── per-device lock ──►  EventStore (audit, source)
                                  │
                         Device interface (DeviceSpec validation)
                      ┌───────────┴────────────┐
                      ▼                        ▼
               VirtualDevice            ESP32MQTTDevice ── MQTTManager ── MQTT broker ── Fake ESP32 / (real ESP32: PENDING)
                      │                        │
                      └──────────┬─────────────┘
                                 ▼
          HomeState (devices + sensors + energy) ──► MLService (Random Forest, Isolation Forest)
                                 │                          │ insights (read-only)
                                 ▼                          ▼
              GET /home/state (polled 5 s) → 3D twin, dashboards      AI context / tools
```

### B. Gesture processing flow

```
Webcam frame ─► MediaPipe HandLandmarker (WASM/WebGL, in browser)
                    │ 21 image landmarks + 21 world landmarks
          ┌─────────┴───────────────────────────────┐
          ▼                                         ▼
  Pinch detector (pinch.js)                Rule classifier (ruleClassifier.js)
  ratio<0.30 & ≥2 fingers open ×4 frames   finger extension → fuzzy scores → gesture + confidence
  start / move / end / cancel                       │
          │                                         ▼  (fed UNKNOWN while a pinch is engaged)
          ▼                                Stabilizer: ≥0.75 conf, hold 600 ms, grace 200 ms,
   routePinch(device, unlock)              fire once until release, 1 s cooldown
     ├─ door selected / unlock busy ─► Door unlock controller (§25)
     └─ fan / AC ─► Adjustment controller: preview on move; ONE command on release
                                                    │ commit {gesture, confidence}
                                                    ▼
                      useGestureControl.execute → intent from /gestures/config
                                                    │
                    POST /api/v1/gestures/commands {gesture, intent, confidence, target_device_id, value?}
                                                    ▼
      GestureService: intent match → not NEUTRAL/UNKNOWN → confidence ≥ threshold → value rule
                      → IntentResolver (capability) → block list → CommandService(source=gesture)
                                                    ▼
                        DeviceEvent + GestureEvent → response → UI refresh → 3D beam
```

### C. Voice processing flow

```
Enable voice ─► SpeechRecognition (en-US, continuous, interim results)  [state: wake]
   │ interim/final transcript
   ▼
splitWake(): "hey|hay|hi" + "nova" within first 3 words (split results joined ≤ 4 s)
   ├─ wake + command ("Hey Nova, turn on the fan") ──────────────┐
   └─ wake only ─► [command] 8 s window ─► final text ───────────┤
                                                                  ▼
                              [processing] mic detached ─► POST /api/v1/ai/command {message}
                                                                  ▼
                                    HomeAgent (same pipeline as typed text; see Diagram D)
                                                                  ▼
                       spokenSummary(backend results) ─► [speaking] speechSynthesis
                                                                  ▼
                 response.confirmation? ─ yes ─► [command] (reply without wake phrase: "yes, unlock it")
                                         └ no ──► [wake]
Errors / too many restarts (5 in 10 s) / mic denied ─► [error];  Turn off / leave page ─► [off]
```

### D. AI Agent + validation flow

```
User text ─► HomeAgent.handle
   │ pending confirmation? ─► classify_reply: CONFIRM / CANCEL / AFFIRM_ONLY / OTHER(drop)
   ▼
HomeContext (devices+capabilities+state, sensors, energy, 5 events, ML insights)
   ▼
AIProvider.plan()  ── Mock (rules)  |  Claude (structured output, ≤4 rounds of read-only tools)
   │  UNTRUSTED {"message", "actions":[{device_id,intent,parameters}]}   (timeout 120 s → 503)
   ▼
ActionPlan (strict, ≤12 actions) ─► PlanValidator per action:
   schema → AI intent allowed → parameters → device exists → capability → range (spec)
   → SecurityPolicy (explicit, non-negated lock/unlock; unlock ⇒ requires_confirmation) → duplicates
   ▼  (all validated before any executes)
 ├─ rejected ─► status "rejected" + code (never executed)
 ├─ query    ─► status "answered" + data (read-only)
 ├─ unlock   ─► HOLD: PendingConfirmation (30 s) ─► status "awaiting_confirmation"
 └─ valid    ─► AgentTools.control_device ─► CommandService(source=ai_agent) ─► "executed" / "failed"
   ▼
AgentResponse: reply (untrusted) + outcome (backend) + per-action results + device_events
```

### E. Secure door unlock flow

```
            Gesture path (double pinch)                         AI / voice path
 ☝️ select Main Door                                      "unlock the main door"
 👌 pinch #1 ─► POST /gestures/commands                   POST /ai/command
               {PINCH, UNLOCK_DOOR, conf}                        │
                     │                                           ▼
       GestureService (conf ≥ 0.75, door has UNLOCK)     PlanValidator + SecurityPolicy
                     │                                   (explicit, non-negated "unlock")
       HomeAgent.hold_gesture_unlock ── same validator ──┐       │
                     ▼                                   ▼       ▼
          ┌───────────────── ConfirmationStore (ONE pending, expires in 30 s) ─────────────────┐
          │ source=gesture  prompt "Pinch again to confirm"  │ source=ai_agent "Say 'yes, unlock it'" │
          └──────────────────────────┬──────────────────────────────────────────────────────────┘
 👌 pinch #2 ─► POST /ai/confirmations/{id} {"decision":"confirm"}   ◄── "yes, unlock it" / Confirm button
                                     ▼
              HomeAgent._confirm: clear pending (once) → RE-VALIDATE (confirmed=True)
                                     ▼
              CommandService.execute(door_main, unlock, source = original source)
                                     ▼
                       DeviceEvent → UI "✓ Unlocked" → 3D door ajar (amber)
 CANCEL (door stays locked): ✋ open palm · other gesture · hand out of view 1.5 s · camera stop ·
                             device change · page leave · 30 s expiry (410) · "no/cancel" · other request
 IGNORED: pinches while request/confirmation in flight
```

### F. MQTT/ESP32 architecture

```
 CommandService ─► ESP32MQTTDevice._perform(cmd)
                     │ publish QoS1  home/{id}/set {command_id, action, parameters, issued_at, expires_at}
                     ▼
                 MQTTManager (one paho connection, clean session, LWT home/backend/availability)
                     ▼
                 MQTT broker (Mosquitto / amqtt on 127.0.0.1:1883 · in-memory broker in tests)
                     ▼
        Fake ESP32 board (per device, own LWT)         ── (real ESP32 firmware: PENDING)
          validate → drop expired → apply physics
                     │ publish retained home/{id}/state {device_id, command_id, timestamp, state}
                     ▼
 ESP32MQTTDevice: ids match? state valid (spec)? reflects command?
     ├─ yes ─► commit confirmed state → DeviceEvent(details.transport="mqtt", ack_latency_ms)
     ├─ wrong state ─► 502 device_state_mismatch (report shown)
     ├─ no ack in 3 s ─► 504 device_timeout (state unchanged, status UNKNOWN)
     └─ offline (LWT/online topic) ─► 503 device_unavailable (nothing published)
 Sensor board ─► home/sensors/{kind} (≤30 s fresh) ─► MQTTSensorProvider ─► HomeState
 Device power ─► home/energy/{id} ─► measured power_w (if after last state change)
```

### G. ML prediction / anomaly flow

```
 STARTUP: simulated datasets (seed 7) ─► train RandomForest (fan) + IsolationForest ×4 ─► metrics (/ml/status)

 PREDICTION:  HomeState snapshot + recent events ─► fan_features (9) ─► impute missing (median)
              ─► RandomForest.predict_proba ─► probability ≥ 0.5 → ON
              ─► one-at-a-time sensitivity (median swap) ─► factors + explanation (+reliable flag)
              ─► /ml/predict · AI context/tools · Home card · 3D "AI NN%" badge
              ─► RECOMMENDATION ONLY (no command)

 ANOMALY:     device state ─► setting_level (0 | 10–100) + power_w (live or reported reading)
              ─► IsolationForest[device_type].decision_function − learned threshold
              ─► score < 0 ⇒ anomaly; normal range from binned percentiles
              ─► DeviceEvent(event_type=energy_anomaly, source=ml) ─► Energy page, 3D red ring, AI

 EXECUTION:   only explicit user request ─► AI plan ─► validation ─► CommandService ─► device
```

### H. 3D Digital Twin data flow

```
FastAPI GET /home/state ──(poll every 5 s, non-overlapping; refresh after each command)──►
   HomeDataProvider (useHomeDashboard) ─► devices, sensors, energy, events
        │
        ├─► AssistantProvider ─► useDisplayDevices() (during AI beams: previous_state → new_state from response)
        ▼
   SmartHomeScene (props only, no own state)
        ├─ Light3D  ← lightVisual(state)   glow level 0.12–1
        ├─ Fan3D    ← fanVisual(state)     2–24 rad/s, smoothed spin
        ├─ AC3D     ← acVisual(state)      airflow particles, set point label
        ├─ Door3D   ← doorVisual(state)    closed/green | ajar 0.6 rad/amber
        ├─ DeviceShell tags: OFFLINE/UNKNOWN, ⚠ Anomaly ring (Isolation Forest), AI % badge (RF ON)
        └─ AIOrb ← aiLifecycle reducer (idle/listening/thinking/planning/executing/success/error)
   CommandFxContext ← real API results only (beams, fizzles, pulses)
   No WebGL ─► FloorPlan2D (same live state)
```

## 64. Screenshots for the Final Report

All of these are **recommended screenshots**. None is claimed to exist. Capture them on a local run (backend `:8000`, frontend `:5173`) in Edge.

| # | Recommended screenshot | How to stage it |
|---|---|---|
| S1 | Main dashboard (Home) with the 3D twin, sensors, status checks and event stream | Open `#/`; turn on the light and fan first |
| S2 | 3D Command Center close-up: fan spinning, AC airflow, light glow | Fan speed 80, AC on at 18 °C, light on at 70 % |
| S3 | 3D door: locked (green) vs unlocked (ajar, amber) | Two captures |
| S4 | 2D floor-plan fallback (optional) | Only if WebGL is disabled |
| S5 | Gesture page: camera with landmark overlay, detection panel, per-finger scores | Show a thumbs-up |
| S6 | Stabilizer hold progress | Mid-hold of a gesture |
| S7 | Fan adjustment: Adjust panel "Fan Speed … (preview)" while pinching | Select the fan, pinch and move up |
| S8 | AC adjustment: "AC Temperature … cooler" | Select the AC, pinch and move up |
| S9 | Door double-pinch, step 1: Door unlock panel "🔐 Unlock Main Door? … Pinch again to confirm" with the countdown | Select the door, pinch once |
| S10 | Door double-pinch, step 2: "✓ Unlocked: confirmed by the door" + 3D door ajar | Pinch again |
| S11 | Door unlock cancelled by open palm ("Cancelled · the door stays locked") | Pinch once, then open palm |
| S12 | Gesture history table with outcomes (executed / rejected / awaiting_confirmation) | After several gestures |
| S13 | AI assistant chat: plan with per-action ✓/✗ and the outcome line | "Turn on the fan and set it to 70"; "Turn on the front door" (rejected) |
| S14 | AI door confirmation (text): "Are you sure…?" with Confirm/Cancel buttons and countdown | "Unlock the front door" |
| S15 | Voice panel: "Listening for 'Hey Nova'" and "Heard: …" | Enable voice |
| S16 | Voice command result (spoken reply text visible) | "Hey Nova, turn on the living room light" |
| S17 | AI request lifecycle pipeline + AI orb state | During a request |
| S18 | ML prediction card ("Random Forest … %", factors, "Recommendation only", "Ask AI why") | Home page |
| S19 | ML model card with metrics and the simulated-data note | Energy page |
| S20 | Anomaly detection: reading tester with 170 W for the fan → flagged; red ring in 3D | Energy page form |
| S21 | Activity stream with source labels and the "ML anomalies" filter | `#/activity` |
| S22 | Energy page: power chart and per-device bars | After a few minutes of polling |
| S23 | Swagger UI (`http://localhost:8000/docs`) listing all endpoints | |
| S24 | Error envelope example (e.g. THUMBS_UP on the door → 400 `intent_not_applicable`) | Swagger "Try it out" |
| S25 | `GET /api/v1/iot/status` with the Fake ESP32 (MQTT mode) | Four-terminal setup |
| S26 | Terminal: Fake ESP32 + backend logs showing command → ack | MQTT mode |
| S27 | Terminal: `pytest` summary (524 passed, 2 skipped) | `backend/` |
| S28 | Terminal: `npm test` summary (212 passed) and `npm run build` success | `frontend/` |
| S29 | GitHub repository page with tags (release history) | github.com/MUKULSHARMA2711/Smart_hand_gesture_Home |
| S30 | Deployment (only if a deployment actually exists) | **Do not include unless real** |
| S31 | Offline banner ("Connection to the backend lost") | Stop the backend briefly |
| S32 | Camera error message ("Camera permission was denied") | Deny permission |

---

## Module Cards (academic writing support)

Each card follows the structure Purpose · Input · Processing · Output · Technologies · Key implementation detail · Security/reliability · Actual result · Limitation.

### MC-1 Virtual IoT backend and device abstraction
- **Purpose:** simulate a home's devices behind a hardware-independent contract.
- **Input:** structured commands `{action, value}`.
- **Processing:** `DeviceSpec.parse_command` (strict Pydantic) → `VirtualDevice.apply` (pure transition) → power model.
- **Output:** previous/new state, `DeviceSnapshot` with capabilities and ranges.
- **Technologies:** Python 3.12, FastAPI, Pydantic v2.
- **Key detail:** each command declares exactly one capability; `supported_commands` publishes ranges to clients.
- **Security/reliability:** strict integers; unknown fields rejected; validation leaves state untouched on error.
- **Actual result:** 4 devices working; [TESTED-AUTO] (`test_domain`, `test_device_commands`, `test_capabilities`).
- **Limitation:** simulated physics and power; in-memory only.

### MC-2 CommandService and event log
- **Purpose:** the single, audited path for state changes.
- **Input:** `device_id`, command, `source`.
- **Processing:** per-device lock → energy sample → `execute_command` → `DeviceEvent`.
- **Output:** event with previous/new state and the true source.
- **Technologies:** asyncio, Pydantic.
- **Key detail:** the direct endpoint accepts only `source=frontend`; ML can never be a source of commands.
- **Security/reliability:** serialised per device; no event on failure.
- **Actual result:** used by every channel; [TESTED-AUTO] (`test_reliability`, `test_events_and_home_state`).
- **Limitation:** events in memory (max 1000).

### MC-3 Gesture recognition and stabilization
- **Purpose:** touch-free control through hand gestures.
- **Input:** webcam frames (in the browser only).
- **Processing:** MediaPipe landmarks → rule classifier (rotation-invariant finger scores, fuzzy AND, ambiguity penalty) → stabilizer (0.75, 600 ms, fire once) → `POST /gestures/commands` → backend re-checks.
- **Output:** one device command per deliberate gesture.
- **Technologies:** MediaPipe Tasks Vision (WASM/WebGL), React, FastAPI.
- **Key detail:** gestures map to device-agnostic intents, resolved by capability.
- **Security/reliability:** server-side threshold; door never reachable by power gestures; `unlock` blocked; camera released on every exit path.
- **Actual result:** five gestures work; [TESTED-AUTO] [TESTED-MANUAL] (Edge).
- **Limitation:** rule-based; lighting and distance sensitivity; one hand; explicit targeting.

### MC-4 Pinch adjustment (fan / AC)
- **Purpose:** continuous control of fan speed and AC temperature.
- **Input:** pinch start/move/end and vertical hand position.
- **Processing:** hysteresis pinch detector → `routePinch` → adjustment preview (clamped to published range, travel 0.5) → one `PINCH/ADJUST` on release → `IntentResolver` → `set_speed` / `set_temperature`.
- **Output:** one command; live preview panel.
- **Technologies:** JS modules, FastAPI.
- **Key detail:** nothing sent per frame; nothing if unchanged or the hand is lost.
- **Security/reliability:** ADJUST can never resolve to a lock; backend range validation; in-flight guard.
- **Actual result:** fan up = faster, AC up = cooler; [TESTED-AUTO] [TESTED-MANUAL].
- **Limitation:** pinch confidence is geometric (≥ 0.75 by construction); light brightness also adjustable in code but not part of the user-facing scope (Appendix C).

### MC-5 Secure double-pinch door unlock
- **Purpose:** allow a gesture unlock without letting any single gesture unlock the door.
- **Input:** two stable pinches with the Main Door selected.
- **Processing:** pinch 1 → `UNLOCK_DOOR` request → `hold_gesture_unlock` (validator + policy) → pending (30 s); pinch 2 → `POST /ai/confirmations/{id}` → re-validate → `CommandService(source=gesture)`.
- **Output:** door unlocked once, or cancelled/expired.
- **Technologies:** React controller, FastAPI, shared `ConfirmationStore`.
- **Key detail:** reuses the AI confirmation endpoint; there is no direct frontend unlock.
- **Security/reliability:** fail-closed on palm, other gesture, hand loss (1.5 s), camera stop, device change, page leave, expiry; duplicate pinches ignored; single-use confirmation.
- **Actual result:** [TESTED-AUTO] (56 targeted tests across 3 files) [TESTED-MANUAL] (Edge).
- **Limitation:** one pending slot; the direct dashboard unlock is not gated; no user authentication.

### MC-6 AI home agent
- **Purpose:** natural-language control and questions.
- **Input:** text (typed or voice).
- **Processing:** `HomeContext` → provider plan (Mock or Claude, read-only tools) → strict parse → `PlanValidator` → execute or hold.
- **Output:** `AgentResponse` with per-action status and a backend-generated outcome.
- **Technologies:** FastAPI, Pydantic, Anthropic SDK (optional).
- **Key detail:** validate all actions before executing any; the LLM has no write tools.
- **Security/reliability:** capability and policy checks; 120 s cap; 503 on outage; partial-plan accuracy.
- **Actual result:** mock provider fully tested; [TESTED-AUTO].
- **Limitation:** the mock is keyword-based; the live Claude provider is not verified in the repository.

### MC-7 Security policy and confirmation
- **Purpose:** protect security-sensitive door actions.
- **Input:** capability, source, the user's utterance, confirmation flag.
- **Processing:** explicit wording regex + clause-scoped negation check → allow / reject / requires_confirmation; reply classifier.
- **Output:** `PolicyDecision`; held confirmations.
- **Technologies:** Python regex.
- **Key detail:** checked in code, independent of the LLM.
- **Security/reliability:** a bare "yes" is insufficient; negation wins; 30 s expiry; executes once; re-validation.
- **Actual result:** [TESTED-AUTO] (`test_door_confirmation` 35, `test_ai_agent`).
- **Limitation:** rule-based; post-verb negation is not detected.

### MC-8 Voice assistant ("Hey Nova")
- **Purpose:** hands-free spoken control.
- **Input:** microphone audio, recognised by the browser.
- **Processing:** wake detection (normalised, split, interim) → command window 8 s → `/ai/command` → spoken summary of backend results.
- **Output:** device actions plus a spoken reply.
- **Technologies:** Web Speech API (SpeechRecognition, speechSynthesis), Web Audio.
- **Key detail:** no separate execution path; replies come from actual results.
- **Security/reliability:** mic paused while speaking; restart limits; full cleanup; unlock still needs "yes, unlock it".
- **Actual result:** [TESTED-AUTO] (47 tests) [TESTED-MANUAL] (Edge).
- **Limitation:** Chrome/Edge, online, en-US only.

### MC-9 Random Forest prediction
- **Purpose:** recommend fan use before it is needed.
- **Input:** 9 features from HomeState and events.
- **Processing:** median imputation → `predict_proba` → sensitivity-based explanation.
- **Output:** probability, ON/OFF, factors, explanation, `reliable`.
- **Technologies:** scikit-learn, numpy.
- **Key detail:** trained at startup, deterministic.
- **Security/reliability:** never executes; plausibility bounds; low-confidence flag when sensors are missing.
- **Actual result:** accuracy 0.8743 vs baseline 0.7125, F1 0.7671 [SIMULATED].
- **Limitation:** simulated data; one device; no real-world validation.

### MC-10 Isolation Forest anomaly detection
- **Purpose:** detect abnormal power draw.
- **Input:** (setting level, watts) per device.
- **Processing:** per-type IsolationForest, learned threshold, binned normal ranges.
- **Output:** `is_anomaly`, score, normal range, explanation; ML events.
- **Technologies:** scikit-learn.
- **Key detail:** threshold keeps 99.8 % of normal readings passing.
- **Security/reliability:** logs only, never acts; no false alarms on 168 sampled legitimate states.
- **Actual result:** F1 0.857–0.968 [SIMULATED].
- **Limitation:** simulated faults; virtual devices never produce real anomalies.

### MC-11 3D digital twin
- **Purpose:** an intuitive live view of the home.
- **Input:** backend snapshots and AI/gesture/dashboard results.
- **Processing:** pure visual mappings; animations smooth toward the backend value.
- **Output:** a 3D scene with devices, orb, beams and badges.
- **Technologies:** three.js, React Three Fiber, drei.
- **Key detail:** no own state.
- **Security/reliability:** shows only confirmed state; 2D fallback; reduced motion.
- **Actual result:** [TESTED-AUTO] (mappings) [TESTED-MANUAL].
- **Limitation:** 983 kB chunk; procedural (not photoreal) geometry.

### MC-12 MQTT / ESP32 layer
- **Purpose:** run devices on real hardware without changing business logic.
- **Input:** validated commands; MQTT messages.
- **Processing:** publish with `command_id` and expiry → wait for a matching, spec-valid, reflecting ack; availability via LWT; fresh-only sensors.
- **Output:** confirmed state or 502/503/504.
- **Technologies:** paho-mqtt, Mosquitto/amqtt, asyncio.
- **Key detail:** publishing is not success.
- **Security/reliability:** clean session, expiry, timeouts, credentials as secrets, localhost brokers.
- **Actual result:** end-to-end with the Fake ESP32 [TESTED-AUTO] [SIMULATED].
- **Limitation:** no physical hardware [PENDING]; firmware not in the repository.

### MC-13 Reliability layer
- **Purpose:** degrade gracefully.
- **Input:** failures of any subsystem.
- **Processing:** error envelope; isolation of AI, ML, sensors, camera and WebGL; timeouts; non-overlapping polling.
- **Output:** clear messages; the rest keeps working.
- **Technologies:** FastAPI exception handlers, React.
- **Key detail:** unexpected errors return a safe 500 with no internals.
- **Security/reliability:** no state mutation on failure.
- **Actual result:** [TESTED-AUTO] (35 + frontend tests).
- **Limitation:** no persistence or retry queue.

---

# Appendices

## Appendix A: Technology Stack and Versions

| Layer | Technology | Declared range | Installed locally (verified) |
|---|---|---|---|
| Backend language | Python | `>=3.12` | 3.12.4 |
| Web framework | FastAPI + uvicorn[standard] | `fastapi>=0.115,<1.0`, `uvicorn>=0.30` | FastAPI 0.142.2 |
| Validation / settings | Pydantic, pydantic-settings | `>=2.8,<3.0`, `>=2.4,<3.0` | Pydantic 2.13.5 |
| ML | scikit-learn (numpy) | `>=1.5,<2.0` | scikit-learn 1.9.1, numpy 2.5.3 |
| LLM SDK (optional) | anthropic | `>=1.11,<2.0` | (lazy import) |
| MQTT | paho-mqtt | `>=2.1,<3.0` | — |
| Dev/test | pytest, httpx, amqtt | `>=8.0`, `>=0.27`, `>=0.11` | — |
| Frontend runtime | Node.js | 20.19+ / 22.12+ (README) | 22.16.0 |
| UI | React, react-dom | `^19.3.0` | — |
| Build | Vite, @vitejs/plugin-react | `^8.3.2`, `^6.1.1` | — |
| Styling | Tailwind CSS (+ @tailwindcss/vite) | `^4.3.3` | — |
| Animation | motion | `^14.0.0` | — |
| 3D | three, @react-three/fiber, @react-three/drei | `^0.186.1`, `^9.8.1`, `^10.7.9` | — |
| Vision | @mediapipe/tasks-vision | `^1.0.1` | — |
| Tests | Vitest | `^5.0.3` | 5.0.3 |
| Broker (dev) | eclipse-mosquitto:2 (Docker) or amqtt | — | — |

## Appendix B: Files Inspected

**Documentation and configuration:** `README.md` (1,270 lines, read in full), `docs/README.md`, `ai/README.md`, `ml/README.md`, `simulation/README.md`, `vision/README.md`, `.gitignore`, `backend/.env.example`, `frontend/.env.example`, `backend/pyproject.toml`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `frontend/package.json`, `frontend/vite.config.js`, `frontend/index.html`, `backend/simulation/mosquitto/{docker-compose.yml,mosquitto.conf}`, `backend/simulation/amqtt.yaml`.

**Backend source (read in full unless noted):** `app/main.py`, `app/config.py`, `app/container.py`; `app/domain/{command_service,intents,policy,home_state,energy,errors}.py`; `app/devices/{types,commands,base,power,factory}.py`, `app/devices/specs/{base,fan,ac,door,light}.py`, `app/devices/virtual/{base,fan,ac,door}.py`; `app/devices/esp32.py` (header, structure and error paths); `app/ai/{agent,confirmation,validation,models,tools,context,errors}.py`, `app/ai/prompts.py` (system prompt), `app/ai/providers/base.py`, `providers/anthropic_provider.py` (structure), `providers/mock.py` (header and structure); `app/gestures/{models,service,errors,history}.py`; `app/api/errors.py`, `app/api/schemas.py`, `app/api/v1/{router,devices,gestures,ai,ml,iot,home,events}.py`; `app/events/models.py`; `app/ml/{features,dataset,prediction,anomaly}.py`, `app/ml/service.py`, `app/ml/models.py` (data note); `app/sensors/{base,simulated}.py`; `app/mqtt/topics.py`, `app/mqtt/{client,manager,memory}.py` (structure); `simulation/mqtt_esp32.py` (header).

**Frontend source:** `App.jsx`, `api/client.js`, `gestures/{types,stabilizer,pinch,ruleClassifier,adjustment,doorUnlock,pinchRouting}.js`, `gestures/{cameraSession,mediapipeRecognizer}.js` (headers/config), `hooks/{useGestureControl,useGestureRecognition,useVoiceAssistant}.js`, `pages/GesturePage.jsx`, `components/gestures/{AdjustmentPanel,DoorUnlockPanel}.jsx`, `components/assistant/VoicePanel.jsx`, `voice/voiceSession.js`, `lib/assistant.js`, `lib/ml.js` (prediction badge), `components/3d/visualState.js`, `components/3d/DeviceShell.jsx` (tags), `state/{polling,homeHealth}.js`, `hooks/useHomeDashboard.js` (poll interval).

**Tests:** all backend and frontend test files (names, counts and scope); `tests/test_ml_models.py` (`VIRTUAL_STATES` = 168), `tests/test_ml_integration.py`, `tests/test_gesture_unlock.py`, `tests/test_anthropic_provider.py`; `pinchRouting.test.js` and `doorUnlock.test.jsx` in full.

**Git:** full log (17 commits with stats), messages of commits `d0ab10b`, `a54ea80`, `4440864`, `49ca328`, `b6c8d66`, `7c97737`, `fd000cb`, `b9cbff0`; all tags and their targets; local vs remote tag and branch equality.

**Executed for verification:** full backend suite, full frontend suite (JSON reporter for per-file counts), production build, ML retraining with default settings (metrics printout).

## Appendix C: Ambiguities and Stale Documentation

1. **README sections that predate the latest features.** The code is authoritative.
   - `README.md` §"Prepared: pinch-to-adjust (not active yet)" (≈ lines 400–422): pinch adjustment **is active** since `8595c34`.
   - §"Safety: no gesture maps to a door intent" (≈ line 374) and "Gestures still cannot unlock" (≈ line 611): **outdated**. A pinch may *request* a confirmation-gated unlock since `fd000cb`/`b9cbff0`. Direct gesture unlock remains blocked.
   - §"Out of scope so far" lists **"Voice control"**, but voice is implemented (`a54ea80`).
   - Day 4 "Anomaly detection is labelled 'Not available yet'": now this label only shows when ML results are absent.
   - The README has no section on the double-pinch door workflow.
2. **Stale code comments** (no behaviour impact):
   - `backend/app/domain/intents.py`: ADJUST "no gesture maps to it yet".
   - `backend/app/config.py`: "No gesture maps to a door intent".
   - `api/schemas.py`: `value` "future pinch adjustment".
3. **Light brightness via pinch.** The frontend `ADJUSTABLE` includes `set_brightness` and the backend resolves ADJUST to `SET_BRIGHTNESS` for the light. Backend-tested (`test_adjustment_prep.py`); no frontend test; not part of the user's verified feature list. The UI text says "Select the fan or the AC". Describe the light as *technically adjustable* or omit it, but do not present it as a verified feature.
4. **Version strings:** package files and the FastAPI app report `0.1.0`, while release tags reach `v0.10.0`.
5. **Naming:** repository `Smart_hand_gesture_Home` vs product `IntelliHome` vs folder `smart-ai-home`. The wake word "Nova" is not the product name.
6. **Phase naming in the README is mixed** (Day 1–4, Phase 5, Day 6, Phase 7). Later work (v0.8–v0.10) has no day or phase label.
7. **Tag `v0.8.0-voice-secure-unlock`** points at the ADJUST-prep chore commit (`4440864`), so it also contains the adjustment interfaces.
8. **Pinch confidence semantics:** it is a geometric margin mapped to 0.75–1.0, so a detected pinch always meets the 0.75 threshold. It is not a classifier probability.
9. **CORS credentials:** not enabled (no `allow_credentials`). Earlier working notes mentioned "preserve credentials"; the code has none, and none are needed because there is no auth.
10. **Gesture/AI shared confirmation slot:** typing "yes, unlock it" on the assistant page could confirm a pending **gesture** unlock, because the store is shared. This follows from the code; no test is specifically about this cross-channel case.

## Appendix D: Information That Could Not Be Verified

| Item | Status |
|---|---|
| Any public deployment (e.g. Vercel), its URL, commit and backend host | Not established from repository |
| Live behaviour of the real Claude provider (API key, latency, plan quality) | Not established from repository (unit-tested with a fake client only) |
| Real-broker test runs (`test_mqtt_broker.py`) | Skipped in the verified run; whether they were ever run is not established |
| Physical ESP32, relays, DHT22/PIR/LDR sensors, power meter | **[PENDING]**: never tested |
| Real-world ML accuracy | Not established; only simulated metrics exist |
| Chrome / Firefox / Safari behaviour | Not established (Edge is the verified browser) |
| Gesture recognition accuracy on real webcams (quantitative) | Not established. Only qualitative user-reported success; the README's 96–98 % is from sample photos via a fake webcam (scripts not committed). |
| Latency / performance measurements (FPS, response times) | Not established from repository |
| User study / usability evaluation | Not established (none in repository) |
| Exact MediaPipe model download size | README states ~7.8 MB; not re-measured |
| Hardware cost / bill of materials | Not established from repository |

## Appendix E: Glossary

| Term | Meaning in IntelliHome |
|---|---|
| Intent | Device-agnostic goal (e.g. `TURN_ON`) emitted by gestures or the AI |
| Capability | Explicit thing a device can do (e.g. `SET_SPEED`); each command declares exactly one |
| DeviceSpec | Hardware-independent contract: state shape + commands + value limits |
| CommandService | The single, serialised, audited execution path |
| Stabilizer | Hold-and-release filter turning noisy frames into deliberate gestures |
| Pinch | Thumb tip touching index tip with the other fingers open; used for adjustment and door confirmation |
| Pending confirmation | A held door unlock (single slot, 30 s expiry) awaiting confirm or cancel |
| HomeState | In-memory aggregate of devices, sensors and energy; the source of truth for the UI, AI and ML |
| Fake ESP32 | Software stand-in for ESP32 firmware speaking the real MQTT contract |
| LWT (Last Will and Testament) | MQTT message the broker publishes if a client disconnects uncleanly; used for availability |
| Mock provider | Deterministic rule-based AI planner, the default; used by all tests |
| Digital twin | 3D (or 2D fallback) visualisation rendering only backend-confirmed state |
