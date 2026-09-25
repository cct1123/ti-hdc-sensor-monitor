"""Exercise Dash callbacks with a real session; physical USB requires --hardware."""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from app import create_app

from .acquisition import AcquisitionService
from .validate import wait_for


def validate_dashboard(hardware=False, serial=None, output=Path("recordings")):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    backend = "usb_hid" if hardware else "simulation"
    report = {
        "backend": backend,
        "physical_validation": hardware,
        "passed": False,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "errors": [],
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = output / f"dashboard_{stamp}.json"
    service = AcquisitionService()
    app = create_app(service, simulation=not hardware, recording_directory=output)
    client = app.server.test_client()

    def check(name, condition):
        report["checks"][name] = bool(condition)
        if not condition:
            raise AssertionError(name)

    def callback(key_part, changed, overrides=None):
        key = next(key for key in app.callback_map if key_part in key)
        entry = app.callback_map[key]
        defaults = {
            "command-revision.data": 0,
            "backend.value": backend,
            "address.value": "0x44",
            "serial.value": serial or "",
            "sample-interval.value": 1,
            "auto-record.value": ["enabled"],
            "measurement-mode.value": "on_demand",
            "low-power.value": 0,
        }
        defaults.update(overrides or {})

        def values(items):
            return [
                dict(
                    item,
                    value=defaults.get(
                        item["id"] + "." + item["property"],
                        1 if item["property"] in ("n_clicks", "n_intervals") else None,
                    ),
                )
                for item in items
            ]

        outputs = entry["output"]
        outputs = (
            [{"id": item.component_id, "property": item.component_property} for item in outputs]
            if isinstance(outputs, list)
            else {"id": outputs.component_id, "property": outputs.component_property}
        )
        response = client.post(
            "/_dash-update-component",
            json={
                "output": key,
                "outputs": outputs,
                "inputs": values(entry["inputs"]),
                "state": values(entry["state"]),
                "changedPropIds": [changed],
            },
        )
        if response.status_code != 200:
            raise RuntimeError(f"Dash callback {changed}: HTTP {response.status_code}")
        return response.get_json()["response"]

    try:
        check(
            "http_routes",
            all(
                client.get(route).status_code == 200
                for route in ("/", "/_dash-layout", "/_dash-dependencies")
            ),
        )
        callback("command-revision", "record-start-button.n_clicks")
        callback("command-revision", "start-button.n_clicks")
        wait_for(service, lambda: len(service.snapshot()) >= 3, 12)
        state = service.session.snapshot()
        report["identity"] = vars(state.identity)
        check("physical_session", state.connection == "connected" and state.sampling and not state.heater_on)
        values = callback("status-badge", "refresh-timer.n_intervals")
        check(
            "paired_live_values",
            "°C" in values["current-temperature"]["children"]
            and "%" in values["current-humidity"]["children"],
        )
        graph = callback("history-graph", "refresh-timer.n_intervals")["history-graph"]["figure"]
        check("paired_plots", len(graph["data"]) == 2 and graph["data"][0]["x"] == graph["data"][1]["x"])

        callback("command-revision", "stop-button.n_clicks")
        wait_for(service, lambda: not service.session.snapshot().sampling, 3)
        callback("command-revision", "record-stop-button.n_clicks")
        samples = service.snapshot()
        recorder = service.recorder.status()
        report["sample_count"] = len(samples)
        report["csv"] = str(recorder.path)
        check(
            "recording_drained",
            not recorder.recording and not recorder.last_error and recorder.dropped_rows == 0,
        )
        with recorder.path.open(newline="", encoding="utf-8") as stream:
            disk_rows = list(csv.DictReader(stream))
        check("recorded_pairs", len(disk_rows) == len(samples) and len(samples) >= 3)
        exported = callback("download-csv", "export-button.n_clicks")["download-csv"]["data"]
        export_rows = list(csv.DictReader(io.StringIO(exported["content"])))
        check("buffer_export", len(export_rows) == len(samples))
        downloaded = callback("download-csv", "download-button.n_clicks")["download-csv"]["data"]
        downloaded_rows = list(csv.DictReader(io.StringIO(base64.b64decode(downloaded["content"]).decode())))
        check("saved_csv_download", downloaded_rows == disk_rows)

        callback(
            "command-revision",
            "apply-settings.n_clicks",
            {"measurement-mode.value": "auto_1hz", "low-power.value": 1},
        )
        wait_for(service, lambda: service.session.snapshot().low_power == 1, 3)
        check("settings_applied", service.session.snapshot().mode == "auto_1hz")
        page = callback("monitor-page", "settings-tab.n_clicks")
        check("settings_page", page["settings-tab"]["aria-selected"] == "true")
        callback("command-revision", "disconnect-button.n_clicks")
        wait_for(service, lambda: service.session.snapshot().connection == "disconnected", 8)
        check("clean_disconnect", not service.session.snapshot().heater_on)
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
    path, report = validate_dashboard(args.hardware, args.serial, args.output)
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {path}")
    if report["errors"]:
        print("\n".join(report["errors"]))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
