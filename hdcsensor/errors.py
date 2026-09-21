"""Explicit transport and sensor error categories."""


class SensorError(RuntimeError):
    """Hardware communication or device validation failed."""


class CRCError(SensorError):
    """Sensor response failed its CRC check."""


class NotReadyError(SensorError):
    """Auto mode has not produced a new conversion yet."""
