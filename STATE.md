# Current checkpoint

Phase: **AWAITING_HUMAN_REVIEW** (H016/H019/H020 revised candidate)
Checkpoint: 2026-09-25 14:31 America/Chicago, H020 publication verified
Last applied human input: H020
Owner: released at 2026-09-25 14:31 America/Chicago.
Staleness window 24 h, after checking task liveness.

## Current result

The reviewed candidate was explicitly approved for connected-board integration
under H007. Its original SHA256 is `511516293b1c4a4faf00c66b5c31351634c0c3d64b1273422b0b926211c36007`
([candidate manifest](outputs/candidate-manifest.json)). The first physical
TEST-005 attempt failed with USB2ANY error -54 before sensor identity (E012).
TI's error table and EVM schematic supported D003: disable bridge-managed I2C
pullups because the stock EVM has passive pullups to its USB-powered 3.3 V rail.
The H010 corrected source/configuration snapshot SHA256 is
`9111c1713dbe667c652141ecd7226ca79967314220731685a2819c27d7b2620a`
([validation manifest](outputs/validation-manifest.json)).

Current retest board: USB2ANY/OneDemo VID:PID 2047:0301, serial
`87F2A26E08002500`, firmware 2.8.2.0; HDC address 0x44, manufacturer
0x3000, NIST ID `1BADE0120F3E` (E028). The earlier board was serial
`88F2A26E25000200`, NIST ID `1A73E0120F3E`. 100 kHz, 7-bit I2C, bridge
pullups off; connect restores on-demand LPM0 and heater off. Current runtime
Python 3.12.13, Dash 3.4.0, Plotly 7.1.0,
hidapi 0.15.0. No firmware/EEPROM/offset/threshold, board-power or general-call
reset command was issued. One H015-approved minimum-element integrated-heater
pulse was issued, then status-off and clean close were verified (E033).

| Requirement | Current status and method |
| --- | --- |
| REQ-001 USB/raw I2C | Explicit-serial physical path PASS on previous runtime (E028/E029, TEST-005); H020 `hid_write=-1` classification and bounded reopen PASS in fake-HID/simulation tests (E042), revised physical path UNTESTED pending review |
| REQ-002 paired conversion/cadence | PASS: 30 new-board physical pairs, 0.999964 s median, zero failed reads; raw conversion/CRC software tests (E027/E029, TEST-001/002/005) |
| REQ-003 live values/stats/history | PASS: real Dash callbacks and browser show paired values/aligned plots and follow behavior (E030/E031, TEST-004/005) |
| REQ-004 CSV/log/export | PASS in 50-test software suite and prior simulator browser for H016 auto-start, UTC rollover, opt-out, disconnect and H020 reopen continuity (E035/E042, TEST-003/004); physical auto path UNTESTED pending candidate review (E036) |
| REQ-005 volatile controls/identity | PASS: all 12 mode/LPM combinations and status clear/reset on the earlier board (E014/E017); new-board identity, auto 1 Hz/LPM1 and one approved integrated-heater pulse/status-off/cooldown (E028/E030/E032/E033, TEST-006) |
| REQ-006 single worker/errors/tests | PASS in 50-test software suite, including H020 stale-handle lifecycle and heater-active refusal (E042); physical integration of changed session callbacks UNTESTED pending candidate review (E036) |

Physical TEST-005 report/CSV:
outputs/hardware-validation/validation_20260923_200902_021356.json and paired
CSV beside it. Non-heater TEST-006 report:
outputs/hardware-validation/controls_20260923_201208_417991.json (auto 1 Hz /
0.5 Hz medians 1.0172985 / 2.0151055 s, zero failed reads). Actual Dash HTTP
callback report and CSV: outputs/hardware-validation/dashboard_20260923_201425_005010.json
and paired CSV beside it. outputs/REPORT.md is the consolidated system report.
New-board retest evidence: E027–E031; reports and paired CSVs in
outputs/hardware-validation with 20260924 timestamps. Only auto 1 Hz/LPM1 of
the non-heater controls was repeated on the new board; E017's all-mode result
applies to the earlier board.
H015 integrated-heater preflight and physical TEST-006 are E032/E033; the
heater report and CSV have 20260924 timestamps. E034 checked all current
software/physical evidence together against REQ-001–006 on the final runtime.
Absolute accuracy/calibration was not an acceptance claim and no independent
reference was supplied; the earlier board's approximately 23 °C / 45–47 %RH
and current board's approximately 22.5–22.7 °C / 43 %RH are plausibility only.

## Architecture and configuration

Dash callbacks → AcquisitionService → queued DeviceSession worker → HDC3020Sensor
→ USB2ANYHIDTransport (or simulator). Paired sample buffer and separate CSV
writer. History limit 7,200 pairs. See ARCHITECTURE.md and docs/protocol.md.
The H010 reviewed source, documentation and evidence commit is
`ae8a3f48bae58bb49e8702b8953cf6cd74762983` on origin/main (E025/E026).
The earlier `6514201` baseline was fast-forwarded. H016 has since changed
runtime recording, session callbacks and UI; its 38-file normalized review
snapshot is `outputs/auto-record-candidate-manifest.json`, SHA256
`550ce489168e64a03720c953add6d3ddbb671547ff103105d42d2b68200a88bc`
(E042; supersedes E040's digest). H017 removed the sample-interval helper note without changing the
configured interval or buffer. H018 updated the guides and pruned three stale
simulator screenshots; commit `b0cb8a2cf290029d5c225d6272be3f0a021a7847`
was pushed to `origin/main` and independently verified (E039). The prior
physical E029–E033 results apply to the older runtime, not the new auto-save
path. H019 improved USB selection/timeout feedback, with 44 software tests
passing. The user's explicit serial works by report; the bridge enumerated
during the blank-serial failure is unknown (E040). The focused source commit
`19fd5f24b638f3ee95cc7923b9e450b03e7e9f58` was pushed to `origin/main`
and its remote ref independently verified (E041).
H020 adds one identity-checked HID reopen after the first failed sample on
Start/Resume, only with heater off. Its failure behavior and CSV continuity
pass software tests; the user's exact button/cable sequence is unconfirmed.
The H020 source commit `93cc0db840d755bdb6681b0841c82c19bd602952`
was pushed to `origin/main` and independently verified (E043).

## Human action required

Review the H016/H019/H020 manifest and report, then explicitly approve a bounded
non-heater automatic-CSV and reconnect check on HDC3020EVM USB serial
`87F2A26E08002500`, address 0x44. E042 shows 50 software tests PASS; H007
covered an older candidate. On approval, verify identity/heater-off anew,
run the short Start/Stop/resume/Disconnect CSV procedure, and have the operator
perform one USB cable unplug/replug while monitoring is stopped to exercise
H020 as documented in docs/hardware-validation.md. Return the button/cable
sequence used in the original failure if known, and the resulting UI status,
error text, CSV row count and device identity from this check. No heater pulse
is requested; H015's single pulse is complete.

## Loop continuity

In-flight operation: none. H020 screenshot shows `hid_write=-1` on repeated
measurement and shutdown commands after a stopped/reconnected device. Stop
pauses sampling but retains the HID handle; a USB replug can invalidate it.
E042/D005 document a bounded software recovery and 50-test PASS. The exact
button/cable sequence remains unconfirmed, and no physical probe is authorized
for this revised candidate. H019 reports `-49` on blank serial while two
bridges are attached and explicit serial succeeds. Under current code, two
enumerated bridges produce an ambiguity error before I2C. The observed HID
enumeration during that failure is unknown; E040 records the software repair
and passing fake-HID tests. No real-device interaction is authorized for the
revised candidate.
The H018 source and evidence commit was published
and remote `refs/heads/main` verified equal to
`b0cb8a2cf290029d5c225d6272be3f0a021a7847` (E039). H016 implementation
and independent validation are complete (E035/E036/E038). Stay at the review
gate until approval of the candidate and scope is recorded as a new H entry.
Then run the bounded physical CSV check and update REQ-004/006 status.
The H015 TEST-006 was performed exactly once, with
final status off and clean disconnect (E033). The runner process exited.
The H011/H012 identity, acquisition, Dash callback and live browser checks
finished (E027–E031). Device state is not assumed to persist after this
checkpoint; verify it anew before any future physical interaction. H015
approval covered only the completed single pulse.
The earlier browser sessions stopped and exited. The H010 source push was
verified against origin/main (E026). Gap attempt count 0; prior H007 heater
request was resolved by H015 for one exact bounded pulse, not repeated tests.

Ruled-out approaches:
- TMP one-byte register reads: HDC uses 16-bit commands and delayed raw reads (E001).
- Empty auto fetch as a valid measurement: all-FF latch means no fresh result (E001/E002).
- Native heater confirmation: embedded-browser stall; use inline acknowledgement (E004).
- Shift simulated auto clock on fetch: inaccurate; use autonomous periodic timing (E004).
- Enable USB2ANY-managed pullups without 3.3 V EXT power: fails -54 on this
  stock EVM (E012/D003); revisit only for a different documented board/power setup.
