# Current checkpoint

Phase: **AWAITING_HUMAN_REVIEW** (H016/H019 revised candidate)
Checkpoint: 2026-09-25 11:35 America/Chicago, H019 software review complete
Last applied human input: H019
Owner: released at 2026-09-25 11:35 America/Chicago.
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
| REQ-001 USB/raw I2C | Explicit-serial physical path PASS on previous runtime (E028/E029, TEST-005); H019 ambiguity and timeout diagnostics PASS in fake-HID tests (E040), revised physical path UNTESTED pending review |
| REQ-002 paired conversion/cadence | PASS: 30 new-board physical pairs, 0.999964 s median, zero failed reads; raw conversion/CRC software tests (E027/E029, TEST-001/002/005) |
| REQ-003 live values/stats/history | PASS: real Dash callbacks and browser show paired values/aligned plots and follow behavior (E030/E031, TEST-004/005) |
| REQ-004 CSV/log/export | PASS in 44-test software suite and prior simulator browser for H016 auto-start, UTC rollover, opt-out and disconnect (E035/E040, TEST-003/004); physical auto path UNTESTED pending candidate review (E036) |
| REQ-005 volatile controls/identity | PASS: all 12 mode/LPM combinations and status clear/reset on the earlier board (E014/E017); new-board identity, auto 1 Hz/LPM1 and one approved integrated-heater pulse/status-off/cooldown (E028/E030/E032/E033, TEST-006) |
| REQ-006 single worker/errors/tests | PASS in 44-test software suite, including H019 bridge errors (E040); physical integration of changed session callbacks UNTESTED pending candidate review (E036) |

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
`687e3411857ce9655a807dfcda50e40388592fa506ff110ca9e6327fdcfae7af`
(E040; supersedes E038's digest). H017 removed the sample-interval helper note without changing the
configured interval or buffer. H018 updated the guides and pruned three stale
simulator screenshots; commit `b0cb8a2cf290029d5c225d6272be3f0a021a7847`
was pushed to `origin/main` and independently verified (E039). The prior
physical E029–E033 results apply to the older runtime, not the new auto-save
path. H019 improved USB selection/timeout feedback, with 44 software tests
passing. The user's explicit serial works by report; the bridge enumerated
during the blank-serial failure is unknown (E040).

## Human action required

Review the revised H016/H019 candidate manifest and report, then explicitly approve the
bounded non-heater automatic-CSV check on the already identified HDC3020EVM,
USB serial `87F2A26E08002500`, address 0x44. E035 shows software and simulator
PASS; E036 records the new source boundary. All useful hardware-independent
work for H016 is complete, but H007 covered an older candidate. Return explicit
approval for this candidate and board, or a changed scope/device identity. On
approval, verify the device identity/heater-off status anew, then follow the
short Start/Stop/resume/disconnect CSV procedure in docs/hardware-validation.md.
No heater pulse is requested; H015's single pulse is complete.

## Loop continuity

In-flight operation: none. H019 reports `-49` on blank serial while two
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
