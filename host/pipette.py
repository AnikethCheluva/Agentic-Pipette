#!/usr/bin/env python3
"""Agent CLI and Python API for Nano pipette serial protocol v1."""
import argparse
import json
import sys
import time
from pathlib import Path


def emit(event):
    print(json.dumps(event), flush=True)


def integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer {low}..{high}')
    return value


def validate_step(step):
    if not isinstance(step, dict):
        raise ValueError('Each step must be an object')
    op = step.get('op')
    allowed = {'servo': {'op', 'angle', 'settle_ms'},
               'servo_us': {'op', 'pulse_us', 'hold_ms'},
               'actuator': {'op', 'direction', 'duration_ms'},
               'wait': {'op', 'duration_ms'}, 'status': {'op'}, 'stop': {'op'}}
    if op not in allowed or set(step) - allowed[op]:
        raise ValueError(f'Unknown operation or fields: {step}')
    if op == 'servo':
        angle = integer(step.get('angle'), 0, 180, 'angle')
        ms = integer(step.get('settle_ms', 500), 1, 10000, 'settle_ms')
        return f'servo {angle} {ms}', ms
    if op == 'servo_us':
        pulse = integer(step.get('pulse_us'), 610, 2000, 'pulse_us')
        ms = integer(step.get('hold_ms', 500), 1, 5000, 'hold_ms')
        return f'servo_us {pulse} {ms}', ms
    if op == 'actuator':
        direction = step.get('direction')
        if direction not in ('forward', 'reverse'):
            raise ValueError('direction must be forward or reverse')
        ms = integer(step.get('duration_ms'), 1, 10000, 'duration_ms')
        return f'actuator {direction} {ms}', ms
    if op == 'wait':
        ms = integer(step.get('duration_ms'), 1, 60000, 'duration_ms')
        return f'wait {ms}', ms
    return op, 0


def validate_sequence(data):
    if not isinstance(data, dict) or set(data) != {'steps'}:
        raise ValueError('Sequence must be an object containing only steps')
    steps = data['steps']
    if not isinstance(steps, list) or not 1 <= len(steps) <= 100:
        raise ValueError('Provide 1..100 steps')
    validated = [validate_step(step) for step in steps]
    if sum(ms for _, ms in validated) > 600000:
        raise ValueError('Sequence exceeds 10 minute limit')
    return validated


class Pipette:
    """One exclusive serial owner; no automatic retries of motion commands."""
    def __init__(self, port, on_event=emit):
        import serial
        self.serial = serial.Serial(port, 115200, timeout=0.05,
                                    write_timeout=1, exclusive=True)
        self.on_event = on_event
        self.next_id = 1
        self.buffer = bytearray()
        try:
            # Opening the Nano port normally resets it. Never send motion before handshake.
            time.sleep(2)
            self.serial.reset_input_buffer()
            result = self.execute('status', 0)
            if result.get('protocol') != 1:
                raise RuntimeError('Upload protocol v1 firmware before using this client')
            if result.get('busy'):
                raise RuntimeError('Device is busy')
        except BaseException:
            self.serial.close()
            raise

    def send(self, command):
        ident = self.next_id
        self.next_id += 1
        self.serial.write(f'@{ident} {command}\n'.encode('ascii'))
        return ident

    def read(self):
        chunk = self.serial.read(self.serial.in_waiting or 1)
        self.buffer.extend(chunk)
        if len(self.buffer) > 8192:
            raise RuntimeError('Serial response buffer overflow')
        while b'\n' in self.buffer:
            raw, _, rest = self.buffer.partition(b'\n')
            self.buffer = bytearray(rest)
            if raw.strip():
                try:
                    event = json.loads(raw)
                except (ValueError, UnicodeError) as exc:
                    raise RuntimeError('Invalid serial response; check firmware/baud') from exc
                if not isinstance(event, dict):
                    raise RuntimeError('Invalid serial event')
                yield event

    def execute(self, command, duration_ms):
        ident = self.send(command)
        deadline = time.monotonic() + duration_ms / 1000 + 3
        heartbeat = time.monotonic() + .4
        while time.monotonic() < deadline:
            if time.monotonic() >= heartbeat:
                self.send('ping')
                heartbeat = time.monotonic() + .4
            for event in self.read():
                if event.get('event') != 'pong':
                    self.on_event(event)
                if event.get('event') == 'ready':
                    raise RuntimeError('Nano reset during command; sequence aborted')
                if event.get('id') != ident:
                    continue
                kind = event.get('event')
                if kind == 'error':
                    raise RuntimeError(event.get('detail', 'Device error'))
                if kind in ('done', 'status'):
                    return event
        raise TimeoutError('No completion response; motion is not retried')

    def run(self, data):
        validated = validate_sequence(data)
        for index, (command, ms) in enumerate(validated):
            self.on_event({'event': 'step_start', 'index': index, 'command': command})
            self.execute(command, ms)
        self.on_event({'event': 'sequence_done', 'steps': len(validated)})

    def close(self):
        if self.serial.is_open:
            try:
                self.execute('stop', 0)
            finally:
                self.serial.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def load(path):
    return json.load(sys.stdin) if path == '-' else json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='/dev/cu.usbserial-2130')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('ports')
    sub.add_parser('status')
    sub.add_parser('stop')
    for name in ('run', 'validate'):
        p = sub.add_parser(name)
        p.add_argument('file', help='JSON sequence file, or - for stdin')
    p = sub.add_parser('command')
    p.add_argument('json', help='Single JSON step')
    args = parser.parse_args()
    try:
        if args.action == 'ports':
            from serial.tools import list_ports
            emit({'ports': [{'device': p.device, 'description': p.description}
                            for p in list_ports.comports()]})
            return 0
        data = None
        if args.action in ('run', 'validate'):
            data = load(args.file)
            validate_sequence(data)
        elif args.action == 'command':
            data = {'steps': [json.loads(args.json)]}
            validate_sequence(data)
        if args.action == 'validate':
            emit({'event': 'valid', 'steps': len(data['steps'])})
            return 0
        with Pipette(args.port) as device:
            if data is not None:
                device.run(data)
            elif args.action == 'stop':
                device.execute('stop', 0)
            # Constructor already emitted status for the status command.
        return 0
    except KeyboardInterrupt:
        emit({'event': 'error', 'detail': 'interrupted'})
        return 130
    except Exception as exc:
        emit({'event': 'error', 'detail': str(exc)})
        return 1


if __name__ == '__main__':
    sys.exit(main())
