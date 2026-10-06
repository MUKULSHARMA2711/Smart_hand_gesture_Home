"""Failure scenarios for the Fake ESP32, and how to switch them at runtime.

Scenarios are switched with a JSON message on ``simulation/{board_id}/scenario``. That
namespace belongs to the simulator only; it is not part of the firmware contract.

    python -m simulation.scenarios fan_living_room no_ack
    python -m simulation.scenarios fan_living_room delay --delay 2
    python -m simulation.scenarios sensors stale
"""

import argparse
import json
import os
from dataclasses import dataclass
from enum import StrEnum

CONTROL_ROOT = "simulation"


class Scenario(StrEnum):
    NORMAL = "normal"  # command → immediate acknowledgement
    DELAY = "delay"  # command → acknowledgement after delay_s
    NO_ACK = "no_ack"  # command → no response (firmware hung)
    OFFLINE = "offline"  # publishes availability=offline and ignores commands
    WRONG_COMMAND_ID = "wrong_command_id"  # executes, acknowledges with another command_id
    WRONG_STATE = "wrong_state"  # acknowledges with an impossible state
    MALFORMED_ACK = "malformed_ack"  # acknowledges with invalid JSON
    DUPLICATE_ACK = "duplicate_ack"  # acknowledges the same command three times
    RECONNECT = "reconnect"  # goes offline, reconnects after reconnect_after_s, then NORMAL


class SensorScenario(StrEnum):
    NORMAL = "normal"  # realistic readings every interval
    STALE = "stale"  # stops publishing (readings age out)
    INVALID = "invalid"  # publishes an impossible temperature
    OFFLINE = "offline"  # publishes availability=offline


@dataclass(frozen=True)
class ScenarioRequest:
    scenario: str
    delay_s: float | None = None
    reconnect_after_s: float | None = None

    def encode(self) -> bytes:
        return json.dumps({k: v for k, v in self.__dict__.items() if v is not None}).encode()

    @classmethod
    def decode(cls, payload: bytes) -> "ScenarioRequest":
        data = json.loads(payload)
        return cls(
            scenario=str(data["scenario"]),
            delay_s=float(data["delay_s"]) if data.get("delay_s") is not None else None,
            reconnect_after_s=float(data["reconnect_after_s"]) if data.get("reconnect_after_s") is not None else None,
        )


def control_topic(board_id: str) -> str:
    return f"{CONTROL_ROOT}/{board_id}/scenario"


def main() -> None:
    parser = argparse.ArgumentParser(description="Switch a running Fake ESP32 board to a scenario.")
    parser.add_argument("board", help="device id (e.g. fan_living_room) or 'sensors'")
    parser.add_argument("scenario", help=f"device: {', '.join(Scenario)}; sensors: {', '.join(SensorScenario)}")
    parser.add_argument("--delay", type=float, help="acknowledgement delay for 'delay' (seconds)")
    parser.add_argument("--reconnect-after", type=float, help="offline time for 'reconnect' (seconds)")
    parser.add_argument("--host", default=os.environ.get("SMARTHOME_MQTT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("SMARTHOME_MQTT_PORT", "1883")))
    args = parser.parse_args()

    import paho.mqtt.publish as publish

    auth = None
    if os.environ.get("SMARTHOME_MQTT_USERNAME"):
        auth = {"username": os.environ["SMARTHOME_MQTT_USERNAME"], "password": os.environ.get("SMARTHOME_MQTT_PASSWORD")}
    request = ScenarioRequest(args.scenario, args.delay, args.reconnect_after)
    publish.single(control_topic(args.board), request.encode(), qos=1, hostname=args.host, port=args.port, auth=auth)
    print(f"{args.board} -> {args.scenario}")


if __name__ == "__main__":
    main()
