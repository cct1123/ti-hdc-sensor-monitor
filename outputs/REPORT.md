# HDC3020EVM monitor: hardware-ready candidate

**Phase: AWAITING_HUMAN_REVIEW.** Software and simulated integration pass;
the physical HDC3020EVM has not been enumerated, opened or measured.
Candidate source/configuration hashes: [candidate-manifest.json](candidate-manifest.json).
Candidate SHA256: `8d6349c231c8ac62431c035b6507c3c2bd55c676258b945addb94280638515f2`.
File hashes normalize CRLF to LF so Windows and Git checkouts verify identically;
the exact digest method is recorded in the manifest. Git publication is tracked in STATE.md.

## Delivered

- TMP-style local Dash UI: paired values, min/mean/max, 7,200-sample history,
  synchronized plots, held zoom/pan and live follow; persistent monitor/settings pages.
- Direct USB2ANY HID packet/CRC/reply validation, raw I2C, bounded timeouts;
  HDC3020 commands, conversion delays, per-word sensor CRC and paired conversion.
- Single queued device worker, bounded queues, explicit errors, cancellation,
  cleanup and reconnect. Bad measurement pairs are discarded; failed writes invalidate the session.
- Separate CSV worker with drain-on-stop, loss/error counters, saved CSV download
  and current-buffer export. UTC timestamps and per-sample mode/LPM/heater metadata.
- On-demand/auto 1 Hz/auto 0.5 Hz, LPM0–3, status read/clear, manufacturer/NIST ID,
  soft reset, minimum-element five-second heater pulse with inline acknowledgement, and heater-off.
- Simulator, tests, bounded validation command, usage/protocol documentation and engineering records.

## Evidence

| Method | Result | Evidence |
| --- | --- | --- |
| TEST-001/002: protocol/driver/fake HID | PASS | [reviewed candidate: 36-test transcript](review-unit-tests.txt) |
| TEST-003: session/CSV concurrency and failure handling | PASS | same transcript |
| TEST-004: Dash HTTP/plots/simulator integration | PASS | same transcript, E004 |
| 30-sample simulated acquisition/CSV/close/reopen | PASS | [JSON report](simulation-validation/validation_20260921_030438_901402.json) |
| Ruff lint/format and Python compile check | PASS | E006; rerun after cleanup |
| Browser monitoring/settings/zoom/follow/recording/heater timer | PASS, simulation only | E004 |
| TEST-005: physical USB acquisition/CSV/reopen | UNTESTED | Candidate approval required |
| TEST-006: physical controls and heater | UNTESTED | After V1; heater needs specific scope |

Final software review (E006) removed unused TMP-specific CSS and discarded per-channel
plot layout setup. The final plotted values/axes are unchanged. Browser checks found
identical computed styles on 36 selected elements and intact monitor/settings pages.
Device, session and recording behavior is unchanged; E003's simulation remains applicable.

Simulation: 30 pairs, median interval **0.999076 s**, range 0.975828–1.019840 s,
zero failed reads, no recording loss, matching CSV values/timestamps and successful reopen.
These are simulator/host results, not physical measurements. The browser session
on the final layout reached 267 samples without read failures; a 77-row recording
saved with zero drops. Browser checks confirmed the final inline heater control
and automatic shutoff while sampling was paused, then soft reset and resumed acquisition.

Environment: Windows, Python 3.12.14, Dash 3.4.0, Plotly 7.1.0, hidapi 0.15.0,
Ruff 0.16.8; dependencies locked in uv.lock. Tests outside the sandbox were needed
for Python temporary-directory ACL compatibility, not device access.

## Limits and assumptions

Actual HDC3020EVM VID/PID, firmware compatibility, pullup settings and raw-read
framing require confirmation. They are grounded in the TMP bridge and TI HDC GUI;
fakes do not prove board compatibility. Manufacturer 0x3000 plus NIST response is
useful identity evidence, not a unique model identifier. See [protocol.md](../docs/protocol.md).

Physical conversion timing, auto-latch behavior, recovery and thermal behavior
remain unverified. No calibrated accuracy claim is made. Heater timing is host-managed,
best-effort; loss of communication or host control cannot guarantee shutoff. Unplug
the EVM if shutdown is uncertain. Heater-on and cooldown readings are not ambient readings.

Run only one local process per board. No EEPROM programming, firmware flashing,
general-call reset, threshold/offset editor or board power switching is exposed.

## Requested next authorization

Connect one stock HDC3020EVM by USB, close TI's GUI, and approve this candidate for
**identity, 30 one-second paired samples, CSV verification, close/reopen**, with
**heater kept off**. Exact first interactions, acceptance checks and recovery:
[hardware-validation.md](../docs/hardware-validation.md).

After approval:

```powershell
uv run --extra usb python -m hdcsensor.validate --hardware --samples 30 --interval 1
```

First: filtered HID discovery and firmware identity, I2C setup, CRC-checked TI/NIST
identity; then heater-off, exit-auto, and on-demand acquisition. Cleanup attempts
heater-off/exit-auto and closes HID. Physically unplug on uncertain shutdown.
Preserve JSON/CSV evidence. Physical control validation follows reliable V1 acquisition;
heater-on testing requires separate explicit scope.
