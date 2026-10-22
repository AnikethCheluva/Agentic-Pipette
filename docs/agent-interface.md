# Agent serial interface

Controls the existing Nano, MG995 servo and L298N actuator. No current sensor,
position sensor, homing, or endpoint detection is installed. All actuator moves
are timed; a completion event means the command timer elapsed, not that measured
travel or position was achieved. Servo angles are absolute commanded angles using
the existing 1000–2000 microsecond calibration; settling is a delay, not feedback.

## Setup

Wiring: servo signal D9; L298N ENA D5, IN1 D4, IN2 D8; actuator OUT1/OUT2.
Remove ENA and 5V-EN jumpers. Nano 5V supplies L298N logic, not servo power.
Keep shared ground and the external motor/servo supplies already configured.

Upload `ArduinoIDE/AgenticPipette/AgenticPipette.ino` using Arduino IDE or:

```sh
pio run -e nano_new_bootloader -t upload --upload-port /dev/cu.usbserial-2130
```

Install the host dependency:

```sh
python3 -m pip install -r host/requirements.txt
```

The existing PlatformIO Python also has pyserial:
`~/.platformio/penv/bin/python`.
Close Arduino IDE Serial Monitor before running the client. Port names can change;
`python3 host/pipette.py ports` lists them. Opening the port normally resets a Nano;
keep one connection open for a whole sequence. Only one process may own the port.

## Agent usage

Run from the project root. All CLI output is JSON Lines on stdout; errors return a
nonzero exit code. Validation happens for the entire sequence before connecting.
Validation never moves hardware. The sample includes motion and is not calibration.

```sh
python3 host/pipette.py validate examples/sequence.json
python3 host/pipette.py --port /dev/cu.usbserial-2130 status
python3 host/pipette.py --port /dev/cu.usbserial-2130 run examples/sequence.json
python3 host/pipette.py command '{"op":"servo","angle":90,"settle_ms":500}'
python3 host/pipette.py command '{"op":"actuator","direction":"reverse","duration_ms":200}'
```

An agent can pipe a JSON object into `python3 host/pipette.py run -`.
Use one sequence for related motions, not a new process per step.

```json
{"steps":[
  {"op":"servo","angle":90,"settle_ms":500},
  {"op":"actuator","direction":"forward","duration_ms":200},
  {"op":"wait","duration_ms":500},
  {"op":"actuator","direction":"reverse","duration_ms":200},
  {"op":"stop"}
]}
```

Steps execute sequentially; the servo holds its commanded angle during later
steps until `stop` or disconnect cleanup. Forward/reverse are electrical directions;
confirm which retracts on your wiring. Equal forward/reverse durations do not
ensure equal travel. Servo range is 0–180; choose angles compatible with your linkage.
Actuator duration is 1–10000 ms; servo settling 1–10000 ms (default 500);
wait 1–60000 ms. Sequences allow 1–100 steps, up to 10 minutes of requested duration.
Very short pulses have serial-processing/timer overhead and are not precise metering.

The runner sends `stop` on successful completion, errors, or Ctrl+C and closes the
port. This disables the actuator and detaches servo pulses. A separate `stop` CLI
cannot take over an already-owned port; interrupt the owning process with Ctrl+C.
If the process crashes or loses USB mid-motion, firmware cancels a tagged action
within approximately 2 seconds without heartbeat, or at its duration limit sooner.
A servo holding after an already-completed step has no independent link timeout;
normal client cleanup detaches it. Removal of pulses is not a physical power cutoff.

Python API (import with project root on the Python path):

```python
from host.pipette import Pipette
with Pipette('/dev/cu.usbserial-2130') as device:
    device.run({'steps': [
        {'op': 'servo', 'angle': 90, 'settle_ms': 500},
        {'op': 'actuator', 'direction': 'forward', 'duration_ms': 200},
    ]})
```

## Direct serial protocol v1

115200 baud, newline terminated ASCII commands, maximum 95 characters.
Use a positive unique 32-bit ID per command within a session:

```text
@1 status
@2 servo 90 500
@3 actuator forward 200
@4 wait 250
@5 ping
@6 stop
```

Responses are newline-delimited JSON:

```json
{"id":3,"event":"ack","detail":"started"}
{"id":3,"event":"done","detail":"timer_elapsed_not_position_verified"}
```

Send `ping` at least every 500 ms while an action runs. The included client does
this automatically every 400 ms. `status`, `ping`, and `stop` work while busy;
other motions are rejected with `busy`. `stop` emits an error `stopped` for the
cancelled action, then `done` for the stop ID. Reset emits `ready` with ID 0; a
reset during a client command aborts its sequence. There is no motion queue on the
Nano and no replay/deduplication cache: never retry an uncertain motion automatically.
Errors include invalid_id, invalid_arguments, invalid_command, line_too_long,
busy, heartbeat_timeout, and stopped. Unknown/invalid input never starts motion.

For manual Serial Monitor use, plain `90` commands absolute servo position;
`actuator`/`forward` and `reverse` run 5 seconds, and `stop` cancels immediately.
Explicit `servo 90 500` / `actuator forward 200` also work without an ID. Manual
commands have duration limits but no heartbeat requirement. Relative angle
shortcuts were removed in this interface; all servo angles are absolute.

## Experimental servo pulse command

Direct serial `@ID servo_us PULSE_US HOLD_MS` accepts 610–2000 us for 1–5000 ms. Use the Python API `execute("servo_us 778 500", 500)` inside a Pipette context so cleanup detaches pulses. Raw pulses are not calibrated angles; status reports commanded_angle=-1. The normal servo angle mapping remains 0–180 to 1000–2000 us. Expanded pulse travel has not been mechanically verified.

The JSON runner also supports `{"op":"servo_us","pulse_us":611,"hold_ms":5000}`. Hold defaults to 500 ms; bounds match firmware. This is an experimental pulse command, not a calibrated negative angle.
