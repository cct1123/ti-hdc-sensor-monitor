# TI HDC Sensor Monitor

Local Python dashboard for the **TI HDC3020EVM**: paired temperature and relative
humidity, live synchronized plots, statistics, CSV logging and basic sensor controls.
Modeled on [ti-tmp-sensor-monitor](https://github.com/cct1123/ti-tmp-sensor-monitor)
using the same Dash interface conventions and single-session architecture.

**Status:** software-tested candidate; physical HDC3020EVM validation is pending.
See [the candidate report](outputs/REPORT.md) and [current checkpoint](STATE.md).

## Quick start

Install [uv](https://docs.astral.sh/uv/), then in this directory:

```powershell
uv sync --extra usb
uv run --extra usb python app.py
```

Open **http://127.0.0.1:8050**. Close TI's EVM GUI, connect one stock HDC3020EVM,
leave USB / USB2ANY HID and address `0x44` selected, and click **Start monitoring**.
The terminal must remain running. Hardware integration by an engineering agent
follows the candidate approval gate in AGENTS.md.

For a preview without a board:

```powershell
uv run python app.py --simulate
```

Then click **Start monitoring**. Simulation is explicitly labeled in the dashboard
and every CSV row. It does not import, enumerate or open HID devices.
The switch preselects simulation; choosing USB later is an explicit physical connection.

Alternative installation, using Python 3.9 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install "dash>=2.18,<4" "hidapi>=0.15,<1"
.\.venv\Scripts\python app.py
```

The USB backend supports 64-bit Python through hidapi; it does not require
`USB2ANY.dll`, TI Cloud Agent, or TI's GUI. Installation downloads dependencies;
monitoring serves assets locally and binds only to loopback. Run one app process
per board. All browser tabs share that process's device session and recorder.

## Monitor and record

- **Connect** opens and identifies the device without sampling. It establishes
  on-demand LPM0 with the heater off; these are volatile changes.
- **Start monitoring** connects automatically or resumes. The default is a fresh
  paired conversion each second. **Stop** pauses host acquisition; **Disconnect**
  turns the heater off, exits auto mode and releases the board.
- Live values show the last sample timestamp. Disconnected/paused readings are
  explicitly marked as retained. Statistics cover the entire 7,200-sample buffer.
- The two plots share their time range. Drag or zoom either plot; **Follow live**
  returns to the last five minutes. **Clear data** clears only the in-memory buffer.
- **Record** saves new samples into `recordings/`. Earlier samples are available
  through **Export buffer**. Logging can remain enabled across sampling pauses.
- **Stop recording** drains accepted rows. **Download last CSV** becomes available
  after the writer finishes. Dropped rows and disk errors remain visible.

CSV columns: `timestamp_utc`, `sequence`, `temperature_c`, `relative_humidity_pct`,
`source`, `raw_temperature`, `raw_humidity`, `mode`, `low_power`, `heater_on`.
Plots use the computer's local time; CSV uses UTC. Heater-on readings remain in
statistics and are marked with orange plot markers and `heater_on=1`.

## Device settings

Both pages remain mounted: changing tabs preserves plots, data, recording and draft controls.
The **Applied** line describes the active configuration; dropdowns are editable drafts.

- Measurement mode: on-demand, auto 1 Hz, or auto 0.5 Hz. The latter is read at
  intervals of at least 2.02 seconds to avoid fetching an empty latch.
- LPM0 through LPM3 select the noise/power tradeoff. Settings apply on the device worker.
- **Take one sample** works while paused in on-demand mode.
- Status read/clear, manufacturer ID (`0x3000` for TI), 48-bit NIST serial, and soft reset.
  HDC3020 has no separate model-ID command in the documented command table; the UI does
  not relabel the manufacturer word as an HDC-specific part ID.
- A confirmed **5 s low-level heater pulse** uses the minimum element (`0x0001`);
  **Heater off** disables it immediately when the worker handles the command.
  Heat changes both measurements, including during cooldown. The host timer is
  best-effort, not a firmware watchdog. If communication fails, unplug the EVM.
- Soft reset restores this app's on-demand LPM0 configuration with heater off.
  EEPROM, offsets, thresholds, firmware and general-call reset are not exposed.

In auto mode, **Stop** pauses reads while the device continues autonomous conversions.
Choose on-demand mode or Disconnect to stop autonomous conversion.

## Errors and troubleshooting

Missing/multiple boards, permissions, I2C NAKs, malformed HID replies, transport CRC,
sensor CRC and short replies produce explicit errors. Specify the USB serial if
several compatible EVMs are attached. Close other software that owns the board.

Bad measurements are discarded as a pair. A transient failure can recover on the
next scheduled read; three consecutive failures close the session. A failed control
operation disconnects immediately because a timed-out write may have taken effect.
Reconnect explicitly to re-establish known state. Cleanup failures are reported;
do not assume a failed heater-off command succeeded.

No board found despite a working TI GUI may indicate a different VID/PID or firmware.
Capture its identity and compare with [the protocol assumptions](docs/protocol.md)
before changing transport behavior. Do not flash firmware as a troubleshooting shortcut.

## Verification

```powershell
uv sync --extra usb --extra dev
uv run python -m unittest discover -s tests -v
uv run ruff check app.py hdcsensor tests
uv run python -m hdcsensor.validate --samples 30
```

The last command runs a bounded **simulation** acquisition/CSV/reopen check and writes
a JSON report. Tests use fakes, including HID framing and error injection; none discover hardware.

After candidate approval, close or Disconnect the dashboard and run:

```powershell
uv run --extra usb python -m hdcsensor.validate --hardware --samples 30 --interval 1
```

Add `--serial <USB-serial>` if needed. This explicitly opens hardware, reads identity,
initializes measurement mode/heater-off, logs samples, closes and reopens the board.
It does not enable the heater. See [physical validation](docs/hardware-validation.md)
for the exact sequence, manual control checks and cleanup.

## Project continuity

Read [PROJECT.md](PROJECT.md) for intent, [STATE.md](STATE.md) for current evidence
and next action, and [AGENTS.md](AGENTS.md) for the engineering loop/review gate.
[Architecture](ARCHITECTURE.md) explains ownership; [NOTICE.md](NOTICE.md) records reuse.
Licensed under [MIT](LICENSE).
