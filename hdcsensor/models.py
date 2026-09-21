"""Immutable values passed between the device worker, recorder and dashboard."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Measurement:
    temperature_c: float
    relative_humidity_pct: float
    raw_temperature: int
    raw_humidity: int
    heater_on: bool = False


@dataclass(frozen=True)
class Sample:
    sequence: int
    timestamp_utc: datetime
    temperature_c: float
    relative_humidity_pct: float
    source: str
    raw_temperature: int = 0
    raw_humidity: int = 0
    mode: str = "on_demand"
    low_power: int = 0
    heater_on: bool = False


@dataclass(frozen=True)
class DeviceIdentity:
    source: str
    serial_number: Optional[str]
    firmware_version: Optional[str]
    manufacturer_id: int
    nist_id: str
    address: int = 0x44


@dataclass(frozen=True)
class DeviceSnapshot:
    connection: str = "disconnected"
    generation: int = 0
    sampling: bool = False
    interval_s: float = 1.0
    mode: str = "on_demand"
    low_power: int = 0
    identity: Optional[DeviceIdentity] = None
    status_word: Optional[int] = None
    heater_on: bool = False
    failures: int = 0
    consecutive_failures: int = 0
    note: str = "Connect a sensor to begin."
    last_error: Optional[str] = None
