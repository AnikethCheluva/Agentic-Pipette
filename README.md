# Agentic-Pipette

Arduino Nano firmware and a Python serial interface for sequencing a pipette's
MG995 servo and L298N-driven DC linear actuator. Agents submit JSON sequences;
the host validates them, sends one motion at a time, and emits JSON status events.

## Hardware

- Classic Arduino Nano (ATmega328P, newer bootloader)
- MG995 servo: signal D9, external regulated 5–6 V power
- L298N: ENA D5, IN1 D4, IN2 D8; actuator on OUT1/OUT2
- 12 V actuator supply; all grounds connected
- L298N ENA and 5V-EN jumpers removed; Nano 5V supplies driver logic only

See [wiring](docs/hardware.md). Do not power the servo from the Nano or L298N 5V.
No position or current sensor is installed. Completion events report elapsed
command time, not measured movement or endpoint detection.

## Install and upload

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r host/requirements.txt
```

Install PlatformIO separately, then run:

```sh
pio run -e nano_new_bootloader
pio run -e nano_new_bootloader -t upload --upload-port /dev/cu.usbserial-2130
```

Alternatively follow [Arduino IDE setup](ArduinoIDE/README.md).
Use your actual serial port (`python host/pipette.py ports`). Close Arduino IDE's
Serial Monitor before using the Python client. Serial runs at 115200 baud.

## Agent commands

```sh
python host/pipette.py status
python host/pipette.py validate examples/sequence.json
python host/pipette.py run examples/sequence.json
python host/pipette.py command '{"op":"servo","angle":90,"settle_ms":500}'
python host/pipette.py command '{"op":"actuator","direction":"forward","duration_ms":400}'
```

The example moves real hardware. Inspect angles and durations for your mechanism
before running it. Override the default port using `--port PORT` before the subcommand.

An agent can pipe a sequence into `python host/pipette.py run -`:

```json
{
  "steps": [
    {"op": "servo", "angle": 90, "settle_ms": 500},
    {"op": "actuator", "direction": "forward", "duration_ms": 400},
    {"op": "wait", "duration_ms": 300},
    {"op": "actuator", "direction": "reverse", "duration_ms": 400},
    {"op": "stop"}
  ]
}
```

| Operation | Fields | Bounds |
|---|---|---|
| `servo` | `angle`, optional `settle_ms` | Absolute 0–180°, 1–10000 ms; default 500 ms |
| `servo_us` | `pulse_us`, optional `hold_ms` | Experimental 610–2000 µs, 1–5000 ms; default 500 ms |
| `actuator` | `direction`, `duration_ms` | forward/reverse, 1–10000 ms |
| `wait` | `duration_ms` | 1–60000 ms |
| `status` / `stop` | none | Read commanded state / disable outputs |

Direct pulse trials use `servo_us`, for example:

```sh
python host/pipette.py command '{"op":"servo_us","pulse_us":611,"hold_ms":5000}'
```

611 µs was tried as an extrapolated −70° relative to the original 1000 µs zero;
this is not a measured angle or a manufacturer-approved travel limit. See
[calibration notes](docs/calibration.md).

## Execution behavior

- Ordered steps, absolute servo angles, unique command IDs, JSON Lines responses.
- Full sequence validation before connection; no automatic motion retries.
- Heartbeat during actions; active tagged commands cancel after about 2 seconds
  without heartbeat. Every motion has a duration limit.
- Ctrl+C, normal completion, and handled errors trigger stop and close the port.
- Stop disables the actuator and detaches servo pulses; it does not cut power.
- The servo holds during subsequent sequence steps until stopped. Separate CLI
  calls detach after each command and normally reset the Nano when opening USB.
- Timed forward/reverse pulses do not guarantee equal travel. Internal actuator
  limit switches are not observable with current wiring.

Read the [full serial protocol and Python API](docs/agent-interface.md).

## Layout

- `ArduinoIDE/AgenticPipette/AgenticPipette.ino`: active firmware for both build paths
- `host/pipette.py`: CLI, JSON validation, sequence runner, Python API
- `examples/sequence.json`: illustrative motion sequence
- `platformio.ini`: Nano build/upload settings
- `docs/`: wiring, protocol, and calibration notes

Firmware has been compiled and uploaded on the connected Nano. Serial handshake,
heartbeat and wait completion were verified; physical motion trials were performed
interactively. Position accuracy and full travel limits have not been measured.
