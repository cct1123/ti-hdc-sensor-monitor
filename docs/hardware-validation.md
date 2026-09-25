# Physical validation procedure and results

Under H007, TEST-005 and the non-heater portion of TEST-006 were run on one
connected HDC3020EVM on 2026-09-23. H011/H012 repeated core monitoring on a
second board, and H015 authorized one bounded physical check of the sensor's
optional integrated heater on that board (E028–E033). See outputs/REPORT.md.
The procedures remain reproducible; independent sensor accuracy calibration
has not been performed.

## H016 automatic-recording candidate (pending review)

The H016 change has software and simulator evidence only (E035). Before using
the revised source with the EVM, review its candidate manifest, current report,
and the following non-heater TEST-005 procedure. H007 approved an earlier
candidate; H015's one heater pulse was consumed. Do not repeat the heater test.

With explicit approval for this candidate and the identified board, close TI's
GUI and any other process holding USB2ANY. Select USB serial
`87F2A26E08002500`, address 0x44, 1 s interval, and leave the checked **Save CSV
automatically while monitoring** option enabled. First identify the bridge,
manufacturer 0x3000, CRC-valid NIST ID `1BADE0120F3E`, and heater-off status;
stop if any differ. Start monitoring, accept at least five paired samples, and
verify that the CSV begins only after connection, has the same paired values and
UTC timestamps as the buffer, and shows zero dropped rows. Pause with **Stop**,
verify the writer remains active, then resume and confirm it uses the same file.
Disconnect and verify the writer drains/closes, **Download last CSV** becomes
available, and the row count matches the accepted buffer. Repeat one short
non-heater run with auto-save unchecked to verify no automatic file is made;
manual **Record** must still work. The UTC boundary is covered by the
deterministic software TEST-003; no physical midnight wait is required.

For the H020 reconnect regression, after normal heater-off monitoring has
produced at least two CSV rows, click **Stop** and confirm sampling pauses.
With the operator present, unplug/replug the EVM's USB cable once and wait for
the same serial to enumerate. Click **Start monitoring** once. If the held HID
handle fails, the worker may reopen it once; verify the NIST ID is unchanged,
monitoring resumes, the same CSV file receives new paired rows with increasing
timestamps, and no heater-on state appears. If identity changes, reopen fails,
or the status stays in Error, stop the check and preserve the exact UI error.
Click **Disconnect** and verify the file drains. This cable-cycle check is a
separate action within the revised candidate's requested approval; it was not
performed during software development.

If identity, paired acquisition, CSV agreement, cleanup, or error reporting
fails, stop and preserve the exact report/CSV/UI error. On clean shutdown the
worker attempts heater-off, exit-auto, and HID close. If device status becomes
uncertain, unplug the EVM. No heater-on, persistent configuration, firmware,
EEPROM, offset, threshold, general-call reset, or board-power action is within
this recording check.

## First authorized interaction (TEST-005)

Scope: one stock USB-powered HDC3020EVM, address 0x44, normal room conditions,
TI GUI closed. No EEPROM, firmware, offset, threshold, general-call reset or heater-on writes.

1. Disconnect any dashboard device session. Connect the board by USB.
2. Run `uv run --extra usb python -m hdcsensor.validate --hardware --samples 30 --interval 1`.
3. First operations: enumerate only VID/PID 2047:0301; require exactly one matching
   board (or explicit serial); open; firmware command 0A; I2C 100 kHz/7-bit with
   bridge pullups disabled (stock EVM has on-board pullups); manufacturer 3781
   and NIST 3683/84/85. A wrong manufacturer causes immediate close.
4. Initialization: heater off 3066, status F32D verification, exit auto 3093.
   Acquire with 2400, wait 16 ms, read six bytes, read status. No CRC-failed pair is logged.
5. Inspect the JSON report: at least 30 pairs, no failed reads/dropped CSV rows,
   median interval 0.8–1.25 s, matching CSV and memory values/timestamps, clean close,
   successful reopen with identical NIST serial, and clean final close.
6. Run the dashboard. Verify both values against TI's GUI in separate sessions,
   or a suitable reference instrument. This is a plausibility check, not a calibrated
   accuracy claim. Verify shared-X plots, Stop/Resume and logging/download in the actual UI.

If VID/PID differ, stop and identify the board/firmware before modifying discovery.
On NAK/CRC errors, save the report and check device ownership and stock wiring.
Avoid changing multiple transport assumptions at once.

Actual TEST-005 result: the first attempt failed with USB2ANY error -54 because
bridge-managed pullups were selected without its 3.3 V EXT output. The stock EVM
schematic shows passive 10 kΩ I2C pullups to its USB-powered 3.3 V rail. D003
disabled bridge pullups; the corrected run passed 30 paired samples, matching
CSV, 1.000613 s median interval, zero failures, and clean close/reopen/close
(E015). The dashboard's physical callbacks then passed plots, recording,
export/download and disconnect (E019).

## Controls (TEST-006, after V1 succeeds)

Record device identity, board/firmware and before/after status. With explicit scope:
switch on-demand/auto 1 Hz/auto 0.5 Hz; exercise LPM0–3; verify cadence and valid paired
responses; pause and take a single on-demand sample; read/clear status and check
reset tracking flags; soft reset and check on-demand LPM0/heater-off defaults.
Commands without readable mode state are established by acknowledged command and
subsequent behavior, not claimed register readback.

Non-heater TEST-006 PASS (E017): all 12 mode/LPM combinations yielded valid
paired values, auto 1 Hz/0.5 Hz median intervals were 1.0172985/2.0151055 s,
status 0x8010 cleared to 0x0000, soft reset restored the reset flag and defaults,
and the session closed without read failures. Reproduce with
`uv run --extra usb python -m hdcsensor.validate_controls --hardware --output
outputs/hardware-validation`.

Heater testing requires separate explicit inclusion in approval: minimum element
0x0001 for one five-second pulse only, board attended, no samples/equipment exposed
to heat. Confirm status bit 13 rises and clears, CSV flag/plot marker appear, and
the sensor returns toward ambient after cooldown. The software cannot certify an
environment-specific thermal limit. Skip this test unless the setup permits heating.
Under H015, the bounded runner was invoked once with `uv run --locked --extra usb
python -m hdcsensor.validate_heater --hardware --confirm-attended --serial
87F2A26E08002500 --output outputs/hardware-validation`. It was first rehearsed
in simulation (E020); its physical report preserves actual temperatures, RH and
status/CSV checks. Do not interpret cooldown values as calibrated accuracy.

Actual H015 TEST-006 result: PASS on serial `87F2A26E08002500`, with one
minimum-element pulse lasting 5.047 s, status-on/off, 13 paired samples, two
heater-on CSV rows, final off status, zero failed reads/recording loss and clean
disconnect (E032/E033). This is one attended validation, not blanket permission
for heating in other physical setups.

## Stop and recovery

Use Disconnect to drain an active recording and release the board. Cleanup
attempts heater-off, exit-auto, HID close.
Terminate the app gracefully with Ctrl+C. If shutdown status is uncertain or the
process/USB path fails, physically unplug the EVM. Reconnect establishes defaults
again; no persistent sensor memory was intentionally changed. Preserve failed
reports rather than marking an inconclusive test PASS.
