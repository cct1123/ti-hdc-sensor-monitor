import csv
import io
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from hdcsensor.acquisition import AcquisitionService
from hdcsensor.device_session import DeviceSession
from hdcsensor.errors import CRCError, SensorError
from hdcsensor.recording import export_csv
from hdcsensor.sensors import create_sensor


def wait_for(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for worker state")


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.service = AcquisitionService(max_samples=3)
        self.addCleanup(self.service.shutdown)
        self.sensor = create_sensor("simulation")

    def connect(self, sampling=False):
        self.service.session.connect(self.sensor, sampling=sampling)
        wait_for(lambda: self.service.session.snapshot().connection == "connected")

    def test_all_io_owned_by_one_worker_and_pause_resume(self):
        calls = []
        for name in ("open", "write", "read", "close"):
            original = getattr(self.sensor.transport, name)

            def wrapped(*args, _original=original, **kwargs):
                calls.append(threading.current_thread().name)
                return _original(*args, **kwargs)

            setattr(self.sensor.transport, name, wrapped)
        self.connect(sampling=True)
        wait_for(lambda: len(self.service.snapshot()) == 1)
        self.service.session.submit("pause").result(2)
        count = len(self.service.snapshot())
        time.sleep(0.04)
        self.assertEqual(len(self.service.snapshot()), count)
        self.service.session.submit("resume").result(2)
        wait_for(lambda: len(self.service.snapshot()) > count)
        self.service.session.disconnect(wait=True)
        self.assertEqual(set(calls), {"hdc-device-session"})
        self.assertFalse(self.sensor.transport.opened)

    def test_buffer_recording_and_export_keep_paired_metadata(self):
        self.connect()
        with tempfile.TemporaryDirectory() as directory:
            path = self.service.recorder.start(Path(directory), "../unsafe/name")
            for _ in range(5):
                self.service.session.submit("sample").result(2)
            self.service.recorder.stop()
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 5)
            self.assertEqual([int(row["sequence"]) for row in rows], [1, 2, 3, 4, 5])
            self.assertIn("SIMULATED", rows[0]["source"])
            self.assertIn("+00:00", rows[0]["timestamp_utc"])
            self.assertEqual(rows[0]["mode"], "on_demand")
            self.assertTrue(float(rows[0]["relative_humidity_pct"]) > 0)
            self.assertEqual(path.parent, Path(directory).resolve())
        self.assertEqual(len(self.service.snapshot()), 3)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(export_csv(self.service.snapshot()))))), 3)
        self.service.clear_samples()
        self.service.session.submit("sample").result(2)
        self.assertEqual(self.service.snapshot()[0].sequence, 6)

    def test_bad_crc_never_published_and_stops_after_three(self):
        self.sensor.read_measurement = Mock(side_effect=CRCError("bad RH CRC"))
        self.connect()
        # Accelerate the scheduler without changing production interval validation.
        with patch.object(self.service.session, "_period", return_value=0.01):
            self.service.session.submit("resume").result(2)
            wait_for(lambda: self.service.session.snapshot().connection == "error")
        self.assertEqual(len(self.service.snapshot()), 0)
        self.assertEqual(self.service.session.snapshot().failures, 3)
        self.assertFalse(self.sensor.transport.opened)

    def test_transient_crc_failure_recovers_and_reports_counter(self):
        self.connect()
        good = self.sensor.read_measurement()
        self.sensor.read_measurement = Mock(side_effect=[CRCError("noise"), good, good, good])
        with patch.object(self.service.session, "_period", return_value=0.03):
            self.service.session.submit("resume").result(2)
            wait_for(lambda: len(self.service.snapshot()) >= 1)
            self.service.session.submit("pause").result(2)
        self.assertEqual(self.service.session.snapshot().failures, 1)
        self.assertIsNone(self.service.session.snapshot().last_error)

    def test_invalid_config_does_not_disconnect_but_io_failure_does(self):
        self.connect()
        future = self.service.session.submit("configure", mode="invalid", low_power=0)
        with self.assertRaises(ValueError):
            future.result(2)
        self.assertEqual(self.service.session.snapshot().connection, "connected")
        with patch.object(self.sensor, "configure", side_effect=SensorError("uncertain write")):
            with self.assertRaises(SensorError):
                self.service.session.submit("configure", mode="auto_1hz", low_power=0).result(2)
            wait_for(lambda: self.service.session.snapshot().connection == "error")
        self.assertIn("uncertain write", self.service.session.snapshot().last_error)

    def test_disconnect_cancels_queue_and_reconnect_has_new_generation(self):
        self.connect()
        entered, release = threading.Event(), threading.Event()
        original = self.sensor.read_status

        def delayed():
            entered.set()
            release.wait(2)
            return original()

        with patch.object(self.sensor, "read_status", side_effect=delayed):
            first = self.service.session.submit("status")
            self.assertTrue(entered.wait(1))
            waiting = self.service.session.submit("identity")
            self.service.session.disconnect()
            with self.assertRaises(RuntimeError):
                self.service.session.connect(create_sensor("simulation"))
            release.set()
            self.service.session.disconnect(wait=True)
            self.assertTrue(first.done())
            self.assertTrue(waiting.cancelled())
        generation = self.service.session.snapshot().generation
        self.service.session.connect(create_sensor("simulation"))
        wait_for(lambda: self.service.session.snapshot().connection == "connected")
        self.assertEqual(self.service.session.snapshot().generation, generation + 1)

    def test_heater_expires_while_sampling_paused_and_reset_defaults(self):
        self.connect()
        self.service.session.submit("configure", mode="auto_1hz", low_power=2).result(2)
        self.service.session.submit("heater_pulse").result(2)
        self.assertTrue(self.service.session.snapshot().heater_on)
        with self.assertRaises(ValueError):
            self.service.session.submit("heater_pulse").result(2)
        self.service.session._heater_deadline = time.monotonic()
        wait_for(lambda: not self.service.session.snapshot().heater_on)
        self.service.session.submit("reset").result(2)
        self.assertEqual(self.service.session.snapshot().mode, "on_demand")
        self.assertEqual(self.service.session.snapshot().low_power, 0)

    def test_queue_is_bounded(self):
        session = DeviceSession(lambda *args: None, queue_size=1)
        self.addCleanup(session.disconnect, wait=True)
        session.connect(self.sensor)
        wait_for(lambda: session.snapshot().connection == "connected")
        entered, release = threading.Event(), threading.Event()

        def delayed():
            entered.set()
            release.wait(2)

        with patch.object(self.sensor, "read_status", side_effect=delayed):
            session.submit("status")
            self.assertTrue(entered.wait(1))
            session.submit("identity")
            try:
                with self.assertRaisesRegex(RuntimeError, "queue is full"):
                    session.submit("status")
            finally:
                release.set()
                session.disconnect(wait=True)
