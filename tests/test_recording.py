import csv
import io
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from test_session import wait_for

from hdcsensor.models import Sample
from hdcsensor.recording import CsvRecorder


class RecorderTests(unittest.TestCase):
    def test_disk_failure_is_visible_and_accepted_rows_count_as_lost(self):
        recorder = CsvRecorder()
        self.addCleanup(recorder.stop)
        entered, release = threading.Event(), threading.Event()

        def fail_open(*args, **kwargs):
            entered.set()
            release.wait(2)
            raise OSError("disk full")

        with tempfile.TemporaryDirectory() as directory, patch.object(Path, "open", side_effect=fail_open):
            recorder.start(Path(directory))
            self.assertTrue(entered.wait(1))
            sample = Sample(1, datetime.now(timezone.utc), 25, 40, "TEST")
            self.assertTrue(recorder.submit(sample))
            self.assertTrue(recorder.submit(sample))
            release.set()
            recorder.stop()
            self.assertIn("disk full", recorder.status().last_error)
            self.assertEqual(recorder.status().dropped_rows, 2)
            self.assertFalse(recorder.submit(sample))

    def test_bounded_queue_nonblocking_and_drain_before_download_ready(self):
        recorder = CsvRecorder(queue_size=1)
        self.addCleanup(recorder.stop)
        entered, release = threading.Event(), threading.Event()
        original = Path.open

        def delayed(path, *args, **kwargs):
            entered.set()
            release.wait(2)
            return original(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as directory, patch.object(Path, "open", delayed):
            path = recorder.start(Path(directory))
            self.assertTrue(entered.wait(1))
            sample = Sample(1, datetime.now(timezone.utc), 25, 40, "TEST")
            self.assertTrue(recorder.submit(sample))
            self.assertFalse(recorder.submit(sample))
            with self.assertRaisesRegex(RuntimeError, "timeout"):
                recorder.stop(timeout=0.01)
            self.assertTrue(recorder.status().recording)
            with self.assertRaisesRegex(RuntimeError, "already active"):
                recorder.start(Path(directory))
            release.set()
            recorder.stop()
            self.assertFalse(recorder.status().recording)
            self.assertEqual(recorder.status().dropped_rows, 1)
            self.assertEqual(recorder.status().rows_written, 1)
            self.assertEqual(len(list(csv.DictReader(io.StringIO(path.read_text())))), 1)

    def test_mid_stream_flush_failure_counts_failed_row(self):
        class FailingStream(io.StringIO):
            def __init__(self):
                super().__init__()
                self.flushes = 0

            def flush(self):
                self.flushes += 1
                if self.flushes > 1:
                    raise OSError("lost disk")

        recorder = CsvRecorder()
        self.addCleanup(recorder.stop)
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(Path, "open", return_value=FailingStream()),
        ):
            recorder.start(Path(directory))
            recorder.submit(Sample(1, datetime.now(timezone.utc), 25, 40, "TEST"))
            wait_for(lambda: recorder.status().last_error is not None)
            recorder.stop()
            self.assertEqual(recorder.status().dropped_rows, 1)
