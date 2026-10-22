# Calibration and observed trials

## Servo

Normal commands map nominal absolute 0–180° to 1000–2000 µs. These are commanded
positions, not measured angles. Horn orientation determines the physical reference.

| Requested extrapolation from original zero | Pulse tried |
|---|---|
| −40° | 778 µs |
| −50° | 722 µs |
| −70° | 611 µs |

The user confirmed movement at 778 µs. Later pulses were commanded, including a
5-second 611 µs hold; no angle measurement was available. Do not treat this table
as verified geometry or mechanical travel limits. Raw pulse commands accept
610–2000 µs with a maximum 5-second hold. They report commanded_angle=-1 because
an absolute angle is not calibrated. Current firmware retains no position across reset.

## Actuator

Trials used forward pulses of 0.4–1 second and reverse pulses including 5 seconds
toward the retract stop. No stroke length, travel speed, or endpoint time has been
measured. Five seconds is a command duration, not proof of full retraction.
The actuator reportedly switches itself off at its endpoints, but the Arduino cannot
observe this through the existing two motor wires and L298N control interface.

Timed displacement can vary with load, supply voltage, direction, and startup.
Position sensing is required for repeatable measured travel. Current sensing may
help detect endpoint cutoff, but also requires distinguishing disconnected wires
and other causes of low current; no such sensor or firmware is currently installed.
