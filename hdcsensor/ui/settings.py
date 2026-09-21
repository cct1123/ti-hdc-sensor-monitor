"""Basic HDC3020 volatile settings; sensor access is queued by app callbacks."""

from dash import dcc, html


def button(label, identity, style="secondary"):
    return html.Button(label, id=identity, className=f"button {style}")


def settings_layout():
    return html.Section(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("HDC3020", className="section-kicker"),
                            html.H2("Device settings"),
                            html.P(
                                "Temporary controls for the connected session. Applied settings appear below."
                            ),
                        ]
                    )
                ],
                className="settings-heading",
            ),
            html.Div(id="settings-feedback", className="feedback", **{"aria-live": "polite"}),
            html.Div(
                [
                    html.Section(
                        [
                            html.Div("ACQUISITION", className="section-kicker"),
                            html.H3("Measurement settings"),
                            html.Div(
                                [
                                    html.Label("Measurement mode", htmlFor="measurement-mode"),
                                    dcc.Dropdown(
                                        id="measurement-mode",
                                        value="on_demand",
                                        clearable=False,
                                        options=[
                                            {
                                                "label": "On demand · fresh conversion per sample",
                                                "value": "on_demand",
                                            },
                                            {"label": "Automatic · 1 Hz", "value": "auto_1hz"},
                                            {"label": "Automatic · 0.5 Hz", "value": "auto_0.5hz"},
                                        ],
                                    ),
                                ],
                                className="field-shell",
                            ),
                            html.Div(
                                [
                                    html.Label("Low-power mode", htmlFor="low-power"),
                                    dcc.Dropdown(
                                        id="low-power",
                                        value=0,
                                        clearable=False,
                                        options=[
                                            {"label": label, "value": value}
                                            for value, label in enumerate(
                                                ["LPM0 · lowest noise", "LPM1", "LPM2", "LPM3 · lowest power"]
                                            )
                                        ],
                                    ),
                                ],
                                className="field-shell",
                            ),
                            html.P(
                                "Lower-power modes trade measurement noise for shorter conversions. "
                                "Automatic 0.5 Hz reads at most every 2.02 s.",
                                className="field-hint",
                            ),
                            html.Div(
                                [
                                    button("Apply measurement settings", "apply-settings", "primary"),
                                    button("Take one sample", "single-sample"),
                                ],
                                className="button-row",
                            ),
                            html.Div(id="applied-settings", className="field-hint"),
                        ],
                        className="panel settings-card",
                    ),
                    html.Section(
                        [
                            html.Div("DEVICE", className="section-kicker"),
                            html.H3("Status & identity"),
                            html.Pre(id="device-details", className="device-details"),
                            html.Div(
                                [
                                    button("Read status", "read-status"),
                                    button("Clear status", "clear-status"),
                                    button("Read device / NIST ID", "read-identity"),
                                ],
                                className="button-row",
                            ),
                            html.P(
                                "Device identity shows TI's manufacturer ID and the sensor's 48-bit NIST serial. "
                                "Clear status clears tracking/reset flags.",
                                className="field-hint",
                            ),
                            button("Soft reset", "reset-request"),
                            html.P("Reset restores on-demand LPM0 with heater off.", className="field-hint"),
                        ],
                        className="panel settings-card",
                    ),
                    html.Section(
                        [
                            html.Div("HEATER", className="section-kicker"),
                            html.H3("Condensation control"),
                            html.P(
                                "Heating changes both temperature and RH. Heated samples are marked in the plot and CSV. "
                                "Allow the sensor to cool before interpreting ambient readings.",
                                className="panel-description",
                            ),
                            html.Div(id="heater-state", className="status"),
                            dcc.Checklist(
                                id="heater-ack",
                                value=[],
                                options=[
                                    {
                                        "label": " I understand this heats the sensor and affects readings.",
                                        "value": "ack",
                                    }
                                ],
                                className="heater-acknowledgement",
                            ),
                            html.Div(
                                [
                                    button("5 s low-level pulse", "heater-request"),
                                    button("Heater off", "heater-off"),
                                ],
                                className="button-row",
                            ),
                            html.P(
                                "The app times the pulse and disables the heater on orderly disconnect. "
                                "If USB communication fails, unplug the board to ensure heater power is removed.",
                                className="field-hint",
                            ),
                        ],
                        className="panel settings-card",
                    ),
                ],
                className="settings-grid",
            ),
        ],
        id="settings-page",
        className="settings-page is-hidden",
        role="tabpanel",
        **{"aria-labelledby": "settings-tab"},
    )
