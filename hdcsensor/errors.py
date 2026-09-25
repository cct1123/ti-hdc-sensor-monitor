"""Explicit transport and sensor error categories."""


class SensorError(RuntimeError):
    """Hardware communication or device validation failed."""


class HIDTransportError(SensorError):
    """The open USB HID handle failed and must be reopened."""


class CRCError(SensorError):
    """Sensor response failed its CRC check."""


class NotReadyError(SensorError):
    """Auto mode has not produced a new conversion yet."""
