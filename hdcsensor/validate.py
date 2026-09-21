"""Bounded acquisition/CSV/reopen check. Defaults to simulation; USB requires --hardware."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .acquisition import AcquisitionService
from .protocol import validate_interval
from .sensors import create_sensor


def wait_for(service, predicate, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = service.session.snapshot()
        if state.connection == "error":
            raise RuntimeError(state.last_error)
        if predicate():
            return
        time.sleep(0.025)
    raise TimeoutError("Validation timed out waiting for device/sample state")


def validate(samples=30, interval=1.0, hardware=False, serial=None, output=Path("recordings")):
    if not 2 <= samples <= 600:
        raise ValueError("Request 2..600 samples")
    interval = validate_interval(interval)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    service = AcquisitionService(max_samples=samples + 10)
    backend = "usb_hid" if hardware else "simulation"
    report = {
        "backend": backend,
        "physical_validation": hardware,
        "passed": False,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "requested_samples": samples,
        "requested_interval_s": interval,
        "errors": [],
        "checks": {},
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = output / f"validation_{stamp}.json"
    try:
        csv_path = service.recorder.start(
            output, "hardware-validation" if hardware else "simulation-validation"
        )
        report["csv"] = str(csv_path.resolve())
        service.start(create_sensor(backend, serial_number=serial), interval)
        wait_for(service, lambda: len(service.snapshot()) >= samples, samples * interval + 15)
        service.session.submit("pause").result(3)
        collected = service.snapshot()
        state = service.session.snapshot()
        report["identity"] = asdict(state.identity)
        report["failed_reads"] = state.failures
        service.recorder.stop()
        with csv_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        durations = [
            (b.timestamp_utc - a.timestamp_utc).total_seconds() for a, b in zip(collected, collected[1:])
        ]
        report["sample_count"] = len(collected)
        report["median_interval_s"] = statistics.median(durations)
        report["interval_range_s"] = [min(durations), max(durations)]
        checks = report["checks"]
        checks["paired_samples"] = len(collected) >= samples and all(
            -45 <= row.temperature_c <= 130 and 0 <= row.relative_humidity_pct <= 100 for row in collected
        )
        checks["cadence"] = 0.8 * interval <= report["median_interval_s"] <= 1.25 * interval
        checks["csv_matches_buffer"] = len(rows) == len(collected) and all(
            int(row["sequence"]) == sample.sequence
            and abs(float(row["temperature_c"]) - sample.temperature_c) < 0.000001
            and abs(float(row["relative_humidity_pct"]) - sample.relative_humidity_pct) < 0.000001
            and row["timestamp_utc"] == sample.timestamp_utc.isoformat()
            for row, sample in zip(rows, collected)
        )
        recorder = service.recorder.status()
        checks["no_recording_loss"] = not recorder.last_error and recorder.dropped_rows == 0
        checks["no_read_failures"] = state.failures == 0
        service.session.disconnect(wait=True)
        checks["clean_disconnect"] = service.session.snapshot().connection == "disconnected"
        service.session.connect(create_sensor(backend, serial_number=serial))
        wait_for(service, lambda: service.session.snapshot().connection == "connected", 12)
        checks["reopen_identity"] = service.session.snapshot().identity.nist_id == state.identity.nist_id
        service.session.disconnect(wait=True)
        checks["reopen_cleanup"] = service.session.snapshot().connection == "disconnected"
        report["passed"] = all(checks.values())
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        try:
            service.shutdown()
        except Exception as exc:
            report["errors"].append(f"Shutdown: {exc}")
        if service.session.snapshot().last_error:
            report["errors"].append(service.session.snapshot().last_error)
        report["passed"] = report["passed"] and not report["errors"]
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hardware", action="store_true", help="Open physical USB HID (candidate approval required)"
    )
    parser.add_argument("--serial", help="USB bridge serial, required if several boards are attached")
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--output", type=Path, default=Path("recordings"))
    args = parser.parse_args()
    path, report = validate(args.samples, args.interval, args.hardware, args.serial, args.output)
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {path}")
    if report["errors"]:
        print("\n".join(report["errors"]))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
