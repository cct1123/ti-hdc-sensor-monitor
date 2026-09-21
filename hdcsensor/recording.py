"""Non-blocking CSV recording worker."""

from __future__ import annotations

import csv
import io
import queue
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Sample

_SAFE_PREFIX = re.compile(r"[^A-Za-z0-9_-]+")


@dataclass(frozen=True)
class RecorderStatus:
    recording: bool
    path: Optional[Path]
    rows_written: int
    dropped_rows: int
    last_error: Optional[str]


class CsvRecorder:
    """Write samples on a separate thread so sampling never waits for disk I/O."""

    def __init__(self, queue_size: int = 4096) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be positive")
        self._queue_size = queue_size
        self._queue: queue.Queue[Sample] = queue.Queue(maxsize=queue_size)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._accepting = False
        self._path: Optional[Path] = None
        self._rows_written = 0
        self._dropped_rows = 0
        self._last_error: Optional[str] = None

    @staticmethod
    def _clean_prefix(prefix: str) -> str:
        cleaned = _SAFE_PREFIX.sub("_", prefix.strip()).strip("_")
        return cleaned[:64] or "hdc3020"

    def start(self, output_directory: Path, prefix: str = "hdc3020") -> Path:
        output_directory = Path(output_directory).resolve()
        output_directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        path = output_directory / f"{self._clean_prefix(prefix)}_{stamp}.csv"

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("CSV recording is already active")
            self._queue = queue.Queue(maxsize=self._queue_size)
            self._stop_event = threading.Event()
            self._accepting = True
            self._path = path
            self._rows_written = 0
            self._dropped_rows = 0
            self._last_error = None
            thread = threading.Thread(
                target=self._writer_loop,
                args=(path,),
                name="hdc-csv-writer",
                daemon=False,
            )
            self._thread = thread
            thread.start()
        return path

    def submit(self, sample: Sample) -> bool:
        with self._lock:
            if not self._accepting:
                return False
            try:
                # Keep the lock through the non-blocking put so stop() cannot
                # let the writer exit between acceptance and enqueueing.
                self._queue.put_nowait(sample)
                return True
            except queue.Full:
                self._dropped_rows += 1
                return False

    def _writer_loop(self, path: Path) -> None:
        try:
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(CSV_COLUMNS)
                stream.flush()
                while not self._stop_event.is_set() or not self._queue.empty():
                    try:
                        sample = self._queue.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    try:
                        writer.writerow(sample_row(sample))
                        stream.flush()
                        with self._lock:
                            self._rows_written += 1
                    except Exception:
                        with self._lock:
                            self._dropped_rows += 1
                        raise
                    finally:
                        self._queue.task_done()
        except Exception as exc:  # the status must expose writer failures
            with self._lock:
                self._last_error = f"{type(exc).__name__}: {exc}"
                self._accepting = False
                # Count accepted rows which can no longer be written. Stop new
                # submissions under the same lock before draining the queue.
                while True:
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        break
                    self._dropped_rows += 1
                    self._queue.task_done()

    def stop(self, timeout: float = 5.0) -> None:
        with self._lock:
            self._accepting = False
            self._stop_event.set()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
            if thread.is_alive():
                raise RuntimeError("CSV writer did not stop within the timeout")
        with self._lock:
            if self._thread is thread:
                self._thread = None

    def status(self) -> RecorderStatus:
        with self._lock:
            return RecorderStatus(
                # Downloads and new recordings must wait until flushing finishes.
                recording=self._thread is not None and self._thread.is_alive(),
                path=self._path,
                rows_written=self._rows_written,
                dropped_rows=self._dropped_rows,
                last_error=self._last_error,
            )


CSV_COLUMNS = [
    "timestamp_utc",
    "sequence",
    "temperature_c",
    "relative_humidity_pct",
    "source",
    "raw_temperature",
    "raw_humidity",
    "mode",
    "low_power",
    "heater_on",
]


def sample_row(sample):
    return [
        sample.timestamp_utc.isoformat(),
        sample.sequence,
        f"{sample.temperature_c:.6f}",
        f"{sample.relative_humidity_pct:.6f}",
        sample.source,
        sample.raw_temperature,
        sample.raw_humidity,
        sample.mode,
        sample.low_power,
        int(sample.heater_on),
    ]


def export_csv(samples):
    """Export a snapshot without changing the ongoing recording."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(CSV_COLUMNS)
    writer.writerows(sample_row(sample) for sample in samples)
    return stream.getvalue()
