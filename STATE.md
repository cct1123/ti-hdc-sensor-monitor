# Current checkpoint

Phase: **AWAITING_HUMAN_REVIEW**
Checkpoint: 2026-09-20 22:29 America/Chicago (2026-09-21 03:29 UTC), E007
Last applied human input: H003
Owner: released after software review and publication checkpoint. Staleness window 24 h, after checking task liveness.

## Current result
Hardware-ready dashboard. Review outputs/REPORT.md and outputs/candidate-manifest.json.
Source/configuration candidate SHA256:
`8d6349c231c8ac62431c035b6507c3c2bd55c676258b945addb94280638515f2`.
Hashes normalize CRLF to LF; see manifest for digest method. Implementation commit
`c1794ea92c06845903356b5d003da24961913a8e` pushed to origin/main under H003 (E007).
This checkpoint is a following documentation commit. Python 3.12.14 / Dash 3.4.0 /
hidapi 0.15.0; packages in uv.lock.
Defaults: USB2ANY 2047:0301, I2C 0x44, 100 kHz, on-demand LPM0, 1 s, heater off.

| Requirement | Software evidence | Overall status / remaining method |
| --- | --- | --- |
| REQ-001 USB/raw I2C | TEST-001, E002 PASS (fake HID) | UNTESTED: actual EVM, TEST-005 |
| REQ-002 paired 1 Hz/CRC/conversion | TEST-001/002/003, E002/E003 PASS | UNTESTED: physical readings, TEST-005 |
| REQ-003 values/stats/history | TEST-004, E002/E004 PASS | PASS simulated UI; physical integration pending |
| REQ-004 CSV/log/export | TEST-003/004, E002/E003/E004 PASS | PASS simulator/disk; physical integration pending |
| REQ-005 basic controls | TEST-002/003/004, E002/E004 PASS | UNTESTED: physical controls, TEST-006 |
| REQ-006 single session/reuse/errors/tests | TEST-001–004, E002 PASS | PASS software; physical failure modes pending |

36 tests, Ruff lint/format and compile check pass after review cleanup (E006).
Thirty-sample simulation median
interval 0.999076 s, no read failures/lost rows, successful close/reopen (E003).
No physical HID enumeration/open performed.
E005 reconciled the original candidate. E006 pruned unused CSS/plot setup and
verified unchanged output; the updated manifest supersedes the original digest.
Saved simulation evidence remains applicable. H003 preserves the hardware gate.

## Architecture
Dash callbacks -> AcquisitionService -> queued DeviceSession worker -> HDC3020Sensor
-> USB2ANYHIDTransport (or simulator). Paired sample buffer and separate CSV writer.
See ARCHITECTURE.md and docs/protocol.md.

## Human action required
Approve the candidate in outputs/REPORT.md for initial USB validation: identity,
thirty approximately one-second paired samples, CSV checks and clean close/reopen.
Connect one stock HDC3020EVM and close TI's GUI. Keep heater off; no EEPROM/firmware
changes. Identify a USB serial if several boards are attached. Record approval as
H004 (or the next unused H ID) with candidate and scope before acting.

Next: follow docs/hardware-validation.md TEST-005, starting with filtered HID
discovery/identity. Preserve reports and reconcile actual hardware assumptions.
Control validation follows reliable V1 acquisition; heater testing needs explicit scope.

## Loop continuity
No hardware authorization recorded. H003 software review and candidate publication
completed (E006/E007). Git destination: git@github.com:cct1123/ti-hdc-sensor-monitor.git,
branch main tracking origin/main. This documentation checkpoint is also to be committed
and pushed; completion is observable by matching local HEAD with remote refs/heads/main.
No physical operation is in flight. Reconcile Git refs before any publication retry.
Current gap: physical validation; zero physical attempts. Preview may be running
at http://127.0.0.1:8050 with simulation selected, heater off and recording stopped.
Test/browser recordings in recordings/ are ignored scratch data. Reproducible
simulation evidence is under outputs/simulation-validation/.

Ruled-out approaches:
- TMP one-byte register reads: HDC uses 16-bit commands and delayed raw reads (E001).
- Empty auto fetch as a valid measurement: all-FF latch means no fresh result (E001/E002).
- Native heater confirmation: embedded-browser stall; use inline acknowledgement (E004).
- Shift simulated auto clock on fetch: inaccurate; use autonomous periodic timing (E004).

No further hardware-independent gap found in final review. Resume at the candidate
gate; software/simulation PASS is not physical validation.
