"""Local Dash dashboard for TI HDC3020EVM; no hardware is touched on import/startup."""

from __future__ import annotations

import argparse
import atexit
from pathlib import Path

from dash import Dash, Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate

from hdcsensor.acquisition import AcquisitionService
from hdcsensor.protocol import status_labels
from hdcsensor.recording import export_csv
from hdcsensor.sensors import create_sensor
from hdcsensor.ui.monitor import _local_time, _metric_card, _plot_range, history_figure
from hdcsensor.ui.settings import button, settings_layout

PROJECT_ROOT = Path(__file__).resolve().parent
RECORDING_DIRECTORY = PROJECT_ROOT / "recordings"


def field(label, identity, component):
    return html.Div([html.Label(label, htmlFor=identity), component], className="field-shell")


def live_value(label, identity):
    return html.Div(
        [html.Div(label, className="current-label"), html.Div("--", id=identity, className="current-value")]
    )


def layout(simulation=False):
    return html.Div(
        [
            dcc.Store(id="command-revision", data=0),
            dcc.Store(id="plot-view"),
            dcc.Interval(id="refresh-timer", interval=750),
            dcc.Download(id="download-csv"),
            html.Header(
                [
                    html.Div(
                        [
                            html.Div("H", className="brand-mark"),
                            html.Div(
                                [
                                    html.Div("LAB INSTRUMENTATION", className="eyebrow"),
                                    html.H1("TI HDC Sensor Monitor"),
                                    html.P("Temperature & relative humidity · HDC3020EVM"),
                                ]
                            ),
                        ],
                        className="brand",
                    ),
                    html.Div(
                        [
                            html.Div("Disconnected", id="status-badge", className="status"),
                            html.Div(
                                "Local device session", id="connection-identity", className="session-label"
                            ),
                        ],
                        className="header-status",
                    ),
                ],
                className="app-header",
            ),
            html.Div(
                [
                    html.Nav(
                        [
                            html.Button(
                                "Monitor",
                                id="monitor-tab",
                                className="page-tab active",
                                role="tab",
                                **{"aria-selected": "true", "aria-controls": "monitor-page"},
                            ),
                            html.Button(
                                "Device settings",
                                id="settings-tab",
                                className="page-tab",
                                role="tab",
                                **{"aria-selected": "false", "aria-controls": "settings-page"},
                            ),
                        ],
                        className="page-tabs",
                        role="tablist",
                        **{"aria-label": "Workspace pages"},
                    ),
                    html.Div(
                        [
                            html.Span("Disconnected", id="connection-state", className="connection-state"),
                            button("Connect", "connect-button"),
                            button("Disconnect", "disconnect-button", "ghost"),
                        ],
                        className="connection-controls",
                    ),
                ],
                className="workspace-toolbar",
            ),
            html.Main(
                [
                    html.Section(
                        [
                            html.Div("DEVICE SETUP", className="section-kicker"),
                            html.H2("Connect your sensor"),
                            html.P(
                                "Start monitoring connects and samples. Stop pauses sampling and keeps the device connected.",
                                className="panel-description",
                            ),
                            field(
                                "Connection",
                                "backend",
                                dcc.Dropdown(
                                    id="backend",
                                    clearable=False,
                                    value="simulation" if simulation else "usb_hid",
                                    options=[
                                        {"label": "USB / USB2ANY HID", "value": "usb_hid"},
                                        {"label": "Simulation · no hardware", "value": "simulation"},
                                    ],
                                ),
                            ),
                            html.Div(
                                "Close TI's GUI before connecting. Stock EVM address: 0x44.",
                                className="field-hint",
                            ),
                            field(
                                "I²C address",
                                "address",
                                dcc.Dropdown(
                                    id="address",
                                    value="0x44",
                                    clearable=False,
                                    options=[
                                        {"label": f"0x{x:02X}", "value": f"0x{x:02X}"}
                                        for x in range(0x44, 0x48)
                                    ],
                                ),
                            ),
                            field(
                                "USB serial (optional)",
                                "serial",
                                dcc.Input(
                                    id="serial",
                                    type="text",
                                    placeholder="Required if several EVMs are connected",
                                    value="",
                                ),
                            ),
                            field(
                                "Sample interval (s)",
                                "sample-interval",
                                dcc.Input(
                                    id="sample-interval", type="number", value=1, min=1, max=60, step=0.1
                                ),
                            ),
                            dcc.Checklist(
                                id="auto-record",
                                options=[
                                    {
                                        "label": "Save CSV automatically while monitoring",
                                        "value": "enabled",
                                    }
                                ],
                                value=["enabled"],
                                className="auto-record-option",
                            ),
                            html.Div(
                                "A new file starts with the first sample of each UTC day. Uncheck for a quick view without saving.",
                                className="field-hint",
                            ),
                            html.Div(
                                [
                                    button("Start monitoring", "start-button", "primary button-main"),
                                    button("Stop", "stop-button"),
                                    button("Clear data", "clear-button", "ghost"),
                                ],
                                className="button-row",
                            ),
                            html.Div(id="command-feedback", className="feedback", **{"aria-live": "polite"}),
                            html.Div(id="session-note", className="field-hint"),
                            html.Div(
                                id="error-message", className="error-message", **{"aria-live": "assertive"}
                            ),
                        ],
                        className="panel controls-panel",
                    ),
                    html.Section(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("LIVE READINGS", className="current-label"),
                                            html.Div(
                                                "No samples yet", id="current-time", className="current-time"
                                            ),
                                        ],
                                        className="current-topline",
                                    ),
                                    html.Div(
                                        [
                                            live_value("TEMPERATURE", "current-temperature"),
                                            live_value("RELATIVE HUMIDITY", "current-humidity"),
                                        ],
                                        className="paired-readings",
                                    ),
                                    html.Div(id="acquisition-note", className="live-note"),
                                ],
                                className="current-card",
                            ),
                            html.Div(
                                [
                                    _metric_card("Temp min / mean / max", "temperature-stats"),
                                    _metric_card("RH min / mean / max", "humidity-stats"),
                                    _metric_card("Buffered samples", "sample-count", "0"),
                                    _metric_card("Failed reads", "failure-count", "0"),
                                ],
                                className="metrics-grid hdc-metrics",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("TREND", className="section-kicker"),
                                            html.H2("Temperature & humidity history"),
                                            html.P(
                                                "Drag either plot to browse; scroll to zoom. Both time axes stay synchronized.",
                                                className="plot-description",
                                            ),
                                            button("Follow live · 5 min", "follow-live-button", "ghost"),
                                            html.Span(
                                                "Live · last 5 minutes",
                                                id="plot-view-label",
                                                className="field-hint",
                                            ),
                                        ],
                                        className="plot-heading",
                                    ),
                                    dcc.Graph(
                                        id="history-graph",
                                        style={"height": "500px"},
                                        figure=history_figure([]),
                                        config={
                                            "displaylogo": False,
                                            "modeBarButtonsToRemove": [
                                                "sendChartToCloud",
                                                "sendDataToCloud",
                                                "select2d",
                                                "lasso2d",
                                            ],
                                            "responsive": True,
                                            "scrollZoom": True,
                                            "displayModeBar": "hover",
                                            "doubleClick": "autosize",
                                        },
                                    ),
                                    html.Div(
                                        "Statistics cover the whole buffer. Orange markers indicate heater-on samples.",
                                        className="field-hint plot-footnote",
                                    ),
                                ],
                                className="panel plot-panel",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("DATA CAPTURE", className="section-kicker"),
                                            html.H2("CSV recording"),
                                            html.Div(
                                                "Not recording",
                                                id="recording-status",
                                                className="recording-status",
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            button("Record", "record-start-button", "primary"),
                                            button("Stop recording", "record-stop-button"),
                                            button("Download last CSV", "download-button", "ghost"),
                                            button("Export buffer", "export-button", "ghost"),
                                        ],
                                        className="recording-controls",
                                    ),
                                ],
                                className="panel recording-panel",
                            ),
                        ],
                        className="monitor-column",
                    ),
                ],
                id="monitor-page",
                className="app-grid",
                role="tabpanel",
                **{"aria-labelledby": "monitor-tab"},
            ),
            settings_layout(),
        ],
        className="app-shell",
    )


def create_app(service=None, simulation=False, recording_directory=RECORDING_DIRECTORY):
    service = service or AcquisitionService()
    app = Dash(
        __name__, title="TI HDC Sensor Monitor", update_title=None, assets_folder=str(PROJECT_ROOT / "assets")
    )
    app.layout = lambda: layout(simulation)
    app.monitor_service = service

    command_inputs = [
        (x, "n_clicks")
        for x in (
            "start-button",
            "stop-button",
            "connect-button",
            "disconnect-button",
            "clear-button",
            "record-start-button",
            "record-stop-button",
            "apply-settings",
            "single-sample",
            "read-status",
            "clear-status",
            "read-identity",
            "heater-off",
            "heater-request",
            "reset-request",
        )
    ]

    @app.callback(
        Output("command-revision", "data"),
        Output("command-feedback", "children"),
        [Input(*item) for item in command_inputs],
        [
            State("command-revision", "data"),
            State("backend", "value"),
            State("address", "value"),
            State("serial", "value"),
            State("sample-interval", "value"),
            State("auto-record", "value"),
            State("measurement-mode", "value"),
            State("low-power", "value"),
            State("heater-ack", "value"),
        ],
        prevent_initial_call=True,
    )
    def handle_command(*args):
        revision, backend, address, serial, interval, auto_record, mode, lp, heater_ack = args[-9:]
        trigger = ctx.triggered_id
        revision = (revision or 0) + 1
        try:
            if trigger in ("start-button", "connect-button"):
                sensor = create_sensor(backend, address, serial)
                if trigger == "start-button":
                    service.start(
                        sensor,
                        interval,
                        auto_record="enabled" in (auto_record or []),
                        recording_directory=recording_directory,
                    )
                else:
                    service.session.connect(sensor, interval)
                message = "Device request queued."
            elif trigger == "disconnect-button":
                service.session.disconnect()
                message = "Disconnect requested."
            elif trigger == "clear-button":
                service.clear_samples()
                message = "Buffer cleared; CSV recordings are retained."
            elif trigger == "record-start-button":
                path = service.recorder.start(recording_directory, "hdc3020")
                message = f"Recording new samples to {path.name}."
            elif trigger == "record-stop-button":
                service.recorder.stop()
                message = "Recording stopped; check the writer status below."
            else:
                if trigger == "heater-request" and "ack" not in (heater_ack or []):
                    raise ValueError("Acknowledge the heating effect before requesting a heater pulse")
                operations = {
                    "stop-button": "pause",
                    "apply-settings": "configure",
                    "single-sample": "sample",
                    "read-status": "status",
                    "clear-status": "clear_status",
                    "read-identity": "identity",
                    "heater-off": "heater_off",
                    "heater-request": "heater_pulse",
                    "reset-request": "reset",
                }
                kwargs = {"mode": mode, "low_power": lp} if trigger == "apply-settings" else {}
                service.session.submit(operations[trigger], **kwargs)
                message = "Command queued; completion is shown in session status."
        except Exception as exc:
            message = f"Command failed: {exc}"
        return revision, message

    outputs = [
        (x, "children")
        for x in (
            "status-badge",
            "connection-identity",
            "connection-state",
            "current-temperature",
            "current-humidity",
            "current-time",
            "acquisition-note",
            "temperature-stats",
            "humidity-stats",
            "sample-count",
            "failure-count",
            "recording-status",
            "error-message",
            "session-note",
            "settings-feedback",
            "applied-settings",
            "device-details",
            "heater-state",
        )
    ]
    outputs += [("status-badge", "className")]
    disabled_ids = [
        "start-button",
        "stop-button",
        "connect-button",
        "disconnect-button",
        "backend",
        "address",
        "serial",
        "sample-interval",
        "auto-record",
        "record-start-button",
        "record-stop-button",
        "download-button",
        "export-button",
        "apply-settings",
        "single-sample",
        "read-status",
        "clear-status",
        "read-identity",
        "reset-request",
        "heater-request",
        "heater-off",
    ]
    outputs += [(x, "disabled") for x in disabled_ids]

    @app.callback(
        [Output(*item) for item in outputs],
        Input("refresh-timer", "n_intervals"),
        Input("command-revision", "data"),
        Input("heater-ack", "value"),
    )
    def refresh(_ticks, _revision, heater_ack):
        device, samples, recorder = service.session.snapshot(), service.snapshot(), service.recorder.status()
        connected = device.connection == "connected"
        busy = device.connection in ("connecting", "disconnecting")
        live = connected and device.sampling
        state = "Monitoring" if live else device.connection.title()
        identity = device.identity
        source = identity.source if identity else "Local device session"
        current_t = f"{samples[-1].temperature_c:.3f} °C" if samples else "--"
        current_rh = f"{samples[-1].relative_humidity_pct:.3f} %" if samples else "--"
        timestamp = (
            _local_time(samples[-1].timestamp_utc).strftime("%Y-%m-%d %H:%M:%S local")
            if samples
            else "No samples"
        )

        def stats(field, unit):
            values = [getattr(sample, field) for sample in samples]
            return (
                f"{min(values):.2f} / {sum(values) / len(values):.2f} / {max(values):.2f} {unit}"
                if values
                else "--"
            )

        recording = "Not recording"
        if recorder.path:
            action = "Writer error" if recorder.last_error else "Recording" if recorder.recording else "Saved"
            recording = (
                f"{action}: {recorder.path.name} · {recorder.rows_written} total rows "
                f"across {recorder.file_count} file(s) · {recorder.dropped_rows} dropped"
            )
        errors = " · ".join(x for x in (device.last_error, recorder.last_error) if x)
        details = "Connect to read device identity and status."
        if identity:
            flags = ", ".join(status_labels(device.status_word or 0)) or "No flags"
            details = (
                f"Source: {identity.source}\nUSB serial: {identity.serial_number}\n"
                f"Bridge firmware: {identity.firmware_version}\nI²C: 0x{identity.address:02X}\n"
                f"TI manufacturer ID: 0x{identity.manufacturer_id:04X}\nNIST serial: {identity.nist_id}\n"
                f"Last status: 0x{device.status_word or 0:04X}\n{flags}"
            )
        note = f"{source} · {'Acquiring' if live else 'Last reading retained'} · {device.interval_s:g} s requested interval"
        if device.heater_on:
            note += " · HEATER ON"
        path_ready = recorder.path is not None and recorder.path.exists() and not recorder.recording
        values = [
            state,
            source,
            device.connection.title(),
            current_t,
            current_rh,
            timestamp,
            note,
            stats("temperature_c", "°C"),
            stats("relative_humidity_pct", "%"),
            str(len(samples)),
            str(device.failures),
            recording,
            errors,
            device.note,
            errors or device.note,
            f"Applied: {device.mode}, LPM{device.low_power} (this session)",
            details,
            "Heater ON · readings affected" if device.heater_on else "Heater off",
            "status status-" + ("running" if live else "error" if errors else "stopped"),
        ]
        disabled = [
            live or busy,
            not live,
            connected or busy,
            not (connected or device.connection == "connecting"),
            connected or busy,
            connected or busy,
            connected or busy,
            live or busy,
            connected or busy,
            recorder.recording,
            not recorder.recording,
            not path_ready,
            not bool(samples),
            not connected,
            not connected or live or device.mode != "on_demand",
            not connected,
            not connected,
            not connected,
            not connected,
            not connected or device.heater_on or "ack" not in (heater_ack or []),
            not connected,
        ]
        return values + disabled

    @app.callback(
        Output("history-graph", "figure"),
        Output("plot-view", "data"),
        Output("plot-view-label", "children"),
        Input("refresh-timer", "n_intervals"),
        Input("history-graph", "relayoutData"),
        Input("follow-live-button", "n_clicks"),
        Input("clear-button", "n_clicks"),
        State("plot-view", "data"),
    )
    def refresh_plot(_ticks, relayout, _follow, _clear, view):
        view = _plot_range(
            view,
            relayout if ctx.triggered_id == "history-graph" else None,
            reset=ctx.triggered_id in ("follow-live-button", "clear-button"),
        )
        return (
            history_figure(service.snapshot(), view),
            view,
            "History · view held" if view else "Live · last 5 minutes",
        )

    @app.callback(
        Output("download-csv", "data"),
        Input("download-button", "n_clicks"),
        Input("export-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def download(_last, _buffer):
        if ctx.triggered_id == "export-button":
            return dcc.send_string(export_csv(service.snapshot()), "hdc3020-buffer.csv")
        recorder = service.recorder.status()
        if recorder.recording or recorder.path is None or not recorder.path.exists():
            raise PreventUpdate
        return dcc.send_file(str(recorder.path))

    @app.callback(
        Output("monitor-page", "className"),
        Output("settings-page", "className"),
        Output("monitor-tab", "className"),
        Output("settings-tab", "className"),
        Output("monitor-tab", "aria-selected"),
        Output("settings-tab", "aria-selected"),
        Input("monitor-tab", "n_clicks"),
        Input("settings-tab", "n_clicks"),
        prevent_initial_call=True,
    )
    def switch_page(_monitor, _settings):
        settings = ctx.triggered_id == "settings-tab"
        return (
            "app-grid is-hidden" if settings else "app-grid",
            "settings-page" if settings else "settings-page is-hidden",
            "page-tab" if settings else "page-tab active",
            "page-tab active" if settings else "page-tab",
            "false" if settings else "true",
            "true" if settings else "false",
        )

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulate", action="store_true", help="Preselect simulation; no hardware access")
    parser.add_argument("--port", type=int, default=8050)
    args = parser.parse_args()
    service = AcquisitionService()
    app = create_app(service, simulation=args.simulate)
    atexit.register(service.shutdown)
    try:
        app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True, use_reloader=False)
    finally:
        service.shutdown()


if __name__ == "__main__":
    main()
