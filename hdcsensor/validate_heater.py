"""One minimum-element five-second heater pulse; physical use needs separate approval."""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .acquisition import AcquisitionService
from .sensors import create_sensor
from .ui.monitor import history_figure
from .validate import wait_for


def validate_heater(hardware=False, serial=None, output=Path("recordings")):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "backend": "usb_hid" if hardware else "simulation",
        "physical_validation": hardware,
        "passed": False,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "errors": [],
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = output / f"heater_{stamp}.json"
    service = AcquisitionService(max_samples=30)

    def check(name, condition):
        report["checks"][name] = bool(condition)
        if not condition:
            raise AssertionError(name)

    def command(name, **kwargs):
        return service.session.submit(name, **kwargs).result(timeout=5)

    try:
        backend = "usb_hid" if hardware else "simulation"
        service.session.connect(create_sensor(backend, serial_number=serial), sampling=False)
        wait_for(service, lambda: service.session.snapshot().connection == "connected", 12)
        report["identity"] = asdict(service.session.snapshot().identity)
        check("initial_heater_off", not service.session.snapshot().heater_on)
        csv_path = service.recorder.start(output, "heater-validation")
        report["csv"] = str(csv_path.resolve())
        command("sample")
        baseline = service.snapshot()[-1]

        pulse_started = time.monotonic()
        command("heater_pulse")
        check("heater_status_on", service.session.snapshot().heater_on)
        command("resume", interval_s=1.0)
        wait_for(service, lambda: len(service.snapshot()) >= 3, 4)
        command("pause")
        check("heater_still_on_when_paused", service.session.snapshot().heater_on)
        wait_for(service, lambda: not service.session.snapshot().heater_on, 8)
        report["pulse_duration_s"] = time.monotonic() - pulse_started
        check("automatic_heater_off", not (service.session.snapshot().status_word & 0x2000))
        check("pulse_duration", 4.5 <= report["pulse_duration_s"] <= 7.0)

        before_cooldown = len(service.snapshot())
        command("resume", interval_s=1.0)
        wait_for(service, lambda: len(service.snapshot()) >= before_cooldown + 10, 15)
        command("pause")
        command("status")
        check("final_heater_status_off", not (service.session.snapshot().status_word & 0x2000))
        samples = service.snapshot()
        heater_samples = [sample for sample in samples if sample.heater_on]
        check("heater_affected_pairs", len(heater_samples) >= 1)
        report["baseline_temperature_c"] = baseline.temperature_c
        report["peak_heater_temperature_c"] = max(sample.temperature_c for sample in heater_samples)
        report["final_temperature_c"] = samples[-1].temperature_c
        report["baseline_humidity_pct"] = baseline.relative_humidity_pct
        report["final_humidity_pct"] = samples[-1].relative_humidity_pct
        report["sample_count"] = len(samples)
        report["heater_on_sample_count"] = len(heater_samples)

        figure = history_figure(samples)
        check(
            "plot_heater_markers",
            len(figure.data) == 2
            and all(
                "Heater on" in trace.customdata and "Heater off" in trace.customdata for trace in figure.data
            ),
        )
        service.recorder.stop()
        with csv_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        check(
            "csv_heater_flags",
            len(rows) == len(samples)
            and any(row["heater_on"] == "1" for row in rows)
            and rows[-1]["heater_on"] == "0",
        )
        recorder = service.recorder.status()
        check("no_recording_loss", not recorder.last_error and recorder.dropped_rows == 0)
        check("no_read_failures", service.session.snapshot().failures == 0)
        service.session.disconnect(wait=True)
        check("clean_disconnect", service.session.snapshot().connection == "disconnected")
        report["passed"] = all(report["checks"].values())
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
    parser.add_argument("--hardware", action="store_true", help="Open the separately approved physical EVM")
    parser.add_argument(
        "--confirm-attended", action="store_true", help="Confirm the physical setup is attended"
    )
    parser.add_argument("--serial", help="USB bridge serial, required if several boards are attached")
    parser.add_argument("--output", type=Path, default=Path("recordings"))
    args = parser.parse_args()
    if args.hardware and not args.confirm_attended:
        parser.error("physical heater testing requires --confirm-attended and separate approval")
    path, report = validate_heater(args.hardware, args.serial, args.output)
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {path}")
    if report["errors"]:
        print("\n".join(report["errors"]))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
