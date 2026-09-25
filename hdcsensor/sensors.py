"""HDC3020 sensor driver; only DeviceSession may call its I/O methods."""

from __future__ import annotations

import time

from .errors import SensorError
from .models import DeviceIdentity
from .protocol import (
    CONVERSION_SECONDS,
    MODE_COMMANDS,
    Command,
    decode_measurement,
    decode_word,
    encode_word,
    validate_settings,
)


class HDC3020Sensor:
    def __init__(self, transport, sleep=time.sleep):
        self.transport = transport
        self._sleep = sleep
        self.mode = "on_demand"
        self.low_power = 0
        self.status_word = 0
        self.identity = None
        self._initialized = False

    @property
    def name(self):
        return self.transport.name

    def command(self, command: int, data: bytes = b""):
        self.transport.write(int(command).to_bytes(2, "big") + data)

    def read_word(self, command: int) -> int:
        self.command(command)
        return decode_word(self.transport.read(3), f"Command 0x{command:04X}")

    def read_identity(self):
        manufacturer = self.read_word(Command.MANUFACTURER)
        if manufacturer != 0x3000:
            raise SensorError(f"Unexpected manufacturer ID 0x{manufacturer:04X}; expected TI 0x3000")
        nist = "".join(
            f"{self.read_word(command):04X}"
            for command in (Command.NIST_HIGH, Command.NIST_MIDDLE, Command.NIST_LOW)
        )
        self.identity = DeviceIdentity(
            self.name,
            self.transport.serial_number,
            self.transport.firmware_version,
            manufacturer,
            nist,
            self.transport.address,
        )
        return self.identity

    def open(self, expected_identity=None):
        self.transport.open()
        try:
            self.read_identity()
            if expected_identity is not None and (
                self.identity.serial_number != expected_identity.serial_number
                or self.identity.nist_id != expected_identity.nist_id
                or self.identity.address != expected_identity.address
            ):
                raise SensorError("Reconnected sensor identity changed; monitoring stopped")
            # Establish known volatile state, only after the identity check passes.
            self._initialized = True
            self.set_heater(False)
            self.configure("on_demand", 0)
        except Exception:
            self.close()
            raise

    def configure(self, mode: str, low_power: int):
        validate_settings(mode, low_power)
        self.command(Command.EXIT_AUTO)
        self._sleep(0.002)
        if mode != "on_demand":
            self.command(MODE_COMMANDS[mode][low_power])
        self.mode, self.low_power = mode, low_power

    def read_measurement(self):
        if self.mode == "on_demand":
            self.command(MODE_COMMANDS[self.mode][self.low_power])
            self._sleep(CONVERSION_SECONDS[self.low_power])
        else:
            self.command(Command.FETCH)
        data = self.transport.read(6)
        self.read_status()
        return decode_measurement(data, self.mode != "on_demand", bool(self.status_word & 0x2000))

    def read_status(self):
        self.status_word = self.read_word(Command.STATUS)
        return self.status_word

    def clear_status(self):
        self.command(Command.CLEAR_STATUS)
        return self.read_status()

    def set_heater(self, enabled: bool):
        if enabled:
            # Minimum single element; deliberately no full-power UI control.
            self.command(Command.HEATER_CONFIG, encode_word(0x0001))
            if self.read_word(Command.HEATER_CONFIG) != 0x0001:
                raise SensorError("Heater configuration readback failed")
        self.command(Command.HEATER_ON if enabled else Command.HEATER_OFF)
        status = self.read_status()
        if bool(status & 0x2000) != enabled:
            raise SensorError("Heater status did not match the requested state")
        return status

    def reset(self):
        self.command(Command.RESET)
        self._sleep(0.020)
        # Startup can be EEPROM-configured to auto; explicitly restore our defaults.
        self.set_heater(False)
        self.configure("on_demand", 0)
        self.read_identity()
        return self.read_status()

    def close(self):
        errors = []
        if self._initialized:
            for command in (Command.HEATER_OFF, Command.EXIT_AUTO):
                try:
                    self.command(command)
                except Exception as exc:
                    errors.append(f"shutdown command 0x{command:04X}: {exc}")
            self._initialized = False
        try:
            self.transport.close()
        except Exception as exc:
            errors.append(str(exc))
        if errors:
            raise SensorError("Device released, but shutdown could not be confirmed: " + "; ".join(errors))


def create_sensor(backend="usb_hid", address=0x44, serial_number=None):
    if isinstance(address, str):
        address = int(address, 0)
    if backend == "simulation":
        from .simulation import SimulatedTransport

        transport = SimulatedTransport()
    elif backend == "usb_hid":
        from .usb_hid import USB2ANYHIDTransport

        transport = USB2ANYHIDTransport(address, serial_number=serial_number or None)
    else:
        raise ValueError("Unknown connection type")
    return HDC3020Sensor(transport)
