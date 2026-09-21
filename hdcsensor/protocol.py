"""HDC3020 command/CRC codec, grounded in SNAS778D tables 7-1 and 7-4."""

import math
from enum import IntEnum

from .errors import CRCError, NotReadyError, SensorError
from .models import Measurement


class Command(IntEnum):
    EXIT_AUTO = 0x3093
    FETCH = 0xE000
    STATUS = 0xF32D
    CLEAR_STATUS = 0x3041
    RESET = 0x30A2
    HEATER_ON = 0x306D
    HEATER_OFF = 0x3066
    HEATER_CONFIG = 0x306E
    NIST_HIGH = 0x3683
    NIST_MIDDLE = 0x3684
    NIST_LOW = 0x3685
    MANUFACTURER = 0x3781


MODE_COMMANDS = {
    "on_demand": (0x2400, 0x240B, 0x2416, 0x24FF),
    "auto_1hz": (0x2130, 0x2126, 0x212D, 0x21FF),
    "auto_0.5hz": (0x2032, 0x2024, 0x202F, 0x20FF),
}
MODE_PERIODS = {"on_demand": 0.0, "auto_1hz": 1.0, "auto_0.5hz": 2.0}
# Datasheet maximum conversion durations, plus a small host scheduling margin.
CONVERSION_SECONDS = (0.016, 0.010, 0.007, 0.006)


def crc8(data: bytes) -> int:
    """Sensor CRC: polynomial 0x31, init 0xFF, no reflection or final XOR."""
    crc = 0xFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = ((crc << 1) ^ (0x31 if crc & 0x80 else 0)) & 0xFF
    return crc


def encode_word(value: int) -> bytes:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFF:
        raise ValueError("Expected an unsigned 16-bit word")
    data = value.to_bytes(2, "big")
    return data + bytes([crc8(data)])


def decode_word(data: bytes, label: str = "word") -> int:
    if len(data) != 3:
        raise SensorError(f"{label}: expected 3 bytes, received {len(data)}")
    expected = crc8(data[:2])
    if data[2] != expected:
        raise CRCError(f"{label}: CRC mismatch (0x{data[2]:02X}, expected 0x{expected:02X})")
    return int.from_bytes(data[:2], "big")


def decode_measurement(data: bytes, auto: bool = False, heater_on: bool = False) -> Measurement:
    if len(data) != 6:
        raise SensorError(f"Measurement: expected 6 bytes, received {len(data)}")
    # TI table 7-4: an empty auto-mode readout returns all FFs. Some revisions
    # return CRC-protected 0xFFFF words; reject both rather than plot 130 C/100%.
    if auto and data in (b"\xff" * 6, encode_word(0xFFFF) * 2):
        raise NotReadyError("Auto measurement has no new result yet")
    temperature = decode_word(data[:3], "temperature")
    humidity = decode_word(data[3:], "humidity")
    return Measurement(
        -45.0 + 175.0 * temperature / 65535.0, 100.0 * humidity / 65535.0, temperature, humidity, heater_on
    )


def validate_settings(mode: str, low_power: int) -> None:
    if mode not in MODE_COMMANDS:
        raise ValueError("Select on-demand, auto 1 Hz, or auto 0.5 Hz")
    if isinstance(low_power, bool) or not isinstance(low_power, int) or not 0 <= low_power <= 3:
        raise ValueError("Low-power mode must be 0, 1, 2, or 3")


def validate_interval(value) -> float:
    if isinstance(value, bool):
        raise ValueError("Sample interval must be 1..60 seconds")
    try:
        value = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Sample interval must be 1..60 seconds") from exc
    if not math.isfinite(value) or not 1 <= value <= 60:
        raise ValueError("Sample interval must be 1..60 seconds")
    return value


STATUS_FLAGS = {
    15: "Alert pending",
    13: "Heater enabled",
    11: "RH tracking alert",
    10: "Temperature tracking alert",
    9: "RH high",
    8: "RH low",
    7: "Temperature high",
    6: "Temperature low",
    4: "Reset detected",
    0: "Last data-write checksum failed",
}


def status_labels(word: int):
    return [label for bit, label in STATUS_FLAGS.items() if word & (1 << bit)]
