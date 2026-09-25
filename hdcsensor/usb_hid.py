"""USB2ANY HID transport adapted from the MIT TMP monitor.

Protocol reference: TI GUI Composer 1.17, ti-core-databind
src/internal/reg/USB2ANY.js and src/internal/HidPacketCodec.js.
Includes acknowledged volatile configuration writes. No EEPROM unlock,
firmware update, or general-call reset is exposed.
"""

from __future__ import annotations

import time
from typing import Optional

from .errors import SensorError

VENDOR_ID = 0x2047
PRODUCT_ID = 0x0301
REPORT_ID = 0x3F
REPORT_SIZE = 64


def _crc8(data: bytes) -> int:
    """CRC-8, polynomial 0x07, initial value zero, no reflection."""
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = ((crc << 1) ^ (0x07 if crc & 0x80 else 0)) & 0xFF
    return crc


class USB2ANYHIDTransport:
    """Raw I2C transport on a USB2ANY/OneDemo HID bridge.

    One acquisition worker must own the instance. Close TI's GUI before use.
    HDC3020EVM hardware validation is tracked in outputs/REPORT.md.
    """

    def __init__(
        self,
        address: int = 0x44,
        serial_number: Optional[str] = None,
        timeout_s: float = 1.0,
    ) -> None:
        if isinstance(address, bool) or not isinstance(address, int) or address not in range(0x44, 0x48):
            raise ValueError("HDC3020 address must be 0x44..0x47")
        self.address = address
        if not 0 < timeout_s <= 5:
            raise ValueError("USB HID timeout must be greater than 0 and at most 5 seconds")
        self.timeout_s = float(timeout_s)
        self.serial_number = serial_number
        self.firmware_version: Optional[str] = None
        self.frequency_hz = 100000
        self._device = None
        self._sequence = 1

    @property
    def name(self) -> str:
        return f"HDC3020EVM USB HID at 0x{self.address:02X}"

    def open(self) -> None:
        if self._device is not None:
            raise SensorError("USB HID sensor is already open")
        try:
            import hid
        except ImportError as exc:
            raise SensorError("The USB HID backend needs hidapi: uv sync --extra usb") from exc

        self.firmware_version = None
        try:
            devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
            if self.serial_number is not None:
                devices = [d for d in devices if d.get("serial_number") == self.serial_number]
            if not devices:
                if self.serial_number is not None:
                    raise SensorError(
                        f"USB2ANY bridge serial {self.serial_number} was not found; "
                        "check the USB connection and serial number"
                    )
                raise SensorError("No USB2ANY/OneDemo bridge was found; check the USB connection")
            if len(devices) != 1:
                serials = ", ".join(str(device.get("serial_number") or "<unavailable>") for device in devices)
                raise SensorError(
                    f"Multiple USB2ANY bridges found ({serials}); "
                    "enter the HDC3020EVM USB serial or connect only that board"
                )
            self._device = hid.device()
            self._device.open_path(devices[0]["path"])
            self.serial_number = devices[0].get("serial_number")
            self._sequence = 1
            version = self._command(0x0A, bytes(4))
            if len(version) != 4:
                raise SensorError("USB2ANY returned an invalid firmware version")
            self.firmware_version = ".".join(str(part) for part in version)
            self.configure_i2c(self.frequency_hz)
        except Exception as exc:
            self.close()
            if isinstance(exc, OSError):
                raise SensorError(
                    f"Could not open USB HID EVM: {exc}. Close TI's EVM GUI and retry."
                ) from exc
            raise

    def _command(self, command: int, payload: bytes) -> bytes:
        if self._device is None:
            raise SensorError("USB HID sensor is not open")
        if len(payload) > 54:
            raise ValueError("USB2ANY payload exceeds 54 bytes")
        sequence = self._sequence
        self._sequence = 1 if sequence >= 254 else sequence + 1
        packet = bytearray([0x54, 0, len(payload), 1, 0, sequence, 0, command])
        packet.extend(payload)
        packet[1] = _crc8(packet[2:])
        report = (bytes([REPORT_ID, len(packet)]) + packet).ljust(REPORT_SIZE, b"\0")
        try:
            written = self._device.write(report)
            if written != REPORT_SIZE:
                raise SensorError(f"USB HID wrote {written} bytes; expected {REPORT_SIZE}")
            deadline = time.monotonic() + self.timeout_s
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SensorError(f"USB2ANY command 0x{command:02X} timed out; close TI's GUI and retry")
                raw = bytes(self._device.read(REPORT_SIZE, max(1, int(remaining * 1000))))
                if not raw:
                    continue
                if len(raw) < 10 or raw[0] != REPORT_ID:
                    raise SensorError("Invalid USB2ANY HID report header")
                length = raw[1]
                if not 8 <= length <= 62 or len(raw) < length + 2:
                    raise SensorError("Invalid USB2ANY HID report length")
                reply = raw[2 : 2 + length]  # Trailing HID padding is not part of the CRC.
                if reply[0] != 0x54 or reply[2] != length - 8:
                    raise SensorError("Invalid USB2ANY packet header or payload length")
                if _crc8(reply[2:]) != reply[1]:
                    raise SensorError("USB2ANY reply CRC mismatch")
                if reply[3] in (4, 5) or reply[5] != sequence or reply[7] != command:
                    continue  # Asynchronous events or replies queued by a previous session.
                if reply[3] == 3:
                    code = reply[6] - 256
                    detail = {
                        -44: "I2C address was not acknowledged",
                        -49: "I2C write timed out (-49); verify the selected bridge and sensor bus",
                        -54: "bridge I2C pullups require 3.3 V EXT power",
                    }.get(code, f"device error {code}")
                    raise SensorError(
                        f"USB2ANY serial {self.serial_number or '<unavailable>'} "
                        f"command 0x{command:02X}: {detail}"
                    )
                if reply[3] != 2 or reply[4] != 0 or reply[6] != 0:
                    raise SensorError("Unexpected USB2ANY reply type, flags, or status")
                return reply[8:]
        except OSError as exc:
            raise SensorError(f"USB HID communication failed: {exc}") from exc

    def configure_i2c(self, frequency_hz: int) -> None:
        if frequency_hz not in (100000, 400000):
            raise ValueError("I2C frequency must be 100 or 400 kHz")
        # The stock EVM has on-board 10 kOhm pullups to its USB-powered 3.3 V rail.
        # Bridge-managed pullups require separate EXT power and fault with -54.
        self._command(0x01, bytes([0 if frequency_hz == 100000 else 1, 0, 0]))
        self.frequency_hz = frequency_hz

    def write(self, data: bytes) -> None:
        """Raw I2C write with STOP; includes no implicit register address."""
        data = bytes(data)
        if not 1 <= len(data) <= 51:
            raise ValueError("Raw I2C write requires 1..51 bytes")
        self._command(0x02, bytes([0, self.address, len(data)]) + data)

    def read(self, count: int) -> bytes:
        """Raw I2C read, using the four-byte payload in TI's HDC3020 GUI."""
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 54:
            raise ValueError("Raw I2C read requires 1..54 bytes")
        data = self._command(0x03, bytes([0, self.address, count, 0]))
        if len(data) != count:
            raise SensorError(f"USB2ANY returned {len(data)} I2C bytes; expected {count}")
        return data

    def close(self) -> None:
        device, self._device = self._device, None
        if device is not None:
            device.close()
