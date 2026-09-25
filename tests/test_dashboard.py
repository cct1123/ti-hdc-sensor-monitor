import csv
import io
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from test_session import wait_for

from app import create_app
from hdcsensor.acquisition import AcquisitionService
from hdcsensor.errors import SensorError
from hdcsensor.models import Sample
from hdcsensor.ui.monitor import _local_time, _plot_range, history_figure


class PlotTests(unittest.TestCase):
    def test_channels_share_time_axis_and_historical_view(self):
        start = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
        samples = [Sample(i, start + timedelta(seconds=i), 20 + i / 10, 40 + i, "TEST") for i in range(5)]
        view = [_local_time(start + timedelta(seconds=i)).isoformat() for i in (1, 3)]
        fig = history_figure(samples, view)
        self.assertEqual(fig.data[0].x, fig.data[1].x)
        self.assertEqual(fig.layout.xaxis.range, fig.layout.xaxis2.range)
        self.assertEqual(fig.layout.xaxis.matches, "x2")
        self.assertEqual(fig.layout.uirevision, "history")
        self.assertEqual(_plot_range(None, {"xaxis2.range": view}), view)
        self.assertIsNone(_plot_range(view, {"xaxis2.autorange": True}))
        self.assertEqual(len(fig.data[0].y), 5)
        self.assertGreater(fig.layout.yaxis.range[0], 20)
        self.assertLess(fig.layout.yaxis.range[1], 20.4)

    def test_empty_and_invalid_range(self):
        self.assertEqual(len(history_figure([]).layout.annotations), 1)
        self.assertIsNone(_plot_range(None, {"xaxis.range": ["bad", "bad"]}))


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.service = AcquisitionService()
        self.addCleanup(self.service.shutdown)
        self.app = create_app(self.service, simulation=True, recording_directory=Path(self.directory.name))
        self.client = self.app.server.test_client()

    def call(self, key_part, changed, overrides=None):
        key = next(k for k in self.app.callback_map if key_part in k)
        callback = self.app.callback_map[key]
        defaults = {
            "command-revision.data": 0,
            "backend.value": "simulation",
            "address.value": "0x44",
            "serial.value": "",
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

        out = callback["output"]
        outputs = (
            [{"id": o.component_id, "property": o.component_property} for o in out]
            if isinstance(out, list)
            else {"id": out.component_id, "property": out.component_property}
        )
        response = self.client.post(
            "/_dash-update-component",
            json={
                "output": key,
                "outputs": outputs,
                "inputs": values(callback["inputs"]),
                "state": values(callback["state"]),
                "changedPropIds": [changed],
            },
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        return response.get_json()["response"]

    def test_http_simulated_flow_plot_record_export_pause_settings_disconnect(self):
        # A failing enumerate sentinel proves this entire app flow never discovers hardware.
        with patch(
            "hdcsensor.usb_hid.USB2ANYHIDTransport.open", side_effect=AssertionError("hardware access")
        ):
            self.assertEqual(self.client.get("/").status_code, 200)
            self.assertEqual(self.client.get("/_dash-layout").status_code, 200)
            self.assertEqual(self.client.get("/_dash-dependencies").status_code, 200)
            self.call("command-revision", "record-start-button.n_clicks")
            self.call("command-revision", "start-button.n_clicks")
            wait_for(lambda: len(self.service.snapshot()) >= 1)
            result = self.call("status-badge", "refresh-timer.n_intervals")
            self.assertIn("°C", result["current-temperature"]["children"])
            self.assertIn("%", result["current-humidity"]["children"])
            self.assertTrue(result["start-button"]["disabled"])
            plot = self.call("history-graph", "refresh-timer.n_intervals")
            self.assertEqual(len(plot["history-graph"]["figure"]["data"]), 2)
            self.call("command-revision", "stop-button.n_clicks")
            wait_for(lambda: not self.service.session.snapshot().sampling)
            self.call("command-revision", "record-stop-button.n_clicks")
            result = self.call("download-csv", "export-button.n_clicks")
            rows = list(csv.DictReader(io.StringIO(result["download-csv"]["data"]["content"])))
            self.assertEqual(len(rows), len(self.service.snapshot()))
            self.assertIn("relative_humidity_pct", rows[0])
            download = self.call("download-csv", "download-button.n_clicks")
            self.assertTrue(download["download-csv"]["data"]["base64"])
            self.call(
                "command-revision",
                "apply-settings.n_clicks",
                {"measurement-mode.value": "auto_1hz", "low-power.value": 3},
            )
            wait_for(lambda: self.service.session.snapshot().low_power == 3)
            page = self.call("monitor-page", "settings-tab.n_clicks")
            self.assertEqual(page["settings-tab"]["aria-selected"], "true")
            self.call("command-revision", "disconnect-button.n_clicks")
            wait_for(lambda: self.service.session.snapshot().connection == "disconnected")

    def test_bad_user_input_is_displayed_without_starting_worker(self):
        result = self.call("command-revision", "start-button.n_clicks", {"sample-interval.value": None})
        self.assertIn("Command failed", result["command-feedback"]["children"])
        self.assertEqual(self.service.session.snapshot().connection, "disconnected")

    def test_auto_csv_starts_with_monitoring_and_closes_on_disconnect(self):
        self.call("command-revision", "start-button.n_clicks")
        wait_for(lambda: len(self.service.snapshot()) >= 2)
        recorder = self.service.recorder.status()
        self.assertTrue(recorder.recording)
        self.assertIsNotNone(recorder.path)
        self.call("command-revision", "stop-button.n_clicks")
        wait_for(lambda: not self.service.session.snapshot().sampling)
        self.assertTrue(self.service.recorder.status().recording)
        self.call("command-revision", "start-button.n_clicks")
        wait_for(lambda: len(self.service.snapshot()) >= 3)
        self.assertEqual(self.service.recorder.status().path, recorder.path)
        self.call("command-revision", "disconnect-button.n_clicks")
        wait_for(lambda: self.service.session.snapshot().connection == "disconnected")
        recorder = self.service.recorder.status()
        self.assertFalse(recorder.recording)
        self.assertEqual(recorder.file_count, 1)
        self.assertEqual(recorder.dropped_rows, 0)
        rows = list(csv.DictReader(io.StringIO(recorder.path.read_text(encoding="utf-8"))))
        self.assertEqual(len(rows), len(self.service.snapshot()))

    def test_auto_csv_opt_out_keeps_manual_record_available(self):
        self.call("command-revision", "start-button.n_clicks", {"auto-record.value": []})
        wait_for(lambda: len(self.service.snapshot()) >= 1)
        self.assertIsNone(self.service.recorder.status().path)
        self.call("command-revision", "record-start-button.n_clicks")
        wait_for(lambda: self.service.recorder.status().recording)
        self.call("command-revision", "disconnect-button.n_clicks")
        wait_for(lambda: self.service.session.snapshot().connection == "disconnected")
        self.assertFalse(self.service.recorder.status().recording)
        self.assertTrue(self.service.recorder.status().path.exists())

    def test_failed_connection_creates_no_auto_csv(self):
        with patch("hdcsensor.simulation.SimulatedTransport.open", side_effect=SensorError("unavailable")):
            self.call("command-revision", "start-button.n_clicks")
            wait_for(lambda: self.service.session.snapshot().connection == "error")
        self.assertIsNone(self.service.recorder.status().path)
        self.assertEqual(list(Path(self.directory.name).glob("*.csv")), [])

    def test_auto_csv_drains_after_measurement_error(self):
        self.call("command-revision", "start-button.n_clicks")
        wait_for(lambda: len(self.service.snapshot()) >= 1)
        with (
            patch.object(self.service.session, "_period", return_value=0.01),
            patch("hdcsensor.simulation.SimulatedTransport.read", side_effect=SensorError("unplugged")),
        ):
            wait_for(lambda: self.service.session.snapshot().connection == "error")
        recorder = self.service.recorder.status()
        self.assertFalse(recorder.recording)
        self.assertTrue(recorder.path.exists())
        self.assertEqual(recorder.rows_written, len(self.service.snapshot()))

    def test_heater_acknowledgement_and_soft_reset_callbacks(self):
        self.call("command-revision", "connect-button.n_clicks")
        wait_for(lambda: self.service.session.snapshot().connection == "connected")
        result = self.call("command-revision", "heater-request.n_clicks")
        self.assertIn("Acknowledge", result["command-feedback"]["children"])
        self.assertFalse(self.service.session.snapshot().heater_on)
        self.call("command-revision", "heater-request.n_clicks", {"heater-ack.value": ["ack"]})
        wait_for(lambda: self.service.session.snapshot().heater_on)
        self.call("command-revision", "heater-off.n_clicks")
        wait_for(lambda: not self.service.session.snapshot().heater_on)
        self.call("command-revision", "reset-request.n_clicks")
        wait_for(lambda: "Soft reset complete" in self.service.session.snapshot().note)
