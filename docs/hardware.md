# Wiring

Disconnect power before changing connections.

| Device pin | Connect to |
|---|---|
| L298N ENA | Nano D5; ENA jumper removed |
| L298N IN1 | Nano D4 |
| L298N IN2 | Nano D8 |
| L298N 5V | Nano 5V; 5V-EN regulator jumper removed |
| L298N GND | Nano GND and supply negative |
| L298N VS / 12V | Actuator's 12 V supply positive |
| L298N OUT1 / OUT2 | Two actuator motor wires |
| Servo signal (orange/yellow) | Nano D9 |
| Servo positive (red) | External regulated 5–6 V |
| Servo ground (brown/black) | Servo supply negative AND Nano GND |

Nano is USB-powered. Servo supply should support its startup/stall load (about 3 A
capacity is a practical starting point for this MG995 setup). Never apply 12 V to
the servo or Nano 5V. Do not use Nano/L298N logic 5V to power the servo.
A shared 12 V source requires an appropriately rated buck converter for the servo
and enough combined current capacity. The actuator has been operated from a
12 V, 2 A source; that does not establish adequacy for both motors simultaneously.
The L298N loses voltage and dissipates heat under load.

Forward/reverse polarity depends on motor wiring. The second L298N channel is
unused. No current sensor, encoder, or position feedback is connected.
