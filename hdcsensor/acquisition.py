"""Thread-safe sample buffer and recorder facade, following the TMP monitor."""

import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from .device_session import DeviceSession
from .models import Sample
from .protocol import validate_interval
from .recording import CsvRecorder


class AcquisitionService:
    def __init__(self, max_samples=7200, recorder_queue_size=4096):
        if max_samples < 1:
            raise ValueError("max_samples must be positive")
        self._lock = threading.RLock()
        self._samples = deque(maxlen=max_samples)
        self._sequence = 0
        self._auto_record = False
        self._recording_directory = Path("recordings")
        self.recorder = CsvRecorder(queue_size=recorder_queue_size)
        self.session = DeviceSession(
            self._accept_sample,
            on_connected=self._on_connected,
            on_disconnected=self.recorder.stop,
        )

    def _on_connected(self, sampling):
        with self._lock:
            auto_record, directory = self._auto_record, self._recording_directory
        if sampling and auto_record and not self.recorder.status().recording:
            self.recorder.start(directory, rotate_daily=True)

    def _accept_sample(self, reading, source, mode, low_power):
        with self._lock:
            self._sequence += 1
            sample = Sample(
                self._sequence,
                datetime.now(timezone.utc),
                reading.temperature_c,
                reading.relative_humidity_pct,
                source,
                reading.raw_temperature,
                reading.raw_humidity,
                mode,
                low_power,
                reading.heater_on,
            )
            self._samples.append(sample)
            self.recorder.submit(sample)

    def snapshot(self):
        with self._lock:
            return tuple(self._samples)

    def clear_samples(self):
        with self._lock:
            self._samples.clear()

    def start(self, sensor, interval_s=1.0, auto_record=False, recording_directory=Path("recordings")):
        interval_s = validate_interval(interval_s)
        with self._lock:
            self._auto_record = bool(auto_record)
            self._recording_directory = Path(recording_directory)
        if self.session.snapshot().connection == "connected":
            self._on_connected(sampling=True)
            return self.session.submit("resume", interval_s=interval_s)
        self.session.connect(sensor, interval_s, sampling=True)

    def shutdown(self):
        errors = []
        try:
            self.session.disconnect(wait=True)
        except Exception as exc:
            errors.append(str(exc))
        try:
            self.recorder.stop()
        except Exception as exc:
            errors.append(str(exc))
        if errors:
            raise RuntimeError("; ".join(errors))
