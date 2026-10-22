# Arduino IDE setup

1. Open `AgenticPipette/AgenticPipette.ino`.
2. Install **Arduino AVR Boards** and **Servo by Arduino (1.2.2)**.
3. Select **Arduino Nano**, processor **ATmega328P** (newer bootloader).
4. Select the connected Nano's USB serial port and upload.
5. Serial Monitor: **115200 baud**, **New Line**.

Manual commands: `90` sets absolute 90°, `actuator` runs forward for 5 seconds,
`reverse` runs reverse for 5 seconds, and `stop` disables outputs. Explicit timed
commands include `actuator forward 400` and `servo 90 500`.
Relative signed-angle commands are not supported. Experimental direct pulse
command: `servo_us 611 500` (microseconds, hold milliseconds).

Close Serial Monitor before using the host agent runner. See
[interface documentation](../docs/agent-interface.md).
The active sketch is self-contained; legacy Config.h/MotorDriver.h files are not used.
