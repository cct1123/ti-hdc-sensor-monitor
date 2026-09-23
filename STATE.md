# Current checkpoint

Phase: **BLOCKED** (resume **HARDWARE_VALIDATION** after heater-scope input)
Checkpoint: 2026-09-23 16:15 America/Chicago, H010 review passed (E025)
Last applied human input: H010
Owner: current Codex session since 2026-09-23 16:11 America/Chicago. Staleness
window 24 h, after checking task liveness.

## Current result

The reviewed candidate was explicitly approved for connected-board integration
under H007. Its original SHA256 is `511516293b1c4a4faf00c66b5c31351634c0c3d64b1273422b0b926211c36007`
([candidate manifest](outputs/candidate-manifest.json)). The first physical
TEST-005 attempt failed with USB2ANY error -54 before sensor identity (E012).
TI's error table and EVM schematic supported D003: disable bridge-managed I2C
pullups because the stock EVM has passive pullups to its USB-powered 3.3 V rail.
The corrected source/configuration SHA256 is
`9111c1713dbe667c652141ecd7226ca79967314220731685a2819c27d7b2620a`
([validation manifest](outputs/validation-manifest.json)).

Actual board: USB2ANY/OneDemo VID:PID 2047:0301, serial `88F2A26E25000200`,
firmware 2.8.2.0; HDC address 0x44, manufacturer 0x3000, NIST ID
`1A73E0120F3E`. 100 kHz, 7-bit I2C, bridge pullups off; connect restores
on-demand LPM0 and heater off. Python 3.12.14, Dash 3.4.0, Plotly 7.1.0,
hidapi 0.15.0. No firmware/EEPROM/offset/threshold, board-power, general-call
reset or heater-on command was issued.

| Requirement | Current status and method |
| --- | --- |
| REQ-001 USB/raw I2C | PASS: physical identity/CRC/firmware and clean reopen/close (E014/E015, TEST-005) |
| REQ-002 paired conversion/cadence | PASS: 30 physical pairs, 1.000613 s median, zero failed reads; raw conversion/CRC software tests (E013/E015, TEST-001/002/005) |
| REQ-003 live values/stats/history | PASS: real Dash callbacks show paired values/aligned plots; visual browser layout/zoom/follow checked in simulation (E004/E019, TEST-004/005) |
| REQ-004 CSV/log/export | PASS: 30 physical CSV rows match buffer; actual Dash recording/export/download passed with zero loss (E015/E019, TEST-005) |
| REQ-005 volatile controls/identity | PARTIAL: all 12 mode/LPM combinations, status clear/reset, NIST identity pass physically (E014/E017); heater-on/cooldown physical test remains UNTESTED pending specific scope (TEST-006) |
| REQ-006 single worker/errors/tests | PASS: 36 software regressions, simulation and physical integration/cleanup (E013/E015/E017/E019, TEST-001–006); heater failure recovery only simulated |

Physical TEST-005 report/CSV:
outputs/hardware-validation/validation_20260923_200902_021356.json and paired
CSV beside it. Non-heater TEST-006 report:
outputs/hardware-validation/controls_20260923_201208_417991.json (auto 1 Hz /
0.5 Hz medians 1.0172985 / 2.0151055 s, zero failed reads). Actual Dash HTTP
callback report and CSV: outputs/hardware-validation/dashboard_20260923_201425_005010.json
and paired CSV beside it. outputs/REPORT.md is the consolidated system report.
Absolute accuracy/calibration was not an acceptance claim and no independent
reference was supplied; the observed 23 °C / 45–47 %RH is plausibility only.

## Architecture and configuration

Dash callbacks → AcquisitionService → queued DeviceSession worker → HDC3020Sensor
→ USB2ANYHIDTransport (or simulator). Paired sample buffer and separate CSV
writer. History limit 7,200 pairs. See ARCHITECTURE.md and docs/protocol.md.
The published baseline is `6514201` on origin/main under H006 (E011); physical
fixes/evidence are local worktree changes. H010 authorizes review, commit and
push; prepublication review passed (E025).

## Human action required

Known: core acquisition, dashboard/CSV and non-heater controls pass on this
board (E015/E017/E019); status and cleanup are verified. The remaining heater
test is outside H007's approved scope, and all other useful independent work
has been completed. Confirm whether to authorize **one attended five-second
minimum-element (0x0001) heater pulse** on this board, with no heat-sensitive
samples or equipment nearby, followed by status-off and cooldown checks. A
yes/no answer is sufficient; if yes, confirm those setup conditions hold.
After authorization, run the bounded TEST-006 heater check in
docs/hardware-validation.md (simulated rehearsal E020), record status/
temperature/RH/CSV markers and cleanup, then perform final integrated
validation. If denied, preserve heater
as an unvalidated requirement and report that limit.

## Loop continuity

In-flight operation: commit the reviewed H010 source, docs, records and evidence,
then push `main` to origin as a fast-forward from
`6514201add0143c38b05099108b1a9a91a1ed516`. Expected effect: origin/main
references the new commit. Verify with `git ls-remote origin refs/heads/main`
and compare to local HEAD; if interrupted, inspect both refs before retrying.
No force push. All physical processes exited; TEST-005 and the
non-heater controls/dashboard checks reported clean close (E015/E017/E019).
Do not infer current device state solely from those reports before another
interaction; enumerate and establish known state again under valid scope.
H009 Bash/uv quick start is complete (E024). H010 review passed (E025);
publication is pending. The physical heater test remains
blocked on separate authorization (E022). Gap attempt count 0; one
asynchronous specific-scope request has been sent. Do not run the physical
heater test while that request is unresolved. Resume hardware validation after
the answer; do not repeat passing physical procedures without a regression reason.

Ruled-out approaches:
- TMP one-byte register reads: HDC uses 16-bit commands and delayed raw reads (E001).
- Empty auto fetch as a valid measurement: all-FF latch means no fresh result (E001/E002).
- Native heater confirmation: embedded-browser stall; use inline acknowledgement (E004).
- Shift simulated auto clock on fetch: inaccurate; use autonomous periodic timing (E004).
- Enable USB2ANY-managed pullups without 3.3 V EXT power: fails -54 on this
  stock EVM (E012/D003); revisit only for a different documented board/power setup.
