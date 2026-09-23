"""Bounded non-heater control check; physical USB requires --hardware."""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .acquisition import AcquisitionService
from .sensors import create_sensor
from .validate import wait_for


def validate_controls(hardware=False, serial=None, output=Path("recordings")):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "backend": "usb_hid" if hardware else "simulation",
        "physical_validation": hardware,
        "passed": False,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "modes": [],
        "errors": [],
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = output / f"controls_{stamp}.json"
    service = AcquisitionService(max_samples=50)

    def check(name, condition):
        report["checks"][name] = bool(condition)
        if not condition:
            raise AssertionError(name)

    def command(name, **kwargs):
        return service.session.submit(name, **kwargs).result(timeout=5)

    def capture(mode, low_power, count, interval):
        command("configure", mode=mode, low_power=low_power)
        before = len(service.snapshot())
        if mode == "on_demand":
            command("sample")
        else:
            command("resume", interval_s=interval)
            try:
                wait_for(service, lambda: len(service.snapshot()) >= before + count, count * interval + 8)
            finally:
                command("pause")
        samples = service.snapshot()[before:]
        valid = len(samples) >= count and all(
            sample.mode == mode
            and sample.low_power == low_power
            and not sample.heater_on
            and -45 <= sample.temperature_c <= 130
            and 0 <= sample.relative_humidity_pct <= 100
            for sample in samples
        )
        check(f"{mode}_lpm{low_power}_paired", valid)
        med = None
        if count >= 3:
            durations = [
                (b.timestamp_utc - a.timestamp_utc).total_seconds() for a, b in zip(samples, samples[1:])
            ]
            med = statistics.median(durations)
            check(f"{mode}_cadence", 0.8 * interval <= med <= 1.3 * interval)
        report["modes"].append(
            {
                "mode": mode,
                "low_power": low_power,
                "sample_count": len(samples),
                "median_interval_s": med,
                "first_temperature_c": samples[0].temperature_c,
                "first_relative_humidity_pct": samples[0].relative_humidity_pct,
            }
        )

    try:
        backend = "usb_hid" if hardware else "simulation"
        service.session.connect(create_sensor(backend, serial_number=serial), sampling=False)
        wait_for(service, lambda: service.session.snapshot().connection == "connected", 12)
        state = service.session.snapshot()
        report["identity"] = asdict(state.identity)
        check("initial_heater_off", not state.heater_on and not state.sampling)
        original_nist = state.identity.nist_id
        command("identity")
        check("identity_stable", service.session.snapshot().identity.nist_id == original_nist)

        command("status")
        report["status_before_clear"] = service.session.snapshot().status_word
        command("clear_status")
        report["status_after_clear"] = service.session.snapshot().status_word
        check("reset_flag_cleared", not (report["status_after_clear"] & 0x0010))

        for low_power in range(4):
            capture("on_demand", low_power, 1, 1.0)
        for mode, interval in (("auto_1hz", 1.0), ("auto_0.5hz", 2.0)):
            for low_power in range(4):
                capture(mode, low_power, 3 if low_power == 0 else 1, interval)

        command("reset")
        state = service.session.snapshot()
        report["status_after_reset"] = state.status_word
        check(
            "reset_defaults",
            state.mode == "on_demand"
            and state.low_power == 0
            and not state.heater_on
            and state.identity.nist_id == original_nist
            and bool(state.status_word & 0x0010),
        )
        command("sample")
        sample = service.snapshot()[-1]
        check("post_reset_pair", sample.mode == "on_demand" and sample.low_power == 0)
        command("clear_status")
        check("post_reset_flag_cleared", not (service.session.snapshot().status_word & 0x0010))
        report["failed_reads"] = service.session.snapshot().failures
        check("no_read_failures", report["failed_reads"] == 0)
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
    parser.add_argument("--hardware", action="store_true", help="Open the approved physical USB EVM")
    parser.add_argument("--serial", help="USB bridge serial, required if several boards are attached")
    parser.add_argument("--output", type=Path, default=Path("recordings"))
    args = parser.parse_args()
    path, report = validate_controls(args.hardware, args.serial, args.output)
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {path}")
    if report["errors"]:
        print("\n".join(report["errors"]))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
