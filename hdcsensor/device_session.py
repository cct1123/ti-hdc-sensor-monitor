"""One worker owns every open, command, measurement and close on the device."""

from __future__ import annotations

import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import replace

from .errors import HIDTransportError, SensorError
from .models import DeviceSnapshot
from .protocol import MODE_PERIODS, validate_interval, validate_settings


class DeviceSession:
    COMMANDS = {
        "resume",
        "pause",
        "configure",
        "status",
        "clear_status",
        "identity",
        "reset",
        "heater_pulse",
        "heater_off",
        "sample",
    }

    def __init__(self, on_sample, queue_size=32, on_connected=None, on_disconnected=None):
        self._on_sample = on_sample
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._lock = threading.RLock()
        self._snapshot = DeviceSnapshot()
        self._thread = None
        self._stop = threading.Event()
        self._queue_size = queue_size
        self._queue = queue.Queue(maxsize=queue_size)
        self._heater_deadline = None
        self._next_sample = 0.0
        self._recovery_available = False

    def snapshot(self):
        with self._lock:
            return self._snapshot

    def _update(self, **changes):
        with self._lock:
            self._snapshot = replace(self._snapshot, **changes)

    def connect(self, sensor, interval_s=1.0, sampling=False):
        interval_s = validate_interval(interval_s)
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("A device session is already active")
            self._stop = threading.Event()
            self._queue = queue.Queue(maxsize=self._queue_size)
            self._heater_deadline = None
            self._recovery_available = sampling
            self._snapshot = DeviceSnapshot(
                connection="connecting",
                interval_s=interval_s,
                generation=self._snapshot.generation + 1,
                note="Opening device…",
            )
            self._thread = threading.Thread(
                target=self._run, args=(sensor, sampling), name="hdc-device-session", daemon=False
            )
            self._thread.start()

    def submit(self, kind, **kwargs) -> Future:
        if kind not in self.COMMANDS:
            raise ValueError(f"Unknown device operation: {kind}")
        with self._lock:
            if self._snapshot.connection != "connected" or self._stop.is_set():
                raise RuntimeError("Connect the device before issuing commands")
            future = Future()
            try:
                self._queue.put_nowait((kind, kwargs, future))
            except queue.Full as exc:
                raise RuntimeError("Device command queue is full; wait for pending operations") from exc
            return future

    def disconnect(self, wait=False, timeout=8.0):
        with self._lock:
            thread = self._thread
            self._stop.set()
            if thread is not None and thread.is_alive():
                self._update(connection="disconnecting", sampling=False, note="Releasing device…")
        if wait and thread is not None and thread is not threading.current_thread():
            thread.join(timeout)
            if thread.is_alive():
                raise RuntimeError("Device worker is still stopping; do not open another session")

    def _publish_device(self, sensor, **changes):
        self._update(
            identity=sensor.identity,
            mode=sensor.mode,
            low_power=sensor.low_power,
            status_word=sensor.status_word,
            heater_on=bool(sensor.status_word & 0x2000),
            **changes,
        )

    def _period(self):
        state = self.snapshot()
        # Margin avoids reading the auto latch just before the next conversion.
        return max(state.interval_s, MODE_PERIODS[state.mode] + 0.020)

    def _take_sample(self, sensor):
        reading = sensor.read_measurement()
        self._on_sample(reading, sensor.name, sensor.mode, sensor.low_power)
        self._recovery_available = False
        self._publish_device(sensor, consecutive_failures=0, last_error=None)

    def _reopen_after_hid_failure(self, sensor):
        state = self.snapshot()
        if state.heater_on or self._heater_deadline is not None:
            raise SensorError("USB HID failed during a heater pulse; shutdown state is uncertain")
        previous_identity = sensor.identity
        previous_mode, previous_low_power = sensor.mode, sensor.low_power
        try:
            sensor.close()
        except SensorError:
            # The stale HID handle may reject shutdown commands. A successful
            # open below verifies heater-off on the newly opened handle.
            pass
        if self._stop.is_set():
            raise SensorError("Disconnect requested before USB HID reopen")
        sensor.open(expected_identity=previous_identity)
        if previous_mode != "on_demand" or previous_low_power != 0:
            sensor.configure(previous_mode, previous_low_power)
        self._publish_device(
            sensor,
            consecutive_failures=0,
            last_error=None,
            note="USB HID handle reopened after failure; monitoring resumed.",
        )

    def _execute(self, sensor, kind, args):
        if kind == "resume":
            interval = validate_interval(args.get("interval_s", self.snapshot().interval_s))
            self._recovery_available = True
            self._update(sampling=True, interval_s=interval)
            self._next_sample = time.monotonic() + (self._period() if sensor.mode != "on_demand" else 0)
            message = "Monitoring started."
        elif kind == "pause":
            self._recovery_available = False
            self._update(sampling=False)
            message = "Sampling paused; device remains connected."
        elif kind == "configure":
            mode, low_power = args.get("mode"), args.get("low_power")
            validate_settings(mode, low_power)
            sensor.configure(mode, low_power)
            self._publish_device(sensor)
            self._next_sample = time.monotonic() + self._period()
            message = f"Measurement mode {mode}, LPM{low_power} applied (volatile)."
        elif kind == "status":
            sensor.read_status()
            message = f"Status read: 0x{sensor.status_word:04X}."
        elif kind == "clear_status":
            sensor.clear_status()
            message = f"Tracking/reset flags cleared; status 0x{sensor.status_word:04X}."
        elif kind == "identity":
            sensor.read_identity()
            message = "Manufacturer and NIST identity checked."
        elif kind == "reset":
            sensor.reset()
            self._heater_deadline = None
            self._next_sample = time.monotonic() + 0.020
            message = "Soft reset complete; on-demand LPM0, heater off."
        elif kind == "heater_pulse":
            # Fixed 5-second pulse, minimum heater element. Repeated requests do
            # not extend an existing pulse. Deadline is checked even while paused.
            if self._heater_deadline is not None:
                raise ValueError("A heater pulse is already active")
            sensor.set_heater(True)
            self._heater_deadline = time.monotonic() + 5.0
            message = "Heater pulse active for 5 s; readings are heater-affected."
        elif kind == "heater_off":
            sensor.set_heater(False)
            self._heater_deadline = None
            message = "Heater disabled and status verified."
        elif kind == "sample":
            if self.snapshot().sampling or sensor.mode != "on_demand":
                raise ValueError("Pause monitoring and select on-demand mode before taking one sample")
            self._take_sample(sensor)
            message = "One paired sample acquired."
        else:
            raise ValueError(f"Unsupported operation {kind}")
        self._publish_device(sensor, note=message, last_error=None)
        return message

    def _run(self, sensor, sampling):
        failure = None
        try:
            sensor.open()
            if not self._stop.is_set():
                if self._on_connected is not None:
                    self._on_connected(sampling)
                self._publish_device(
                    sensor,
                    connection="connected",
                    sampling=sampling,
                    note="Connected; heater off, on-demand LPM0.",
                )
            self._next_sample = time.monotonic()
            while not self._stop.is_set():
                now = time.monotonic()
                if self._heater_deadline is not None and now >= self._heater_deadline:
                    sensor.set_heater(False)
                    self._heater_deadline = None
                    self._publish_device(sensor, note="Heater pulse finished; allow the sensor to cool.")
                if self.snapshot().sampling and now >= self._next_sample:
                    try:
                        self._take_sample(sensor)
                    except HIDTransportError:
                        state = self.snapshot()
                        self._update(failures=state.failures + 1, consecutive_failures=1)
                        if not self._recovery_available:
                            raise
                        self._recovery_available = False
                        self._reopen_after_hid_failure(sensor)
                        self._next_sample = time.monotonic() + (
                            self._period() if sensor.mode != "on_demand" else 0
                        )
                        continue
                    except SensorError as exc:
                        state = self.snapshot()
                        self._update(
                            failures=state.failures + 1,
                            consecutive_failures=state.consecutive_failures + 1,
                            last_error=str(exc),
                        )
                        if state.consecutive_failures + 1 >= 3:
                            raise SensorError(
                                f"Stopped after 3 consecutive failed measurements: {exc}"
                            ) from exc
                    # Skip missed slots rather than burst-read old measurements.
                    self._next_sample = max(self._next_sample + self._period(), time.monotonic() + 0.001)
                deadlines = [time.monotonic() + 0.2]
                if self.snapshot().sampling:
                    deadlines.append(self._next_sample)
                if self._heater_deadline is not None:
                    deadlines.append(self._heater_deadline)
                try:
                    kind, args, future = self._queue.get(timeout=max(0.0, min(deadlines) - time.monotonic()))
                except queue.Empty:
                    continue
                try:
                    if self._stop.is_set():
                        future.cancel()
                        continue
                    if not future.set_running_or_notify_cancel():
                        continue
                    try:
                        result = self._execute(sensor, kind, args)
                    except (ValueError, TypeError) as exc:
                        self._update(note=f"Command rejected: {exc}")
                        future.set_exception(exc)
                    except Exception as exc:
                        future.set_exception(exc)
                        # A timed-out write can have taken effect. Reconnect must
                        # establish known state before further sampling/commands.
                        raise
                    else:
                        future.set_result(result)
                finally:
                    self._queue.task_done()
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
        finally:
            # Reject new requests before draining, including after unexpected errors.
            self._update(connection="disconnecting", sampling=False)
            while True:
                try:
                    _, _, future = self._queue.get_nowait()
                except queue.Empty:
                    break
                future.cancel()
                self._queue.task_done()
            try:
                sensor.close()
            except Exception as exc:
                failure = "; ".join(filter(None, (failure, str(exc))))
            if self._on_disconnected is not None:
                try:
                    self._on_disconnected()
                except Exception as exc:
                    failure = "; ".join(filter(None, (failure, str(exc))))
            self._heater_deadline = None
            self._update(
                connection="error" if failure else "disconnected",
                sampling=False,
                last_error=failure,
                heater_on=False if not failure else self.snapshot().heater_on,
                note="Session failed; reconnect explicitly." if failure else "Disconnected; heater disabled.",
            )
