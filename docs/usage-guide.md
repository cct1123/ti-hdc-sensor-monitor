# Usage guide

Follow **Start monitoring → inspect readings and CSV → adjust settings →
Disconnect**.

For the shortest first-use path, see the [quick start](quick-start.md). The
settings screenshot uses this application's simulator; its identity values are
fixtures. Physical acquisition, manual CSV, the live dashboard and volatile
controls passed on HDC3020EVMs, while automatic CSV still awaits a physical
check. See the [validation report](../outputs/REPORT.md).

## 1. Inspect the monitor

Start with the [quick start](quick-start.md), then watch the temperature/RH
pair update about once a second. The header shows the current connection state.

Check these four places:

1. **Source and connection** identify which backend is active.
2. **Live readings and timestamp** show the latest complete temperature/RH pair.
3. **Buffered samples / Failed reads** show acquisition progress and errors.
4. **CSV recording** shows whether new samples are being saved.

Statistics cover the whole buffer. Up to 7,200 pairs are retained, about two hours
at the default interval; older pairs roll out as new ones arrive. **Clear data** clears
the buffer and statistics but does not remove recordings.

**Connect** identifies the board and selects on-demand LPM0 with heater off;
**Start monitoring** begins acquisition and, by default, CSV capture. Leave
the optional heater off during normal monitoring; the [hardware validation
procedure](hardware-validation.md) describes its earlier bounded test.

## 2. Browse history and return to live

The upper plot shows temperature and the lower plot shows relative humidity.
Their time axes remain synchronized, so changes can be compared at the same instant.

1. Drag either plot horizontally to browse earlier samples.
2. Scroll over a plot to zoom, or use its **Zoom in / Zoom out** toolbar controls.
3. Look for **History · view held**. Acquisition continues, but the selected time
   range stays fixed while new samples arrive.
4. Click **Follow live · 5 min** to restore the latest five-minute view.

**History · view held** identifies a selected range. Both plots use the same
time range; statistics still describe the entire buffer.

**Stop** pauses acquisition. The last values and timestamp remain visible, labeled
as retained. **Start monitoring** resumes. In auto mode, Stop pauses host reads only;
the sensor keeps converting until on-demand mode is selected or you Disconnect.

## 3. Record and export CSV

By default, **Start monitoring** begins CSV capture after a successful connection.
New samples go to a timestamped file such as
`recordings/hdc3020_YYYYMMDD_HHMMSS_ffffff.csv`. The writer starts a new file
on the first accepted sample of each UTC day. Earlier daily files remain in
`recordings/`; samples from before recording began are not backfilled.

Uncheck **Save CSV automatically while monitoring** before starting for a quick
view without a file. You can still click **Record** to begin a manual capture;
manual recordings stay in one file until stopped.
If you click **Stop recording** while monitoring continues, later samples are
not saved until **Record** or the next **Start monitoring**. **Stop** pauses
sampling but keeps an active recording open for resume; **Disconnect** drains
and closes it.

Click **Stop recording** to finish the file. The writer drains accepted rows before
**Download last CSV** becomes available. Confirm **Saved**, the written-row count,
and **0 dropped** before using the recording.

| Action | Data included | Effect on recording |
| --- | --- | --- |
| **Start monitoring** with auto-save checked | New samples after successful connection | Starts a daily-rotated recording. |
| **Record** | New samples after manual recording starts | Starts a non-rotating file when auto-save is off or stopped. |
| **Stop recording** | All rows accepted before stopping | Drains and closes the file. |
| **Download last CSV** | The latest file after recording stops; earlier daily files remain in `recordings/` | None. |
| **Export buffer** | A snapshot of all currently buffered pairs | None. |
| **Clear data** | Removes buffered pairs from the UI | The file remains; recording can continue. |

Each row keeps both channels from the same conversion:

| Columns | Meaning |
| --- | --- |
| `timestamp_utc`, `sequence` | UTC timestamp and increasing sample number. Clearing the buffer does not reset the sequence. |
| `temperature_c`, `relative_humidity_pct` | Converted temperature in °C and humidity in %RH. |
| `source` | USB or explicitly labeled simulator source. |
| `raw_temperature`, `raw_humidity` | Unsigned 16-bit sensor words after CRC validation. |
| `mode`, `low_power` | Active measurement mode and LPM0–3 for that pair. |
| `heater_on` | `1` when heater status was on, otherwise `0`. Cooldown effects are not captured by this flag. |

Plots display local time. CSV timestamps use UTC with the `+00:00` offset. Incomplete
or CRC-failed pairs are discarded. Queue overflow and disk errors appear in the UI;
a file with dropped rows or a writer error is not a complete capture.

## 4. Apply settings and check the result

Switch to **Device settings** while connected. Monitoring and recording continue
across tab changes, and editable controls retain draft values.

1. Select a **Measurement mode** and **Low-power mode**.
2. Click **Apply measurement settings**.
3. Check the completion message and **Applied** line. Selecting a dropdown alone
   does not change the device.

![Simulated device after applying automatic 1 Hz and LPM1, with identity and heater-off status visible](images/device-settings.jpg)

*Applied: auto_1hz, LPM1. The simulator's NIST serial is a fixture. No physical
device was contacted for this screenshot.*

| Mode | Acquisition behavior |
| --- | --- |
| **On demand** | Each host sample triggers and waits for a new conversion. Default: one pair every second. |
| **Automatic · 1 Hz** | The sensor converts autonomously; host fetch spacing is at least 1.02 s. |
| **Automatic · 0.5 Hz** | The sensor converts autonomously; host fetch spacing is at least 2.02 s. |

A longer requested sample interval slows host reads further. LPM0 has the lowest
noise; LPM1–3 trade noise for lower power and shorter conversions. Settings are volatile.

**Take one sample** requires paused monitoring and on-demand mode. **Read status**
refreshes flags; **Clear status** clears tracking/reset flags. **Read device / NIST ID**
shows TI manufacturer ID `0x3000`, a 48-bit sensor NIST serial, bridge firmware and USB
serial. The manufacturer word is not an HDC-specific model identifier.

**Soft reset** restores the app's on-demand LPM0 defaults and heater-off state.
It does not make current dropdown drafts the active configuration.

### Heater control

Acknowledge **I understand this heats the sensor and affects readings**, then request
**5 s low-level pulse** only when heating is appropriate. The app uses the minimum
heater element; **Heater off** requests disable on the device worker. Orange plot
markers and `heater_on=1` identify heater-on samples, which remain in statistics.
Allow cooldown before interpreting ambient readings.

The host timer runs even while sampling is paused. USB failure or a stopped host
cannot guarantee shutdown: unplug the board if heater-off is uncertain. One
minimum-element physical pulse passed under H015's attended scope (E033); that
test does not authorize routine heating in other setups. The settings
screenshot keeps the heater off.

## 5. Finish a session

1. Click **Disconnect** to drain the CSV, attempt heater-off/exit-auto and
   release the device. Wait for **Saved** in the recording status.
2. Download the latest file if needed; earlier daily files remain in
   `recordings/`.
3. Stop the server with **Ctrl+C** in its terminal.

Closing a browser tab does not stop the Python process or its session. **Stop** alone
also keeps the device open. Disconnect before opening TI's GUI or another hardware
test, or before unplugging/replugging USB. Wait for **Disconnected** and **Saved**
before removing the cable. If cleanup fails, resolve the error and unplug the
EVM when shutdown is uncertain.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| No USB2ANY/OneDemo bridge found | Check USB and close TI's GUI. Confirm board/firmware assumptions in the [protocol notes](protocol.md); do not flash firmware as a shortcut. |
| Multiple USB2ANY bridges found | Enter the HDC3020EVM's USB serial from the listed bridges, or connect only that board. A blank serial selects a bridge only when exactly one is enumerated; it does not identify the sensor automatically. |
| USB2ANY I²C write timeout `-49` | The selected bridge reported a timeout during a raw I²C write. Read the USB serial in the error, confirm it is the HDC3020EVM, check address/connection and close TI's GUI, then reconnect. With two attached bridges, enter the known EVM serial instead of leaving it blank. |
| USB HID write failed (`-1`) after USB reconnect | HIDAPI reports `-1` for a failed write. **Stop** retains the old HID handle, which can fail after a cable replug. On the first sample after **Start**, the app makes one bounded reopen of the selected bridge, verifies the same sensor identity, then resumes the CSV. If reopening fails, wait for USB enumeration and use **Start** again after the session has closed; do not repeatedly click while it says Connecting or Disconnecting. |
| Missing HID dependency | Start with `uv run --extra usb python app.py` so uv includes the USB dependency. |
| USB2ANY error -54 | The bridge's internal I²C pullups need its separate 3.3 V EXT output. The stock EVM already has on-board pullups, so this app disables bridge pullups (E012/D003). Verify this is a stock board and use the current code. |
| CRC, NAK or failed reads | Check connection, address and device ownership. Three consecutive failures close the session; reconnect after resolving the cause. |
| A settings command fails | The session closes because a timed-out write may have taken effect. Reconnect to establish known state. |
| Download last CSV is disabled | Start a recording, stop it, and allow the writer to finish. Inspect writer errors if it stays unavailable. |
| Old values remain visible | Check timestamp and connection. Pausing/disconnecting retains history; it does not imply new acquisition. |
| Plots stopped following data | Click **Follow live · 5 min** to leave the held range. |
| Default port is busy | Use `uv run python app.py --simulate --port 8051` and open `http://127.0.0.1:8051/`. Never run two processes against one board. |

[Back to README](../README.md) · [Validation evidence](../outputs/REPORT.md)
