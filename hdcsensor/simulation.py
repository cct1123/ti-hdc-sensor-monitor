"""Opt-in software device. Exercises the actual HDC command/CRC driver; no HID import."""

import math
import time

from .errors import SensorError
from .protocol import MODE_COMMANDS, MODE_PERIODS, Command, decode_word, encode_word


class SimulatedTransport:
    name = "SIMULATED HDC3020 (no hardware)"
    serial_number = "SIMULATION"
    firmware_version = "simulation-1"
    address = 0x44

    def __init__(self):
        self.opened = False
        self.status = 0x8010
        self.mode = "on_demand"
        self.pending = None
        self.heater_config = 0
        self._next_auto = 0.0

    def open(self):
        if self.opened:
            raise SensorError("Simulation already open")
        self.opened = True

    def write(self, data):
        if not self.opened:
            raise SensorError("Simulation is closed")
        self.pending = int.from_bytes(data[:2], "big")
        command = self.pending
        if command == Command.HEATER_ON:
            self.status |= 0x2000
        elif command == Command.HEATER_OFF:
            self.status &= ~0x2000
        elif command == Command.HEATER_CONFIG and len(data) == 5:
            self.heater_config = decode_word(data[2:])
        elif command == Command.RESET:
            self.status, self.mode = 0x8010, "on_demand"
        elif command == Command.CLEAR_STATUS:
            self.status &= 0x2001
        elif command == Command.EXIT_AUTO:
            self.mode = "on_demand"
        else:
            for mode, commands in MODE_COMMANDS.items():
                if command in commands:
                    self.mode = mode
                    self._next_auto = time.monotonic() + MODE_PERIODS[mode]

    def read(self, count):
        if not self.opened:
            raise SensorError("Simulation is closed")
        words = {
            Command.MANUFACTURER: 0x3000,
            Command.NIST_HIGH: 0x0123,
            Command.NIST_MIDDLE: 0x4567,
            Command.NIST_LOW: 0x89AB,
            Command.STATUS: self.status,
            Command.HEATER_CONFIG: self.heater_config,
        }
        if self.pending in words:
            result = encode_word(words[self.pending])
        elif self.pending == Command.FETCH or self.pending in MODE_COMMANDS["on_demand"]:
            now = time.monotonic()
            if self.pending == Command.FETCH and now < self._next_auto:
                return b"\xff" * 6
            period = MODE_PERIODS[self.mode]
            if period:
                # The real sensor converts on its own clock; a late host read
                # consumes the latch without shifting the conversion schedule.
                self._next_auto += (int((now - self._next_auto) // period) + 1) * period
            t = 23.5 + 0.35 * math.sin(now / 24) + (1.2 if self.status & 0x2000 else 0)
            rh = 46 + 1.5 * math.cos(now / 31)
            result = encode_word(round((t + 45) * 65535 / 175)) + encode_word(round(rh * 65535 / 100))
        else:
            raise SensorError(f"Unsupported simulated command 0x{self.pending:04X}")
        if len(result) != count:
            raise SensorError("Simulation read length mismatch")
        return result

    def close(self):
        self.opened = False
